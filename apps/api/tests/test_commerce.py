"""Exercise release gates, authenticated checkout, stock, and webhook replay."""

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from app import auth, jobs, models, payment
from app import commerce_models as cm
from app.config import settings


def register_verified(http, local, email="buyer@example.com"):
    response = http.post(
        "/api/v1/auth/register", json={"email": email, "password": "a-long-test-password"}
    )
    assert response.status_code == 201, response.text
    with local() as db:
        customer = db.scalar(select(cm.Customer).where(cm.Customer.email == email))
        customer.email_verified_at = datetime.now(UTC)
        db.commit()
    return {"X-CSRF-Token": http.cookies["brew67_csrf"]}


def prepare_product(local):
    with local() as db:
        product = db.scalar(
            select(models.Product).where(models.Product.slug == "tri-realm-catalyst")
        )
        product.unit_size = "500 mL"
        product.usage_instructions = "Follow the approved label on general surfaces."
        product.description = "A concentrated general surface cleaner for approved household use."
        product.subtitle = "Brew No. 67 · General surface cleaner"
        product.product_type = "home care"
        product.ingredients = ["Water", "Reviewed surfactant"]
        product.warnings = "Keep away from children and eyes."
        product.storage_instructions = "Store sealed at room temperature."
        product.packaging = "Reusable bottle with a recyclable paper carton."
        product.shipping_details = "Ships within the United States by ground carrier."
        product.availability_status = "available"
        formulation = models.FormulationVersion(
            product_id=product.id,
            version_label="production-1",
            status="approved",
            ingredients=["approved test ingredient"],
            safety_document_reference="evidence:safety-review",
            approved_by="reviewer",
        )
        db.add(formulation)
        inventory = cm.InventoryItem(product_id=product.id, sku="BREW-67", on_hand=5, reserved=0)
        db.add(inventory)
        for gate in [
            "formulation",
            "safety",
            "label",
            "claims",
            "shipping",
            "tax",
            "fulfillment",
            "support",
        ]:
            db.add(
                cm.ProductReleaseApproval(
                    product_id=product.id,
                    gate=gate,
                    status="approved",
                    evidence_reference=f"evidence:{gate}",
                    reviewer="reviewer",
                )
            )
        db.commit()
        return product.id


def cart_with_product(http, product_id):
    cart = http.post("/api/v1/carts", json={}).json()
    response = http.post(
        f"/api/v1/carts/{cart['id']}/items",
        headers={"X-Cart-Token": cart["token"]},
        json={"product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 200
    return cart


def test_account_session_csrf_and_private_orders(client):
    http, local = client
    anonymous = http.get("/api/v1/auth/me")
    assert anonymous.status_code == 401
    assert anonymous.headers["cache-control"] == "no-store"
    assert len(anonymous.headers["x-request-id"]) == 16
    headers = register_verified(http, local)
    assert http.get("/api/v1/auth/me").json()["email"] == "buyer@example.com"
    assert (
        http.patch("/api/v1/auth/preferences", json={"preferred_biome": "forest"}).status_code
        == 403
    )
    assert (
        http.patch(
            "/api/v1/auth/preferences", headers=headers, json={"preferred_biome": "forest"}
        ).status_code
        == 200
    )
    assert http.get("/api/v1/account/orders").json() == []
    assert http.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert http.get("/api/v1/auth/me").status_code == 401


def test_release_gate_blocks_checkout_even_with_flag(client, monkeypatch):
    http, local = client
    monkeypatch.setattr(settings, "commerce_enabled", True)
    headers = register_verified(http, local)
    product = http.get("/api/v1/products/tri-realm-catalyst").json()
    cart = cart_with_product(http, product["id"])
    response = http.post(
        "/api/v1/checkout/session",
        headers=headers,
        json={"cart_id": cart["id"], "cart_token": cart["token"]},
    )
    assert response.status_code == 409
    assert "release_errors" in response.json()["detail"]
    with local() as db:
        assert db.scalars(select(cm.Order)).all() == []


def test_production_checkout_fails_closed_without_launch_approval(client, monkeypatch):
    http, local = client
    product_id = prepare_product(local)
    cart = cart_with_product(http, product_id)
    register_verified(http, local)
    monkeypatch.setattr(settings, "commerce_enabled", True)
    monkeypatch.setattr(settings, "environment", "production")
    assert http.get("/api/v1/capabilities").json()["commerce_enabled"] is False
    response = http.post(
        "/api/v1/checkout/session",
        json={"cart_id": cart["id"], "cart_token": cart["token"]},
    )
    assert response.status_code == 409
    with local() as db:
        assert db.scalars(select(cm.Order)).all() == []


def test_impact_estimates_require_approved_factor_and_delivered_purchase(client):
    http, local = client
    product_id = prepare_product(local)
    assert http.get("/api/v1/account/impact").status_code == 401
    register_verified(http, local)
    with local() as db:
        customer = db.scalar(select(cm.Customer).where(cm.Customer.email == "buyer@example.com"))
        inventory = db.scalar(
            select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id)
        )
        order = cm.Order(
            customer_id=customer.id,
            status="paid",
            payment_status="paid",
            fulfillment_status="delivered",
            subtotal_cents=6800,
            fulfilled_at=datetime.now(UTC),
        )
        order.items.append(
            cm.OrderItem(
                product_id=product_id,
                inventory_item_id=inventory.id,
                product_name="The Tri-Realm Catalyst",
                sku=inventory.sku,
                quantity=2,
                unit_price_cents=3400,
            )
        )
        db.add(order)
        db.add(
            cm.ImpactFactor(
                product_id=product_id,
                metric_type="packaging mass difference",
                factor_value=Decimal("0.250000"),
                unit="kg",
                baseline="Conventional bottle packaging for one unit",
                comparison_scenario="Approved refill packaging for one unit",
                methodology_version="v1",
                source_reference="evidence:packaging-weighing",
                qualification="Modeled from reviewed packaging masses only",
                status="approved",
                valid_from=datetime.now(UTC) - timedelta(days=1),
            )
        )
        db.add(
            cm.ImpactFactor(
                product_id=product_id,
                metric_type="unreviewed metric",
                factor_value=Decimal("2.000000"),
                unit="kg",
                baseline="Unreviewed baseline packaging mass",
                comparison_scenario="Unreviewed comparison packaging mass",
                methodology_version="draft",
                source_reference="internal:draft",
                qualification="This has not been reviewed",
                status="draft",
            )
        )
        db.commit()
    response = http.get("/api/v1/account/impact")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert Decimal(response.json()[0]["estimated_value"]) == Decimal("0.5")
    assert response.json()[0]["units_counted"] == 2
    assert response.json()[0]["estimate_kind"] == "modeled estimate"
    with local() as db:
        order = db.scalar(select(cm.Order))
        order.payment_status = "refunded"
        db.commit()
    assert http.get("/api/v1/account/impact").json() == []


def test_checkout_webhook_idempotency_and_inventory(client, monkeypatch):
    http, local = client
    monkeypatch.setattr(settings, "commerce_enabled", True)
    headers = register_verified(http, local)
    product_id = prepare_product(local)
    cart = cart_with_product(http, product_id)
    monkeypatch.setattr(
        payment, "create_checkout", lambda *args: ("cs_test_1", "https://checkout.example/1")
    )
    payload = {"cart_id": cart["id"], "cart_token": cart["token"]}
    assert http.post("/api/v1/checkout/session", json=payload).status_code == 403
    response = http.post("/api/v1/checkout/session", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    order_id = response.json()["order_id"]
    assert (
        http.post("/api/v1/checkout/session", headers=headers, json=payload).json()["order_id"]
        == order_id
    )
    with local() as db:
        stock = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id))
        assert (stock.on_hand, stock.reserved) == (5, 2)
    event = {
        "id": "evt_paid_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "mode": "payment",
                "client_reference_id": order_id,
                "payment_status": "paid",
                "payment_intent": "pi_test_1",
                "currency": "usd",
                "amount_total": 10000,
                "total_details": {"amount_tax": 0},
                "shipping_cost": {"amount_total": 0},
                "customer": "cus_test_1",
            }
        },
    }
    monkeypatch.setattr(payment, "verify_event", lambda *args: event)
    assert http.post("/api/v1/webhooks/stripe").status_code == 200
    assert http.post("/api/v1/webhooks/stripe").json()["duplicate"] is True
    with local() as db:
        stock = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id))
        assert (stock.on_hand, stock.reserved) == (3, 0)
        assert db.get(cm.Order, order_id).payment_status == "paid"
    assert http.get(f"/api/v1/account/orders/{order_id}").json()["payment_status"] == "paid"
    with local() as db:
        customer = db.scalar(select(cm.Customer).where(cm.Customer.email == "buyer@example.com"))
        customer.role = "operations"
        db.commit()
    metrics = http.get("/api/v1/admin/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["orders_by_status"]["paid"] == 1
    assert metrics.json()["processed_payment_events"] >= 1
    monkeypatch.setattr(
        payment, "create_refund", lambda *args: SimpleNamespace(id="re_1", status="succeeded")
    )
    refund = http.post(
        f"/api/v1/admin/orders/{order_id}/refunds",
        headers=headers,
        json={"amount_cents": 2500, "reason": "Customer return accepted"},
    )
    assert refund.status_code == 200, refund.text
    assert (
        http.get(f"/api/v1/account/orders/{order_id}").json()["payment_status"]
        == "partially_refunded"
    )
    event["id"] = "evt_paid_again"
    assert http.post("/api/v1/webhooks/stripe").status_code == 200
    with local() as db:
        stock = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id))
        assert stock.on_hand == 3
    http.cookies.clear()
    register_verified(http, local, "other@example.com")
    assert http.get(f"/api/v1/account/orders/{order_id}").status_code == 404


def test_checkout_failure_releases_reserved_stock(client, monkeypatch):
    http, local = client
    monkeypatch.setattr(settings, "commerce_enabled", True)
    headers = register_verified(http, local)
    product_id = prepare_product(local)
    cart = cart_with_product(http, product_id)

    def failed(*args):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(payment, "create_checkout", failed)
    try:
        http.post(
            "/api/v1/checkout/session",
            headers=headers,
            json={"cart_id": cart["id"], "cart_token": cart["token"]},
        )
    except RuntimeError:
        pass
    with local() as db:
        stock = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id))
        assert stock.reserved == 0
        assert db.scalar(select(cm.Order)).status == "checkout_failed"


def test_expired_checkout_reconciles_provider_before_releasing_stock(client, monkeypatch):
    http, local = client
    monkeypatch.setattr(settings, "commerce_enabled", True)
    headers = register_verified(http, local)
    product_id = prepare_product(local)
    cart = cart_with_product(http, product_id)
    monkeypatch.setattr(
        payment, "create_checkout", lambda *args: ("cs_expiring", "https://checkout.example/x")
    )
    response = http.post(
        "/api/v1/checkout/session",
        headers=headers,
        json={"cart_id": cart["id"], "cart_token": cart["token"]},
    )
    assert response.status_code == 200
    with local() as db:
        order = db.get(cm.Order, response.json()["order_id"])
        order.reservation_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    monkeypatch.setattr(jobs, "SessionLocal", local)
    monkeypatch.setattr(payment, "checkout_state", lambda *_: ("complete", "paid"))
    assert jobs.reconcile_expired_checkouts() == 0
    with local() as db:
        assert db.scalar(select(cm.InventoryItem)).reserved == 2
    monkeypatch.setattr(payment, "checkout_state", lambda *_: ("expired", "unpaid"))
    assert jobs.reconcile_expired_checkouts() == 1
    with local() as db:
        assert db.scalar(select(cm.InventoryItem)).reserved == 0
        assert db.get(cm.Order, response.json()["order_id"]).status == "checkout_expired"


def test_subscription_invoice_creates_fulfillable_order_and_stock_hold(client, monkeypatch):
    http, local = client
    monkeypatch.setattr(settings, "commerce_enabled", True)
    monkeypatch.setattr(settings, "subscriptions_enabled", True)
    headers = register_verified(http, local)
    product_id = prepare_product(local)
    with local() as db:
        product = db.get(models.Product, product_id)
        product.refillable = True
        product.stripe_recurring_price_id = "price_refill_test"
        customer = db.scalar(select(cm.Customer).where(cm.Customer.email == "buyer@example.com"))
        customer_id = customer.id
        db.commit()
    monkeypatch.setattr(
        payment,
        "create_subscription_checkout",
        lambda *args: ("cs_sub_1", "https://checkout.example/sub"),
    )
    response = http.post(f"/api/v1/account/subscriptions/{product_id}/checkout", headers=headers)
    assert response.status_code == 200, response.text
    event = {
        "id": "evt_sub_1",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_1",
                "metadata": {"account_id": customer_id, "product_id": product_id},
                "customer": "cus_sub_1",
                "status": "active",
                "current_period_end": 1800000000,
            }
        },
    }
    monkeypatch.setattr(payment, "verify_event", lambda *args: event)
    assert http.post("/api/v1/webhooks/stripe").status_code == 200
    assert len(http.get("/api/v1/account/subscriptions").json()) == 1
    event = {
        "id": "evt_invoice_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_1",
                "billing_reason": "subscription_cycle",
                "status": "paid",
                "currency": "usd",
                "amount_paid": 1500,
                "subtotal": 1400,
                "total": 1500,
                "total_excluding_tax": 1400,
                "amount_shipping": 0,
                "customer": "cus_sub_1",
                "parent": {"subscription_details": {"subscription": "sub_1"}},
            }
        },
    }
    assert http.post("/api/v1/webhooks/stripe").status_code == 200
    assert http.post("/api/v1/webhooks/stripe").json()["duplicate"] is True
    with local() as db:
        stock = db.scalar(select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id))
        assert (stock.on_hand, stock.reserved) == (4, 0)
        order = db.scalar(select(cm.Order).where(cm.Order.stripe_invoice_id == "in_1"))
        assert order.status == "paid" and order.source == "subscription"
        stock.on_hand = 0
        db.commit()
    event = {
        "id": "evt_invoice_2",
        "type": "invoice.paid",
        "data": {
            "object": {
                **event["data"]["object"],
                "id": "in_2",
            }
        },
    }
    assert http.post("/api/v1/webhooks/stripe").status_code == 200
    with local() as db:
        held = db.scalar(select(cm.Order).where(cm.Order.stripe_invoice_id == "in_2"))
        assert held.status == "paid_stock_hold" and held.fulfillment_status == "hold"
        customer = db.get(cm.Customer, customer_id)
        customer.role = "operations"
        db.commit()
        held_id = held.id
    stock_update = http.put(
        f"/api/v1/admin/products/{product_id}/inventory",
        headers=headers,
        json={
            "sku": "BREW-67",
            "adjustment": 2,
            "low_stock_threshold": 0,
            "reason": "Replenished test stock",
        },
    )
    assert stock_update.status_code == 200, stock_update.text
    allocated = http.post(f"/api/v1/admin/orders/{held_id}/allocate", headers=headers)
    assert allocated.status_code == 200, allocated.text
    with local() as db:
        assert (
            db.scalar(
                select(cm.InventoryItem).where(cm.InventoryItem.product_id == product_id)
            ).on_hand
            == 1
        )


def test_login_lockout_and_staff_role_guard(client):
    http, local = client
    register_verified(http, local)
    for _ in range(5):
        assert (
            http.post(
                "/api/v1/auth/login",
                json={"email": "buyer@example.com", "password": "wrong-password"},
            ).status_code
            == 401
        )
    assert (
        http.post(
            "/api/v1/auth/login",
            json={"email": "buyer@example.com", "password": "a-long-test-password"},
        ).status_code
        == 429
    )
    headers = {"X-CSRF-Token": http.cookies["brew67_csrf"]}
    assert (
        http.patch(
            "/api/v1/admin/staff/role",
            headers=headers,
            json={
                "email": "buyer@example.com",
                "role": "admin",
                "reason": "Unauthorized promotion",
            },
        ).status_code
        == 403
    )


def test_stripe_signature_verification_rejects_tampering(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_placeholder")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")
    payload = json.dumps({"id": "evt_test", "type": "ping"}).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        b"whsec_test_secret", f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    header = f"t={timestamp},v1={signature}"
    assert payment.verify_event(payload, header)["id"] == "evt_test"
    try:
        payment.verify_event(payload + b" ", header)
    except HTTPException as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Tampered webhook was accepted")


def test_privacy_export_request_and_operator_redaction(client):
    http, local = client
    headers = register_verified(http, local)
    http.post(
        "/api/v1/intent-signups",
        json={"email": "buyer@example.com", "contact_consent": True, "marketing_consent": False},
    )
    exported = http.get("/api/v1/account/privacy-export")
    assert exported.status_code == 200
    assert exported.json()["interest_signups"][0]["interest"] == "general"
    assert (
        http.post(
            "/api/v1/account/privacy-requests", headers=headers, json={"password": "wrong"}
        ).status_code
        == 403
    )
    requested = http.post(
        "/api/v1/account/privacy-requests",
        headers=headers,
        json={"password": "a-long-test-password"},
    )
    assert requested.status_code == 202
    request_id = requested.json()["id"]
    with local() as db:
        buyer = db.scalar(select(cm.Customer).where(cm.Customer.email == "buyer@example.com"))
        buyer.stripe_customer_id = "cus_privacy_1"
        admin = cm.Customer(
            email="admin@example.com",
            password_hash=auth.hasher.hash("admin-test-password"),
            role="admin",
            email_verified_at=datetime.now(UTC),
        )
        db.add(admin)
        db.commit()
    assert http.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert (
        http.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin-test-password"},
        ).status_code
        == 200
    )
    admin_headers = {"X-CSRF-Token": http.cookies["brew67_csrf"]}
    assert len(http.get("/api/v1/admin/privacy-requests").json()) == 1
    reviewed = http.post(
        f"/api/v1/admin/privacy-requests/{request_id}/redact",
        headers=admin_headers,
        json={"reason": "Verified deletion request", "evidence_reference": "ticket:privacy-1"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "external_pending"
    with local() as db:
        buyer = db.scalar(select(cm.Customer).where(cm.Customer.email.like("deleted-%")))
        assert buyer.active is False and buyer.preferences == {}
        assert (
            db.scalars(
                select(models.IntentSignup).where(models.IntentSignup.email == "buyer@example.com")
            ).all()
            == []
        )
    completed = http.post(
        f"/api/v1/admin/privacy-requests/{request_id}/complete",
        headers=admin_headers,
        json={
            "reason": "Provider follow-up confirmed",
            "evidence_reference": "ticket:stripe-delete-1",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
