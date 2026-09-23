"""Release-gated commerce, operations, and impact API."""

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import auth, models, payment
from app import commerce_models as cm
from app import commerce_service as service
from app.config import settings
from app.db import get_db
from app.services import get_cart

router = APIRouter(prefix="/api/v1", tags=["commerce"])
Db = Annotated[Session, Depends(get_db)]


class CheckoutIn(BaseModel):
    cart_id: str
    cart_token: str


class InventoryIn(BaseModel):
    sku: str = Field(min_length=2, max_length=80)
    adjustment: int = Field(ge=-100000, le=100000)
    reason: str = Field(min_length=5, max_length=200)
    low_stock_threshold: int = Field(default=0, ge=0)


class ApprovalIn(BaseModel):
    status: Literal["approved", "rejected"]
    evidence_reference: str = Field(min_length=8, max_length=500)
    reason: str = Field(min_length=5, max_length=500)


class FormulationReviewIn(BaseModel):
    status: Literal["approved", "rejected"]
    reason: str = Field(min_length=5, max_length=500)


class ImpactIn(BaseModel):
    metric_type: str = Field(min_length=3, max_length=80)
    factor_value: Decimal = Field(gt=0)
    unit: str = Field(min_length=2, max_length=40)
    baseline: str = Field(min_length=10)
    comparison_scenario: str = Field(min_length=10)
    methodology_version: str = Field(min_length=2, max_length=60)
    source_reference: str = Field(min_length=8, max_length=500)
    qualification: str = Field(min_length=10)
    valid_to: datetime | None = None


class RefundIn(BaseModel):
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=5, max_length=500)


class FulfillmentIn(BaseModel):
    status: Literal["processing", "shipped", "delivered", "cancelled"]
    reason: str = Field(min_length=5, max_length=500)


class StaffRoleIn(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    role: Literal["customer", "support", "operations", "admin"]
    reason: str = Field(min_length=5, max_length=500)


class PrivacyRequestIn(BaseModel):
    password: str


class PrivacyReviewIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    evidence_reference: str = Field(min_length=8, max_length=500)


def audit(
    db: Session,
    actor: cm.Customer,
    action: str,
    entity: str,
    entity_id: str,
    reason: str,
    before: dict | None,
    after: dict | None,
) -> None:
    db.add(
        models.AuditEvent(
            actor=actor.email,
            reason=reason,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            before_snapshot=before,
            after_snapshot=after,
        )
    )


def staff(request: Request, db: Db) -> cm.Customer:
    session = auth.resolve_session(db, request.cookies.get("brew67_session"))
    if not session or session.customer.role not in {"support", "operations", "admin"}:
        raise HTTPException(403, "Staff access required")
    return session.customer


def operator(request: Request, db: Db) -> cm.Customer:
    customer = staff(request, db)
    if customer.role not in {"operations", "admin"}:
        raise HTTPException(403, "Operations access required")
    session = auth.resolve_session(db, request.cookies.get("brew67_session"))
    auth.enforce_csrf(request, session)
    return customer


def administrator(request: Request, db: Db) -> cm.Customer:
    customer = operator(request, db)
    if customer.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return customer


Staff = Annotated[cm.Customer, Depends(staff)]
Operator = Annotated[cm.Customer, Depends(operator)]
Administrator = Annotated[cm.Customer, Depends(administrator)]


def order_view(order: cm.Order) -> dict:
    return {
        "id": order.id,
        "status": order.status,
        "payment_status": order.payment_status,
        "fulfillment_status": order.fulfillment_status,
        "subtotal_cents": order.subtotal_cents,
        "tax_cents": order.tax_cents,
        "shipping_cents": order.shipping_cents,
        "total_cents": order.total_cents,
        "currency": order.currency,
        "created_at": order.created_at,
        "items": [
            {
                "product_id": item.product_id,
                "name": item.product_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price_cents": item.unit_price_cents,
            }
            for item in order.items
        ],
    }


def loaded_order(db: Session, order_id: str) -> cm.Order | None:
    return db.scalar(
        select(cm.Order)
        .options(selectinload(cm.Order.items))
        .where(cm.Order.id == order_id)
        .with_for_update()
    )


def upsert_subscription(
    db: Session,
    subscription_id: str,
    metadata: dict,
    stripe_customer_id: str | None,
    status: str,
    period_end: int | None = None,
) -> cm.Subscription | None:
    row = db.scalar(
        select(cm.Subscription)
        .where(cm.Subscription.provider_subscription_id == subscription_id)
        .with_for_update()
    )
    if not row:
        account_id, product_id = metadata.get("account_id"), metadata.get("product_id")
        customer = db.get(cm.Customer, account_id) if account_id else None
        product = db.get(models.Product, product_id) if product_id else None
        if not customer or not product:
            return None
        row = cm.Subscription(
            customer_id=customer.id,
            product_id=product.id,
            provider_subscription_id=subscription_id,
            status=status,
        )
        db.add(row)
        db.flush()
    row.status = status
    if period_end:
        row.current_period_end = datetime.fromtimestamp(period_end, UTC)
    if stripe_customer_id:
        customer = db.get(cm.Customer, row.customer_id)
        if customer.stripe_customer_id and customer.stripe_customer_id != stripe_customer_id:
            raise HTTPException(409, "Subscription customer mismatch")
        customer.stripe_customer_id = stripe_customer_id
    return row


def fulfill_subscription_invoice(db: Session, invoice: dict) -> str | None:
    if invoice.get("billing_reason") not in {"subscription_create", "subscription_cycle"}:
        return None
    if invoice.get("status") != "paid" or invoice.get("currency", "").upper() != "USD":
        raise HTTPException(409, "Subscription invoice is not a paid USD invoice")
    if (invoice.get("amount_paid") or 0) <= 0:
        return None
    parent = invoice.get("parent") or {}
    subscription_id = invoice.get("subscription") or (parent.get("subscription_details") or {}).get(
        "subscription"
    )
    if not subscription_id:
        raise HTTPException(409, "Subscription invoice has no subscription reference")
    existing = db.scalar(select(cm.Order).where(cm.Order.stripe_invoice_id == invoice["id"]))
    if existing:
        return existing.id
    subscription = db.scalar(
        select(cm.Subscription)
        .where(cm.Subscription.provider_subscription_id == subscription_id)
        .with_for_update()
    )
    if not subscription:
        identity = payment.subscription_identity(subscription_id)
        subscription = upsert_subscription(
            db, subscription_id, identity["metadata"], identity["customer"], identity["status"]
        )
    if not subscription:
        raise HTTPException(409, "Subscription record is not ready")
    customer = db.get(cm.Customer, subscription.customer_id)
    if customer.stripe_customer_id != invoice.get("customer"):
        raise HTTPException(409, "Invoice customer mismatch")
    product = db.get(models.Product, subscription.product_id)
    inventory = db.scalar(
        select(cm.InventoryItem).where(cm.InventoryItem.product_id == product.id).with_for_update()
    )
    formulation = service.approved_formulation(db, product.id)
    can_allocate = (
        not service.release_errors(db, product) and inventory and inventory.available >= 1
    )
    order = cm.Order(
        customer_id=customer.id,
        cart_id=None,
        subscription_id=subscription.id,
        source="subscription",
        stripe_invoice_id=invoice["id"],
        status="paid" if can_allocate else "paid_stock_hold",
        payment_status="paid",
        fulfillment_status="unfulfilled" if can_allocate else "hold",
        subtotal_cents=invoice.get("subtotal") or 0,
        tax_cents=(invoice.get("total") or 0) - (invoice.get("total_excluding_tax") or 0),
        shipping_cents=invoice.get("amount_shipping") or 0,
        total_cents=invoice.get("amount_paid"),
        currency="USD",
        shipping_snapshot=invoice.get("shipping_details") or invoice.get("customer_shipping"),
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    if inventory:
        order.items.append(
            cm.OrderItem(
                product_id=product.id,
                inventory_item_id=inventory.id,
                product_name=product.name,
                sku=inventory.sku,
                quantity=1,
                unit_price_cents=product.price_cents,
                currency="USD",
                formulation_version_id=formulation.id if formulation else None,
            )
        )
        if can_allocate:
            inventory.on_hand -= 1
            db.add(
                cm.InventoryMovement(
                    inventory_item_id=inventory.id,
                    order_id=order.id,
                    delta_on_hand=-1,
                    reason="paid subscription invoice",
                    actor="payment webhook",
                )
            )
    if can_allocate:
        db.add(
            cm.EmailOutbox(
                recipient=customer.email, template="order_confirmed", payload={"order_id": order.id}
            )
        )
    elif settings.operations_email:
        db.add(
            cm.EmailOutbox(
                recipient=settings.operations_email,
                template="order_stock_hold",
                payload={"order_id": order.id},
            )
        )
    return order.id


@router.post("/checkout/session")
def checkout(request: Request, db: Db, payload: CheckoutIn | None = None):
    if not service.commerce_ready():
        raise HTTPException(
            409, "Checkout is disabled until product and commerce release gates pass"
        )
    if payload is None:
        raise HTTPException(422, "Cart is required")
    session = auth.resolve_session(db, request.cookies.get("brew67_session"))
    if not session:
        raise HTTPException(401, "Sign in required")
    auth.enforce_csrf(request, session)
    customer = session.customer
    if not customer.email_verified_at:
        raise HTTPException(403, "Verify your email before checkout")
    cart = get_cart(db, payload.cart_id, payload.cart_token)
    db.execute(select(models.Cart).where(models.Cart.id == cart.id).with_for_update()).first()
    if not cart.items:
        raise HTTPException(409, "Cart is empty")
    existing = db.scalar(
        select(cm.Order)
        .where(
            cm.Order.cart_id == cart.id,
            cm.Order.customer_id == customer.id,
            cm.Order.status.in_(["pending_payment", "checkout_open"]),
        )
        .order_by(cm.Order.created_at.desc())
    )
    if existing:
        if (
            existing.checkout_url
            and existing.reservation_expires_at
            and auth.utc(existing.reservation_expires_at) > datetime.now(UTC)
        ):
            return {"order_id": existing.id, "checkout_url": existing.checkout_url}
        raise HTTPException(409, "A checkout is already in progress")
    order = cm.Order(
        customer_id=customer.id,
        cart_id=cart.id,
        subtotal_cents=0,
        currency="USD",
        reservation_expires_at=datetime.now(UTC) + timedelta(minutes=31),
    )
    db.add(order)
    db.flush()
    for cart_item in cart.items:
        product = db.get(models.Product, cart_item.product_id)
        if not product:
            raise HTTPException(409, "Product is unavailable")
        errors = service.release_errors(db, product)
        if errors:
            raise HTTPException(409, {"product": product.slug, "release_errors": errors})
        inventory = db.scalar(
            select(cm.InventoryItem).where(cm.InventoryItem.product_id == product.id)
        )
        formulation = service.approved_formulation(db, product.id)
        order.items.append(
            cm.OrderItem(
                product_id=product.id,
                inventory_item_id=inventory.id,
                sku=inventory.sku,
                product_name=product.name,
                quantity=cart_item.quantity,
                unit_price_cents=product.price_cents,
                currency=product.currency,
                formulation_version_id=formulation.id,
            )
        )
        order.subtotal_cents += product.price_cents * cart_item.quantity
    db.flush()
    service.reserve_inventory(db, order)
    db.commit()
    try:
        checkout_id, url = payment.create_checkout(
            order.id,
            customer.email,
            [
                {
                    "product_name": item.product_name,
                    "unit_price_cents": item.unit_price_cents,
                    "quantity": item.quantity,
                }
                for item in order.items
            ],
            order.currency,
            customer.stripe_customer_id,
        )
    except Exception:
        db.refresh(order)
        service.release_reservation(db, order, "checkout_failed")
        db.commit()
        raise
    db.refresh(order)
    order.stripe_checkout_id = checkout_id
    order.checkout_url = url
    if order.payment_status != "paid":
        order.status = "checkout_open"
    db.commit()
    return {"order_id": order.id, "checkout_url": url}


@router.get("/account/orders")
def my_orders(customer: auth.CustomerDep, db: Db):
    orders = db.scalars(
        select(cm.Order)
        .options(selectinload(cm.Order.items))
        .where(cm.Order.customer_id == customer.id)
        .order_by(cm.Order.created_at.desc())
    ).all()
    return [order_view(order) for order in orders]


@router.get("/account/orders/{order_id}")
def my_order(order_id: str, customer: auth.CustomerDep, db: Db):
    order = loaded_order(db, order_id)
    if not order or order.customer_id != customer.id:
        raise HTTPException(404, "Order not found")
    return order_view(order)


@router.get("/account/privacy-export")
def privacy_export(customer: auth.CustomerDep, db: Db):
    orders = db.scalars(
        select(cm.Order)
        .options(selectinload(cm.Order.items))
        .where(cm.Order.customer_id == customer.id)
    ).all()
    signups = db.scalars(
        select(models.IntentSignup).where(models.IntentSignup.email == customer.email)
    ).all()
    subscriptions = db.scalars(
        select(cm.Subscription).where(cm.Subscription.customer_id == customer.id)
    ).all()
    return {
        "account": {
            "email": customer.email,
            "preferences": customer.preferences,
            "created_at": customer.created_at,
        },
        "orders": [order_view(order) | {"shipping": order.shipping_snapshot} for order in orders],
        "interest_signups": [
            {
                "interest": row.interest,
                "contact_consent": row.contact_consent,
                "marketing_consent": row.marketing_consent,
                "consent_policy_version": row.consent_policy_version,
                "consented_at": row.consented_at,
            }
            for row in signups
        ],
        "subscriptions": [
            {
                "product_id": row.product_id,
                "status": row.status,
                "current_period_end": row.current_period_end,
            }
            for row in subscriptions
        ],
    }


@router.post("/account/privacy-requests", status_code=202)
def request_deletion(payload: PrivacyRequestIn, customer: auth.CsrfCustomer, db: Db):
    try:
        valid = auth.hasher.verify(customer.password_hash, payload.password)
    except VerificationError:
        valid = False
    if not valid:
        raise HTTPException(403, "Password confirmation failed")
    existing = db.scalar(
        select(cm.PrivacyRequest).where(
            cm.PrivacyRequest.customer_id == customer.id,
            cm.PrivacyRequest.request_type == "deletion",
            cm.PrivacyRequest.status.in_(["pending", "external_pending"]),
        )
    )
    if existing:
        return {"id": existing.id, "status": existing.status}
    row = cm.PrivacyRequest(customer_id=customer.id, request_type="deletion")
    db.add(row)
    db.flush()
    db.add(
        models.AuditEvent(
            actor=customer.email,
            reason="Customer deletion request",
            action="privacy_request",
            entity_type="customer",
            entity_id=customer.id,
            before_snapshot=None,
            after_snapshot={"request_id": row.id},
        )
    )
    db.commit()
    return {"id": row.id, "status": row.status}


@router.get("/account/privacy-requests")
def my_privacy_requests(customer: auth.CustomerDep, db: Db):
    rows = db.scalars(
        select(cm.PrivacyRequest)
        .where(cm.PrivacyRequest.customer_id == customer.id)
        .order_by(cm.PrivacyRequest.created_at.desc())
    ).all()
    return [
        {"id": row.id, "type": row.request_type, "status": row.status, "created_at": row.created_at}
        for row in rows
    ]


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Db):
    event = payment.verify_event(await request.body(), request.headers.get("stripe-signature"))
    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        raise HTTPException(400, "Malformed payment event")
    if db.get(cm.PaymentEvent, event_id):
        return {"received": True, "duplicate": True}
    ledger = cm.PaymentEvent(event_id=event_id, event_type=event_type)
    db.add(ledger)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}
    obj = event["data"]["object"]
    order_id = None
    if event_type.startswith("checkout.session.") and obj.get("mode") == "payment":
        order_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("order_id")
        order = loaded_order(db, order_id) if order_id else None
        if not order or (order.stripe_checkout_id and order.stripe_checkout_id != obj.get("id")):
            raise HTTPException(409, "Payment event does not match an order")
        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            if obj.get("payment_status") == "paid":
                if obj.get("currency", "").upper() != order.currency:
                    raise HTTPException(409, "Payment currency mismatch")
                if (obj.get("amount_total") or 0) < order.subtotal_cents:
                    raise HTTPException(409, "Payment amount mismatch")
                if not obj.get("payment_intent"):
                    raise HTTPException(409, "Payment reference is missing")
                details = obj.get("total_details") or {}
                shipping = obj.get("shipping_cost") or {}
                was_paid = order.payment_status in {"paid", "partially_refunded", "refunded"}
                service.mark_paid(
                    db,
                    order,
                    obj.get("payment_intent"),
                    obj.get("amount_total"),
                    details.get("amount_tax"),
                    shipping.get("amount_total"),
                    obj.get("shipping_details"),
                )
                if obj.get("customer"):
                    if (
                        order.customer.stripe_customer_id
                        and order.customer.stripe_customer_id != obj["customer"]
                    ):
                        raise HTTPException(409, "Payment customer mismatch")
                    order.customer.stripe_customer_id = obj["customer"]
                if not was_paid:
                    db.add(
                        cm.EmailOutbox(
                            recipient=order.customer.email,
                            template="order_confirmed",
                            payload={"order_id": order.id},
                        )
                    )
            elif order.payment_status not in {"paid", "partially_refunded", "refunded"}:
                order.status = "pending_payment"
        elif event_type in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
            service.release_reservation(db, order, "checkout_expired")
    elif event_type == "checkout.session.completed" and obj.get("mode") == "subscription":
        subscription_id = obj.get("subscription")
        if subscription_id:
            identity = payment.subscription_identity(subscription_id)
            metadata = identity["metadata"] or obj.get("metadata") or {}
            upsert_subscription(
                db, subscription_id, metadata, identity["customer"], identity["status"]
            )
    elif event_type.startswith("customer.subscription."):
        metadata = obj.get("metadata") or {}
        subscription = upsert_subscription(
            db,
            obj["id"],
            metadata,
            obj.get("customer"),
            obj.get("status", "incomplete"),
            obj.get("current_period_end"),
        )
        if subscription:
            subscription.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    elif event_type == "invoice.paid":
        order_id = fulfill_subscription_invoice(db, obj)
    elif event_type in {"refund.created", "refund.updated"}:
        refund = db.scalar(select(cm.Refund).where(cm.Refund.provider_refund_id == obj.get("id")))
        if not refund and (obj.get("metadata") or {}).get("internal_refund_id"):
            refund = db.get(cm.Refund, obj["metadata"]["internal_refund_id"])
        if refund:
            refund.provider_refund_id = obj["id"]
            refund.status = obj.get("status", refund.status)
            if refund.status == "succeeded":
                order = db.get(cm.Order, refund.order_id)
                succeeded = sum(
                    db.scalars(
                        select(cm.Refund.amount_cents).where(
                            cm.Refund.order_id == order.id, cm.Refund.status == "succeeded"
                        )
                    ).all()
                )
                order.payment_status = (
                    "refunded" if succeeded >= (order.total_cents or 0) else "partially_refunded"
                )
    ledger.order_id = order_id
    db.commit()
    return {"received": True}


@router.get("/products/{product_id}/impact")
def product_impact(product_id: str, db: Db):
    now = datetime.now(UTC)
    factors = db.scalars(
        select(cm.ImpactFactor).where(
            cm.ImpactFactor.product_id == product_id, cm.ImpactFactor.status == "approved"
        )
    ).all()
    return [
        {
            "metric_type": item.metric_type,
            "factor_value": str(item.factor_value),
            "unit": item.unit,
            "baseline": item.baseline,
            "comparison_scenario": item.comparison_scenario,
            "methodology_version": item.methodology_version,
            "source_reference": item.source_reference,
            "qualification": item.qualification,
        }
        for item in factors
        if (not item.valid_from or auth.utc(item.valid_from) <= now)
        and (not item.valid_to or auth.utc(item.valid_to) >= now)
    ]


@router.get("/account/subscriptions")
def my_subscriptions(customer: auth.CustomerDep, db: Db):
    rows = db.scalars(
        select(cm.Subscription).where(cm.Subscription.customer_id == customer.id)
    ).all()
    return [
        {
            "id": row.id,
            "product_id": row.product_id,
            "status": row.status,
            "current_period_end": row.current_period_end,
            "cancel_at_period_end": row.cancel_at_period_end,
        }
        for row in rows
    ]


@router.get("/capabilities")
def capabilities():
    return {
        "commerce_enabled": service.commerce_ready(),
        "subscriptions_enabled": service.commerce_ready() and settings.subscriptions_enabled,
    }


@router.post("/account/subscriptions/{product_id}/checkout")
def subscription_checkout(product_id: str, customer: auth.CsrfCustomer, db: Db):
    if not service.commerce_ready() or not settings.subscriptions_enabled:
        raise HTTPException(409, "Subscriptions are disabled")
    if not customer.email_verified_at:
        raise HTTPException(403, "Verify your email before checkout")
    product = db.get(models.Product, product_id)
    if not product or not product.refillable or not product.stripe_recurring_price_id:
        raise HTTPException(409, "This product has no approved subscription")
    errors = service.release_errors(db, product)
    if errors:
        raise HTTPException(409, {"release_errors": errors})
    session_id, url = payment.create_subscription_checkout(
        customer.stripe_customer_id,
        customer.email,
        customer.id,
        product.stripe_recurring_price_id,
        product.id,
    )
    return {"session_id": session_id, "checkout_url": url}


@router.post("/account/subscriptions/portal")
def subscription_portal(customer: auth.CsrfCustomer):
    if not customer.stripe_customer_id:
        raise HTTPException(409, "No billing account exists")
    return {"portal_url": payment.create_billing_portal(customer.stripe_customer_id)}


@router.get("/admin/orders")
def all_orders(_staff: Staff, db: Db):
    orders = db.scalars(
        select(cm.Order)
        .options(selectinload(cm.Order.items))
        .order_by(cm.Order.created_at.desc())
        .limit(100)
    ).all()
    return [order_view(order) | {"customer_id": order.customer_id} for order in orders]


@router.get("/admin/privacy-requests")
def all_privacy_requests(_staff: Staff, db: Db):
    if _staff.role != "admin":
        raise HTTPException(403, "Administrator access required")
    rows = db.scalars(
        select(cm.PrivacyRequest)
        .where(cm.PrivacyRequest.status.in_(["pending", "external_pending"]))
        .order_by(cm.PrivacyRequest.created_at)
        .limit(100)
    ).all()
    return [
        {
            "id": row.id,
            "customer_id": row.customer_id,
            "type": row.request_type,
            "status": row.status,
            "provider_customer_id": row.provider_customer_id,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/admin/privacy-requests/{request_id}/redact")
def redact_account(request_id: str, payload: PrivacyReviewIn, actor: Administrator, db: Db):
    privacy = db.scalar(
        select(cm.PrivacyRequest).where(cm.PrivacyRequest.id == request_id).with_for_update()
    )
    if not privacy or privacy.request_type != "deletion" or privacy.status != "pending":
        raise HTTPException(409, "Pending deletion request required")
    customer = db.get(cm.Customer, privacy.customer_id)
    if customer.role == "admin":
        admins = (
            db.scalar(
                select(func.count())
                .select_from(cm.Customer)
                .where(cm.Customer.role == "admin", cm.Customer.active.is_(True))
            )
            or 0
        )
        if admins <= 1:
            raise HTTPException(409, "The last administrator cannot be redacted")
    open_orders = db.scalars(select(cm.Order).where(cm.Order.customer_id == customer.id)).all()
    if any(
        order.status in {"pending_payment", "checkout_open", "paid_stock_hold"}
        or (
            order.payment_status in {"paid", "partially_refunded"}
            and order.fulfillment_status not in {"delivered", "cancelled"}
        )
        for order in open_orders
    ):
        raise HTTPException(409, "Fulfill or close active orders before redaction")
    subscriptions = db.scalars(
        select(cm.Subscription).where(cm.Subscription.customer_id == customer.id)
    ).all()
    if any(row.status not in {"canceled", "incomplete_expired"} for row in subscriptions):
        raise HTTPException(409, "Cancel subscriptions before redaction")
    pending_refunds = db.scalars(
        select(cm.Refund)
        .join(cm.Order)
        .where(cm.Order.customer_id == customer.id, cm.Refund.status == "pending")
    ).all()
    if pending_refunds:
        raise HTTPException(409, "Resolve pending refunds before redaction")
    prior_email = customer.email
    privacy.provider_customer_id = customer.stripe_customer_id
    db.execute(delete(models.IntentSignup).where(models.IntentSignup.email == prior_email))
    db.execute(delete(cm.EmailVerification).where(cm.EmailVerification.customer_id == customer.id))
    db.execute(delete(cm.PasswordReset).where(cm.PasswordReset.customer_id == customer.id))
    for row in db.scalars(select(cm.EmailOutbox).where(cm.EmailOutbox.recipient == prior_email)):
        if row.status == "pending":
            db.delete(row)
        else:
            row.recipient = "redacted@example.invalid"
            row.payload = {}
    for order in open_orders:
        order.shipping_snapshot = None
    customer.email = f"deleted-{customer.id}@example.invalid"
    customer.password_hash = auth.hasher.hash(secrets.token_urlsafe(48))
    customer.preferences = {}
    customer.stripe_customer_id = None
    customer.role = "customer"
    customer.active = False
    db.execute(
        update(cm.AuthSession)
        .where(cm.AuthSession.customer_id == customer.id)
        .values(revoked_at=datetime.now(UTC))
    )
    privacy.status = "external_pending" if privacy.provider_customer_id else "completed"
    privacy.evidence_reference = payload.evidence_reference
    privacy.processed_at = datetime.now(UTC)
    audit(
        db,
        actor,
        "privacy_redaction",
        "customer",
        customer.id,
        payload.reason,
        {"active": True},
        {"active": False, "provider_followup": bool(privacy.provider_customer_id)},
    )
    db.commit()
    return {"id": privacy.id, "status": privacy.status}


@router.post("/admin/privacy-requests/{request_id}/complete")
def complete_external_deletion(
    request_id: str, payload: PrivacyReviewIn, actor: Administrator, db: Db
):
    privacy = db.get(cm.PrivacyRequest, request_id)
    if not privacy or privacy.status != "external_pending":
        raise HTTPException(409, "External provider follow-up is not pending")
    privacy.status = "completed"
    privacy.evidence_reference = payload.evidence_reference
    privacy.provider_customer_id = None
    privacy.processed_at = datetime.now(UTC)
    audit(
        db,
        actor,
        "privacy_external_completion",
        "customer",
        privacy.customer_id,
        payload.reason,
        {"status": "external_pending"},
        {"status": "completed", "evidence_reference": payload.evidence_reference},
    )
    db.commit()
    return {"id": privacy.id, "status": privacy.status}


@router.get("/admin/products")
def admin_products(_staff: Staff, db: Db):
    products = db.scalars(select(models.Product).order_by(models.Product.brew_number)).all()
    rows = []
    for product in products:
        inventory = db.scalar(
            select(cm.InventoryItem).where(cm.InventoryItem.product_id == product.id)
        )
        approvals = db.scalars(
            select(cm.ProductReleaseApproval).where(
                cm.ProductReleaseApproval.product_id == product.id
            )
        ).all()
        rows.append(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "availability_status": product.availability_status,
                "release_errors": service.release_errors(db, product, require_published=False),
                "inventory": {
                    "sku": inventory.sku,
                    "on_hand": inventory.on_hand,
                    "reserved": inventory.reserved,
                    "available": inventory.available,
                }
                if inventory
                else None,
                "approvals": [
                    {
                        "gate": a.gate,
                        "status": a.status,
                        "evidence_reference": a.evidence_reference,
                        "reviewer": a.reviewer,
                    }
                    for a in approvals
                ],
            }
        )
    return rows


@router.patch("/admin/staff/role")
def change_staff_role(payload: StaffRoleIn, actor: Administrator, db: Db):
    customer = db.scalar(select(cm.Customer).where(cm.Customer.email == payload.email.lower()))
    if not customer:
        raise HTTPException(404, "Account not found")
    if customer.role == "admin" and payload.role != "admin":
        admins = (
            db.scalar(
                select(func.count())
                .select_from(cm.Customer)
                .where(cm.Customer.role == "admin", cm.Customer.active.is_(True))
            )
            or 0
        )
        if admins <= 1:
            raise HTTPException(409, "The last administrator cannot be demoted")
    before = customer.role
    customer.role = payload.role
    db.execute(
        update(cm.AuthSession)
        .where(cm.AuthSession.customer_id == customer.id)
        .values(revoked_at=datetime.now(UTC))
    )
    audit(
        db,
        actor,
        "role_change",
        "customer",
        customer.id,
        payload.reason,
        {"role": before},
        {"role": customer.role},
    )
    db.commit()
    return {"id": customer.id, "email": customer.email, "role": customer.role}


@router.get("/admin/products/{product_id}/evidence")
def product_evidence(product_id: str, _staff: Staff, db: Db):
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    formulations = db.scalars(
        select(models.FormulationVersion).where(models.FormulationVersion.product_id == product_id)
    ).all()
    claims = db.scalars(
        select(models.ClaimEvidence).where(models.ClaimEvidence.product_id == product_id)
    ).all()
    impacts = db.scalars(
        select(cm.ImpactFactor).where(cm.ImpactFactor.product_id == product_id)
    ).all()
    return {
        "formulations": [
            {
                "id": row.id,
                "version_label": row.version_label,
                "status": row.status,
                "safety_document_reference": row.safety_document_reference,
            }
            for row in formulations
        ],
        "claims": [
            {
                "id": row.id,
                "claim_text": row.claim_text,
                "status": row.status,
                "source_reference": row.source_reference,
            }
            for row in claims
        ],
        "impacts": [
            {
                "id": row.id,
                "metric_type": row.metric_type,
                "status": row.status,
                "source_reference": row.source_reference,
            }
            for row in impacts
        ],
    }


@router.patch("/admin/orders/{order_id}/fulfillment")
def fulfill(order_id: str, payload: FulfillmentIn, actor: Operator, db: Db):
    order = loaded_order(db, order_id)
    if (
        not order
        or order.status != "paid"
        or order.payment_status not in {"paid", "partially_refunded"}
    ):
        raise HTTPException(409, "Paid order required")
    before = order.fulfillment_status
    order.fulfillment_status = payload.status
    if payload.status == "delivered":
        order.fulfilled_at = datetime.now(UTC)
    audit(
        db,
        actor,
        "fulfillment_update",
        "order",
        order.id,
        payload.reason,
        {"status": before},
        {"status": payload.status},
    )
    db.commit()
    return order_view(order)


@router.post("/admin/orders/{order_id}/allocate")
def allocate_stock_hold(order_id: str, actor: Operator, db: Db):
    order = loaded_order(db, order_id)
    if not order or order.status != "paid_stock_hold" or not order.subscription_id:
        raise HTTPException(409, "Paid subscription stock hold required")
    subscription = db.get(cm.Subscription, order.subscription_id)
    product = db.get(models.Product, subscription.product_id)
    errors = service.release_errors(db, product)
    if errors:
        raise HTTPException(409, {"release_errors": errors})
    inventory = db.scalar(
        select(cm.InventoryItem).where(cm.InventoryItem.product_id == product.id).with_for_update()
    )
    if not inventory or inventory.available < 1:
        raise HTTPException(409, "No available inventory")
    formulation = service.approved_formulation(db, product.id)
    if order.items:
        item = order.items[0]
        item.inventory_item_id = inventory.id
        item.sku = inventory.sku
        item.formulation_version_id = formulation.id
    else:
        order.items.append(
            cm.OrderItem(
                product_id=product.id,
                inventory_item_id=inventory.id,
                product_name=product.name,
                sku=inventory.sku,
                quantity=1,
                unit_price_cents=product.price_cents,
                currency="USD",
                formulation_version_id=formulation.id,
            )
        )
    inventory.on_hand -= 1
    order.status = "paid"
    order.fulfillment_status = "unfulfilled"
    db.add(
        cm.InventoryMovement(
            inventory_item_id=inventory.id,
            order_id=order.id,
            delta_on_hand=-1,
            reason="allocate paid refill order",
            actor=actor.email,
        )
    )
    audit(
        db,
        actor,
        "allocate_stock_hold",
        "order",
        order.id,
        "Inventory replenished and release gates checked",
        {"status": "paid_stock_hold"},
        {"status": "paid"},
    )
    db.add(
        cm.EmailOutbox(
            recipient=order.customer.email,
            template="order_confirmed",
            payload={"order_id": order.id},
        )
    )
    db.commit()
    return order_view(order)


@router.put("/admin/products/{product_id}/inventory")
def adjust_inventory(product_id: str, payload: InventoryIn, actor: Operator, db: Db):
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    item = db.scalar(
        select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id).with_for_update()
    )
    if item is None:
        if payload.adjustment < 0:
            raise HTTPException(409, "Inventory cannot be negative")
        item = cm.InventoryItem(product_id=product_id, sku=payload.sku, on_hand=0, reserved=0)
        db.add(item)
        db.flush()
    if item.sku != payload.sku or item.on_hand + payload.adjustment < item.reserved:
        raise HTTPException(409, "SKU mismatch or adjustment would violate reservations")
    before = item.on_hand
    item.on_hand += payload.adjustment
    item.low_stock_threshold = payload.low_stock_threshold
    db.add(
        cm.InventoryMovement(
            inventory_item_id=item.id,
            delta_on_hand=payload.adjustment,
            reason=payload.reason,
            actor=actor.email,
        )
    )
    audit(
        db,
        actor,
        "inventory_adjustment",
        "inventory_item",
        item.id,
        payload.reason,
        {"on_hand": before},
        {"on_hand": item.on_hand},
    )
    db.commit()
    return {
        "sku": item.sku,
        "on_hand": item.on_hand,
        "reserved": item.reserved,
        "available": item.available,
    }


@router.get("/admin/products/{product_id}/release")
def release_status(product_id: str, _staff: Staff, db: Db):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return {
        "ready": not service.release_errors(db, product, require_published=False),
        "errors": service.release_errors(db, product, require_published=False),
    }


@router.put("/admin/products/{product_id}/release/{gate}")
def approve_gate(product_id: str, gate: str, payload: ApprovalIn, actor: Operator, db: Db):
    if gate not in service.RELEASE_GATES:
        raise HTTPException(422, "Unknown release gate")
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    record = db.scalar(
        select(cm.ProductReleaseApproval).where(
            cm.ProductReleaseApproval.product_id == product_id,
            cm.ProductReleaseApproval.gate == gate,
        )
    )
    if not record:
        record = cm.ProductReleaseApproval(product_id=product_id, gate=gate)
        db.add(record)
    before = {"status": record.status, "evidence_reference": record.evidence_reference}
    record.status = payload.status
    record.evidence_reference = payload.evidence_reference
    record.reviewer = actor.email
    record.reviewed_at = datetime.now(UTC)
    audit(
        db,
        actor,
        "release_gate_review",
        "product",
        product_id,
        payload.reason,
        before,
        {"gate": gate, "status": payload.status, "evidence_reference": payload.evidence_reference},
    )
    db.commit()
    return {"gate": gate, "status": record.status}


@router.patch("/admin/formulations/{formulation_id}/review")
def review_formulation(formulation_id: str, payload: FormulationReviewIn, actor: Operator, db: Db):
    record = db.get(models.FormulationVersion, formulation_id)
    if not record or (payload.status == "approved" and not record.safety_document_reference):
        raise HTTPException(409, "Formulation and safety evidence are required")
    before = record.status
    record.status = payload.status
    record.approved_by = actor.email if payload.status == "approved" else None
    record.effective_at = datetime.now(UTC) if payload.status == "approved" else None
    audit(
        db,
        actor,
        "formulation_review",
        "formulation",
        record.id,
        payload.reason,
        {"status": before},
        {"status": payload.status},
    )
    db.commit()
    return {"id": record.id, "status": record.status}


@router.patch("/admin/claims/{claim_id}/review")
def review_claim(claim_id: str, payload: ApprovalIn, actor: Operator, db: Db):
    record = db.get(models.ClaimEvidence, claim_id)
    if not record:
        raise HTTPException(404, "Claim not found")
    before = record.status
    record.status = payload.status
    record.reviewer = actor.email
    record.review_date = datetime.now(UTC)
    record.source_reference = payload.evidence_reference
    audit(
        db,
        actor,
        "claim_review",
        "claim_evidence",
        record.id,
        payload.reason,
        {"status": before},
        {"status": payload.status},
    )
    db.commit()
    return {"id": record.id, "status": record.status}


@router.post("/admin/products/{product_id}/impact")
def add_impact(product_id: str, payload: ImpactIn, actor: Operator, db: Db):
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    record = cm.ImpactFactor(product_id=product_id, **payload.model_dump())
    db.add(record)
    db.flush()
    audit(
        db,
        actor,
        "impact_draft",
        "impact_factor",
        record.id,
        "New impact methodology draft",
        None,
        payload.model_dump(mode="json"),
    )
    db.commit()
    return {"id": record.id, "status": record.status}


@router.patch("/admin/impact/{impact_id}/review")
def review_impact(impact_id: str, payload: ApprovalIn, actor: Operator, db: Db):
    record = db.get(cm.ImpactFactor, impact_id)
    if not record:
        raise HTTPException(404, "Impact factor not found")
    before = record.status
    record.status = payload.status
    record.reviewer = actor.email
    record.reviewed_at = datetime.now(UTC)
    audit(
        db,
        actor,
        "impact_review",
        "impact_factor",
        record.id,
        payload.reason,
        {"status": before},
        {"status": record.status, "evidence_reference": payload.evidence_reference},
    )
    db.commit()
    return {"id": record.id, "status": record.status}


@router.post("/admin/orders/{order_id}/refunds")
def refund_order(order_id: str, payload: RefundIn, actor: Operator, db: Db):
    order = loaded_order(db, order_id)
    if (
        not order
        or order.payment_status not in {"paid", "partially_refunded"}
        or not order.stripe_payment_intent_id
    ):
        raise HTTPException(409, "A paid order with a payment reference is required")
    refunded = sum(
        db.scalars(
            select(cm.Refund.amount_cents).where(
                cm.Refund.order_id == order.id, cm.Refund.status.in_(["pending", "succeeded"])
            )
        ).all()
    )
    if payload.amount_cents > (order.total_cents or 0) - refunded:
        raise HTTPException(409, "Refund exceeds remaining paid amount")
    record = cm.Refund(order_id=order.id, amount_cents=payload.amount_cents, reason=payload.reason)
    db.add(record)
    db.flush()
    db.commit()
    try:
        result = payment.create_refund(
            order.stripe_payment_intent_id, payload.amount_cents, record.id
        )
    except Exception:
        record.status = "failed"
        db.commit()
        raise
    record.provider_refund_id = result.id
    record.status = result.status
    if record.status == "succeeded":
        succeeded = sum(
            db.scalars(
                select(cm.Refund.amount_cents).where(
                    cm.Refund.order_id == order.id, cm.Refund.status == "succeeded"
                )
            ).all()
        )
        order.payment_status = (
            "refunded" if succeeded >= (order.total_cents or 0) else "partially_refunded"
        )
    audit(
        db,
        actor,
        "refund",
        "order",
        order.id,
        payload.reason,
        None,
        {"refund_id": record.id, "amount_cents": payload.amount_cents},
    )
    db.commit()
    return {"id": record.id, "status": record.status}
