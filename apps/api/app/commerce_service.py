"""Release validation and transactional order state transitions."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import commerce_models as cm
from app import models
from app.config import settings

RELEASE_GATES = {
    "formulation",
    "safety",
    "label",
    "claims",
    "shipping",
    "tax",
    "fulfillment",
    "support",
}


def commerce_ready() -> bool:
    if not settings.commerce_enabled:
        return False
    if (
        settings.environment == "local"
        and settings.web_origin.startswith("http://localhost")
        and settings.public_web_url.startswith("http://localhost")
    ):
        return bool(
            settings.local_test_commerce
            and settings.stripe_secret_key.startswith("sk_test_")
            and settings.stripe_webhook_secret
            and settings.stripe_shipping_rate_id
        )
    return bool(
        settings.launch_approval_reference
        and settings.support_email
        and settings.terms_url.startswith("https://")
        and settings.refund_policy_url.startswith("https://")
        and settings.public_web_url.startswith("https://")
        and settings.web_origin.startswith("https://")
        and settings.stripe_secret_key
        and settings.stripe_webhook_secret
        and settings.stripe_shipping_rate_id
        and settings.smtp_host
        and settings.smtp_starttls
        and settings.smtp_from
        and settings.operations_email
    )


def approved_formulation(db: Session, product_id: str) -> models.FormulationVersion | None:
    return db.scalar(
        select(models.FormulationVersion)
        .where(
            models.FormulationVersion.product_id == product_id,
            models.FormulationVersion.status == "approved",
        )
        .order_by(models.FormulationVersion.created_at.desc())
    )


def release_errors(
    db: Session, product: models.Product, *, require_published: bool = True
) -> list[str]:
    errors: list[str] = []
    if not product.active or (require_published and product.availability_status != "available"):
        errors.append("Product is not published for sale")
    if product.price_cents <= 0 or product.currency != "USD":
        errors.append("Price or currency is not approved")
    final_copy = {
        "description": product.description,
        "subtitle": product.subtitle,
        "product type": product.product_type,
        "unit size": product.unit_size,
        "ingredients": ", ".join(product.ingredients),
        "usage instructions": product.usage_instructions,
        "warnings": product.warnings,
        "storage instructions": product.storage_instructions,
        "packaging": product.packaging,
        "shipping details": product.shipping_details,
    }
    placeholders = (
        "pending",
        "under review",
        "proposed",
        "concept",
        "to be confirmed",
        "unconfirmed",
        "unverified",
        "not tested",
        "not approved",
        "not available during",
    )
    for field, value in final_copy.items():
        if not value.strip() or any(marker in value.lower() for marker in placeholders):
            errors.append(f"{field.capitalize()} are not final")
    formulation = approved_formulation(db, product.id)
    if not formulation or not formulation.safety_document_reference:
        errors.append("Approved formulation and safety document are required")
    approvals = db.scalars(
        select(cm.ProductReleaseApproval).where(
            cm.ProductReleaseApproval.product_id == product.id,
            cm.ProductReleaseApproval.status == "approved",
        )
    ).all()
    approved = {record.gate for record in approvals if record.evidence_reference}
    missing = RELEASE_GATES - approved
    if missing:
        errors.append("Missing release gates: " + ", ".join(sorted(missing)))
    inventory = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product.id))
    if not inventory or inventory.available <= 0:
        errors.append("No available inventory")
    return errors


def reserve_inventory(db: Session, order: cm.Order) -> None:
    for item in sorted(order.items, key=lambda entry: entry.inventory_item_id):
        inventory = db.scalar(
            select(cm.InventoryItem)
            .where(cm.InventoryItem.id == item.inventory_item_id)
            .with_for_update()
        )
        if not inventory or inventory.available < item.quantity:
            raise HTTPException(409, f"Insufficient inventory for {item.sku}")
        inventory.reserved += item.quantity
        db.add(
            cm.InventoryMovement(
                inventory_item_id=inventory.id,
                order_id=order.id,
                delta_reserved=item.quantity,
                reason="checkout reservation",
                actor="system",
            )
        )


def release_reservation(db: Session, order: cm.Order, status: str) -> None:
    if order.status not in {"pending_payment", "checkout_open"}:
        return
    for item in order.items:
        inventory = db.scalar(
            select(cm.InventoryItem)
            .where(cm.InventoryItem.id == item.inventory_item_id)
            .with_for_update()
        )
        if inventory and inventory.reserved >= item.quantity:
            inventory.reserved -= item.quantity
            db.add(
                cm.InventoryMovement(
                    inventory_item_id=inventory.id,
                    order_id=order.id,
                    delta_reserved=-item.quantity,
                    reason=status,
                    actor="system",
                )
            )
    order.status = status
    order.payment_status = "unpaid"


def mark_paid(
    db: Session,
    order: cm.Order,
    payment_intent_id: str | None,
    total_cents: int | None,
    tax_cents: int | None,
    shipping_cents: int | None,
    shipping_snapshot: dict | None,
) -> None:
    if order.payment_status in {"paid", "partially_refunded", "refunded"}:
        return
    if order.status not in {"checkout_open", "pending_payment"}:
        raise HTTPException(409, "Order is not awaiting payment")
    for item in order.items:
        inventory = db.scalar(
            select(cm.InventoryItem)
            .where(cm.InventoryItem.id == item.inventory_item_id)
            .with_for_update()
        )
        if not inventory or inventory.reserved < item.quantity or inventory.on_hand < item.quantity:
            raise HTTPException(409, "Inventory reservation mismatch")
        inventory.reserved -= item.quantity
        inventory.on_hand -= item.quantity
        db.add(
            cm.InventoryMovement(
                inventory_item_id=inventory.id,
                order_id=order.id,
                delta_on_hand=-item.quantity,
                delta_reserved=-item.quantity,
                reason="payment confirmed",
                actor="payment webhook",
            )
        )
    order.status = "paid"
    order.payment_status = "paid"
    order.paid_at = datetime.now(UTC)
    order.stripe_payment_intent_id = payment_intent_id
    order.total_cents = total_cents
    order.tax_cents = tax_cents
    order.shipping_cents = shipping_cents
    order.shipping_snapshot = shipping_snapshot
