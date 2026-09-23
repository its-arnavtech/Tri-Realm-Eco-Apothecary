import re
import secrets
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app import models
from app.config import settings
from app.db import get_db
from app.schemas import (
    EVENT_CONTEXT_KEYS,
    EVENT_NAMES,
    AdminChange,
    AnalyticsEventIn,
    BiomeOut,
    CartCreate,
    CartItemCreate,
    CartItemPatch,
    CartOut,
    ClaimEvidenceCreate,
    FormulationCreate,
    IntentSignupIn,
    IntentSignupOut,
    ProductAdminPatch,
    ProductOut,
    ProductPage,
    RecommendationInput,
    RecommendationOut,
)
from app.services import cart_view, create_cart, evaluate_recommendation, get_cart, public_product

app = FastAPI(title="brew67potions API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Cart-Token", "X-Admin-Key", "X-Actor", "X-Reason"],
)

Db = Annotated[Session, Depends(get_db)]
_requests: dict[str, deque[datetime]] = defaultdict(deque)


def limited(request: Request) -> None:
    # POC single-process limiter. A shared store is required before scaled deployment.
    key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
    current = datetime.now(UTC)
    bucket = _requests[key]
    cutoff = current - timedelta(minutes=15)
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= 20:
        raise HTTPException(429, "Too many submissions. Try again later.")
    bucket.append(current)


def admin_change(
    x_admin_key: Annotated[str | None, Header()] = None,
    x_actor: Annotated[str | None, Header()] = None,
    x_reason: Annotated[str | None, Header()] = None,
) -> AdminChange:
    if not settings.admin_api_key:
        raise HTTPException(503, "Admin operations are not configured")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(403, "Admin authorization required")
    return AdminChange(actor=x_actor or "", reason=x_reason or "")


Admin = Annotated[AdminChange, Depends(admin_change)]


def audit(
    db: Session,
    change: AdminChange,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None,
    after: dict | None,
) -> None:
    db.add(
        models.AuditEvent(
            actor=change.actor,
            reason=change.reason,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_snapshot=before,
            after_snapshot=after,
        )
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: Db) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/v1/biomes", response_model=list[BiomeOut])
def list_biomes(db: Db):
    return db.scalars(
        select(models.Biome)
        .where(models.Biome.active.is_(True))
        .order_by(models.Biome.display_order)
    ).all()


@app.get("/api/v1/products", response_model=ProductPage)
def list_products(
    db: Db,
    biome: str | None = None,
    product_type: str | None = None,
    availability: str | None = None,
    refillable: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=48),
):
    query = select(models.Product).join(models.Biome).where(models.Product.active.is_(True))
    if biome:
        query = query.where(models.Biome.slug == biome)
    if product_type:
        query = query.where(models.Product.product_type == product_type)
    if availability:
        query = query.where(models.Product.availability_status == availability)
    if refillable is not None:
        query = query.where(models.Product.refillable == refillable)
    products = db.scalars(
        query.options(joinedload(models.Product.biome))
        .order_by(models.Product.brew_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    count_query = (
        select(models.Product.id).join(models.Biome).where(models.Product.active.is_(True))
    )
    if biome:
        count_query = count_query.where(models.Biome.slug == biome)
    if product_type:
        count_query = count_query.where(models.Product.product_type == product_type)
    if availability:
        count_query = count_query.where(models.Product.availability_status == availability)
    if refillable is not None:
        count_query = count_query.where(models.Product.refillable == refillable)
    total = len(db.execute(count_query).all())
    return ProductPage(
        items=[public_product(db, p) for p in products], total=total, page=page, page_size=page_size
    )


@app.get("/api/v1/products/{slug}", response_model=ProductOut)
def product_detail(slug: str, db: Db):
    product = db.scalar(
        select(models.Product)
        .options(joinedload(models.Product.biome))
        .where(models.Product.slug == slug, models.Product.active.is_(True))
    )
    if not product:
        raise HTTPException(404, "Product not found")
    return public_product(db, product)


@app.post("/api/v1/recommendations", response_model=RecommendationOut)
def recommend(payload: RecommendationInput, db: Db):
    return evaluate_recommendation(db, payload)


@app.post("/api/v1/carts", response_model=CartOut, status_code=201)
def new_cart(payload: CartCreate, db: Db):
    if payload.token:
        cart = db.scalar(select(models.Cart).where(models.Cart.token == payload.token))
        if cart:
            return cart_view(cart)
    return cart_view(create_cart(db))


@app.get("/api/v1/carts/{cart_id}", response_model=CartOut)
def read_cart(cart_id: str, db: Db, x_cart_token: Annotated[str | None, Header()] = None):
    return cart_view(get_cart(db, cart_id, x_cart_token))


@app.post("/api/v1/carts/{cart_id}/items", response_model=CartOut)
def add_cart_item(
    cart_id: str,
    payload: CartItemCreate,
    db: Db,
    x_cart_token: Annotated[str | None, Header()] = None,
):
    cart = get_cart(db, cart_id, x_cart_token)
    product = db.get(models.Product, payload.product_id)
    if (
        not product
        or not product.active
        or product.availability_status not in {"concept", "available"}
    ):
        raise HTTPException(409, "Product cannot be added to the concept cart")
    item = next((item for item in cart.items if item.product_id == product.id), None)
    if item:
        if item.quantity + payload.quantity > 20:
            raise HTTPException(422, "Maximum quantity is 20")
        item.quantity += payload.quantity
        item.price_snapshot_cents = product.price_cents
    else:
        db.add(
            models.CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=payload.quantity,
                price_snapshot_cents=product.price_cents,
            )
        )
    db.commit()
    db.refresh(cart)
    return cart_view(cart)


@app.patch("/api/v1/carts/{cart_id}/items/{item_id}", response_model=CartOut)
def update_cart_item(
    cart_id: str,
    item_id: str,
    payload: CartItemPatch,
    db: Db,
    x_cart_token: Annotated[str | None, Header()] = None,
):
    cart = get_cart(db, cart_id, x_cart_token)
    item = next((item for item in cart.items if item.id == item_id), None)
    if not item:
        raise HTTPException(404, "Cart item not found")
    item.quantity = payload.quantity
    db.commit()
    return cart_view(cart)


@app.delete("/api/v1/carts/{cart_id}/items/{item_id}", response_model=CartOut)
def remove_cart_item(
    cart_id: str,
    item_id: str,
    db: Db,
    x_cart_token: Annotated[str | None, Header()] = None,
):
    cart = get_cart(db, cart_id, x_cart_token)
    item = next((item for item in cart.items if item.id == item_id), None)
    if not item:
        raise HTTPException(404, "Cart item not found")
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart_view(cart)


@app.post(
    "/api/v1/intent-signups",
    response_model=IntentSignupOut,
    status_code=201,
    dependencies=[Depends(limited)],
)
def capture_intent(payload: IntentSignupIn, db: Db):
    signup = models.IntentSignup(
        email=str(payload.email).lower(),
        interest=payload.interest,
        contact_consent=payload.contact_consent,
        marketing_consent=payload.marketing_consent,
        consent_policy_version=settings.consent_policy_version,
    )
    db.add(signup)
    db.commit()
    db.refresh(signup)
    return signup


@app.post("/api/v1/events", status_code=202, dependencies=[Depends(limited)])
def record_event(payload: AnalyticsEventIn, db: Db):
    if payload.event_name not in EVENT_NAMES:
        raise HTTPException(422, "Unknown event name")
    if any(
        key not in EVENT_CONTEXT_KEYS or not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", value)
        for key, value in payload.context.items()
    ):
        raise HTTPException(422, "Unsupported event context")
    db.add(models.AnalyticsEvent(**payload.model_dump()))
    db.commit()
    return {"accepted": True}


@app.post("/api/v1/checkout/session", status_code=409)
def checkout_unavailable():
    raise HTTPException(409, "Checkout is disabled until product and commerce release gates pass")


@app.patch("/api/v1/admin/products/{product_id}", response_model=ProductOut)
def edit_product(product_id: str, payload: ProductAdminPatch, db: Db, change: Admin):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    updates = payload.model_dump(exclude_unset=True)
    before = {key: getattr(product, key) for key in updates}
    for key, value in updates.items():
        setattr(product, key, value)
    product.version += 1
    audit(db, change, "update", "product", product.id, before, updates)
    db.commit()
    db.refresh(product)
    return public_product(db, product)


@app.post("/api/v1/admin/products/{product_id}/formulations", status_code=201)
def add_formulation(product_id: str, payload: FormulationCreate, db: Db, change: Admin):
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    formulation = models.FormulationVersion(product_id=product_id, **payload.model_dump())
    db.add(formulation)
    db.flush()
    audit(db, change, "create", "formulation_version", formulation.id, None, payload.model_dump())
    db.commit()
    return {"id": formulation.id, "status": formulation.status}


@app.post("/api/v1/admin/products/{product_id}/claims", status_code=201)
def add_claim_evidence(product_id: str, payload: ClaimEvidenceCreate, db: Db, change: Admin):
    if not db.get(models.Product, product_id):
        raise HTTPException(404, "Product not found")
    evidence = models.ClaimEvidence(product_id=product_id, **payload.model_dump())
    db.add(evidence)
    db.flush()
    audit(db, change, "create", "claim_evidence", evidence.id, None, payload.model_dump())
    db.commit()
    return {"id": evidence.id, "status": evidence.status}
