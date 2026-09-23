from sqlalchemy import select

from app import commerce_models as cm
from app import models


def test_catalog_filters_and_excludes_unapproved_claims(client):
    http, local = client
    assert http.get("/api/v1/products/facets").json() == [
        "home-care concept",
        "multi-surface concept",
    ]
    response = http.get("/api/v1/products?biome=forest")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["brew_number"] == 14
    assert http.get("/api/v1/products?availability=available").json()["total"] == 0
    assert http.get("/api/v1/products?availability=concept").json()["total"] == 4
    assert http.get("/api/v1/products?availability=invalid").status_code == 422
    with local() as db:
        product = db.scalar(select(models.Product).where(models.Product.brew_number == 14))
        db.add(
            models.ClaimEvidence(
                product_id=product.id,
                claim_text="Unverified claim",
                evidence_type="draft",
                source_reference="internal:pending",
            )
        )
        db.commit()
    assert http.get("/api/v1/products/pine-mycelium-grounding-drops").json()["claims"] == []


def test_recommendation_is_versioned_and_safe(client):
    http, _ = client
    payload = {
        "water_hardness": "hard",
        "household_size": 5,
        "usage_area": "general_surfaces",
        "purchase_type": "starter",
    }
    result = http.post("/api/v1/recommendations", json=payload).json()
    assert result["rule_set_version"] == "poc-1.0.0"
    assert result["quantity"] == 2
    assert result["product_slug"] == "tri-realm-catalyst"
    assert any("hardness" in warning.lower() for warning in result["warnings"])
    payload["usage_area"] = "water_treatment"
    unsupported = http.post("/api/v1/recommendations", json=payload).json()
    assert unsupported["supported"] is False
    assert unsupported["product_slug"] is None
    payload["usage_area"] = "general_surfaces"
    payload["household_size"] = 0
    assert http.post("/api/v1/recommendations", json=payload).status_code == 422


def test_cart_uses_server_price_and_private_token(client):
    http, _ = client
    product = http.get("/api/v1/products/tri-realm-catalyst").json()
    cart = http.post("/api/v1/carts", json={}).json()
    path = f"/api/v1/carts/{cart['id']}"
    assert http.get(path).status_code == 404
    response = http.post(
        path + "/items",
        headers={"X-Cart-Token": cart["token"]},
        json={"product_id": product["id"], "quantity": 2, "price_cents": 1},
    )
    assert response.status_code == 200
    assert response.json()["subtotal_cents"] == product["price_cents"] * 2
    assert response.json()["total_cents"] is None
    item_id = response.json()["items"][0]["id"]
    assert (
        http.patch(
            path + f"/items/{item_id}", headers={"X-Cart-Token": "wrong"}, json={"quantity": 1}
        ).status_code
        == 404
    )
    assert (
        http.patch(
            path + f"/items/{item_id}",
            headers={"X-Cart-Token": cart["token"]},
            json={"quantity": 1},
        ).json()["subtotal_cents"]
        == product["price_cents"]
    )
    assert http.post("/api/v1/checkout/session").status_code == 409


def test_intent_requires_consent_and_analytics_rejects_pii(client):
    http, _ = client
    assert (
        http.post(
            "/api/v1/intent-signups",
            json={
                "email": "user@example.com",
                "contact_consent": False,
            },
        ).status_code
        == 422
    )
    assert (
        http.post(
            "/api/v1/intent-signups",
            json={
                "email": "user@example.com",
                "contact_consent": True,
                "marketing_consent": False,
            },
        ).status_code
        == 201
    )
    event = {
        "event_name": "page_view",
        "anonymous_id": "anonymous123",
        "session_id": "session123",
        "context": {"page": "home"},
    }
    assert http.post("/api/v1/events", json=event).status_code == 202
    event["context"] = {"email": "user@example.com"}
    assert http.post("/api/v1/events", json=event).status_code == 422
    event["context"] = {"page": "user@example.com"}
    assert http.post("/api/v1/events", json=event).status_code == 422


def test_admin_requires_key_and_audits_change(client):
    http, local = client
    product = http.get("/api/v1/products/tri-realm-catalyst").json()
    path = f"/api/v1/admin/products/{product['id']}"
    assert http.patch(path, json={"name": "New name"}).status_code == 403
    response = http.patch(
        path,
        headers={
            "X-Admin-Key": "test-admin-secret",
            "X-Actor": "operator",
            "X-Reason": "POC copy correction",
        },
        json={"name": "Catalyst concept"},
    )
    assert response.status_code == 200
    with local() as db:
        audit = db.scalar(select(models.AuditEvent))
        assert audit.actor == "operator"
        assert audit.before_snapshot["name"] == product["name"]


def test_staff_can_create_private_product_draft(client):
    http, local = client
    path = "/api/v1/admin/products"
    payload = {
        "brew_number": 88,
        "slug": "new-forest-brew",
        "name": "New forest brew",
        "biome_slug": "forest",
    }
    headers = {
        "X-Admin-Key": "test-admin-secret",
        "X-Actor": "operator",
        "X-Reason": "New product concept draft",
    }
    assert http.post(path, json=payload).status_code == 403
    created = http.post(path, headers=headers, json=payload)
    assert created.status_code == 201
    product_id = created.json()["id"]
    assert created.json()["availability_status"] == "concept"
    assert http.get(f"{path}/{product_id}").status_code == 403
    assert http.get(f"{path}/{product_id}", headers=headers).status_code == 200
    assert http.get("/api/v1/products/new-forest-brew").status_code == 404
    assert http.post(path, headers=headers, json=payload).status_code == 409
    assert (
        http.post(
            path, headers=headers, json={**payload, "biome_slug": "unknown", "slug": "other-brew"}
        ).status_code
        == 422
    )
    assert (
        http.patch(f"{path}/{product_id}", headers=headers, json={"active": True}).status_code
        == 200
    )
    assert http.get("/api/v1/products/new-forest-brew").status_code == 200
    assert (
        http.patch(
            f"{path}/{product_id}", headers=headers, json={"availability_status": "available"}
        ).status_code
        == 409
    )
    with local() as db:
        events = db.scalars(
            select(models.AuditEvent).where(models.AuditEvent.entity_id == product_id)
        ).all()
        assert [event.action for event in events] == ["create", "update"]


def test_staff_can_read_admin_product_without_csrf_but_mutation_requires_it(client):
    http, local = client
    registered = http.post(
        "/api/v1/auth/register",
        json={"email": "operator@example.com", "password": "a-long-test-password"},
    )
    assert registered.status_code == 201
    with local() as db:
        operator = db.scalar(select(cm.Customer).where(cm.Customer.email == "operator@example.com"))
        operator.role = "operations"
        db.commit()
    product_id = http.get("/api/v1/products/tri-realm-catalyst").json()["id"]
    path = f"/api/v1/admin/products/{product_id}"
    assert http.get(path).status_code == 200
    assert http.patch(path, json={"name": "Updated name"}).status_code == 403
    assert (
        http.patch(
            path,
            headers={
                "X-CSRF-Token": http.cookies["brew67_csrf"],
                "X-Reason": "Reviewed product copy",
            },
            json={"name": "Updated name"},
        ).status_code
        == 200
    )


def test_public_submission_limit_is_shared_in_database(client):
    http, local = client
    payload = {
        "email": "interest@example.com",
        "contact_consent": True,
        "marketing_consent": False,
    }
    for _ in range(10):
        assert http.post("/api/v1/intent-signups", json=payload).status_code == 201
    assert http.post("/api/v1/intent-signups", json=payload).status_code == 429
    with local() as db:
        bucket = db.scalar(select(cm.RateLimitBucket))
        assert bucket.attempts == 11
    assert (
        http.post(
            "/api/v1/events",
            json={
                "event_name": "page_view",
                "anonymous_id": "anonymous123",
                "session_id": "session123",
                "context": {"page": "home"},
            },
        ).status_code
        == 202
    )
