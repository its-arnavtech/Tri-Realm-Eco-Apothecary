import json
import logging
import re
import secrets
from time import perf_counter
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import auth, commerce, commerce_service, models
from app.config import settings
from app.db import get_db
from app.rate_limit import limited
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
    ProductCreate,
    ProductOut,
    ProductPage,
    RecommendationInput,
    RecommendationOut,
)
from app.services import cart_view, create_cart, evaluate_recommendation, get_cart, public_product

app = FastAPI(title="brew67potions API", version="0.1.0")
request_logger = logging.getLogger("brew67.requests")
if not request_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)
request_logger.setLevel(logging.INFO)
request_logger.propagate = False
app.include_router(auth.router)
app.include_router(commerce.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=[
        "Content-Type",
        "X-Cart-Token",
        "X-Admin-Key",
        "X-Actor",
        "X-Reason",
        "X-CSRF-Token",
    ],
)

Db = Annotated[Session, Depends(get_db)]


@app.middleware("http")
async def log_request(request: Request, call_next):
    """Emit latency/status telemetry without query strings, bodies, or customer data."""
    request_id = secrets.token_hex(8)
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith(("/api/v1/account", "/api/v1/admin", "/api/v1/auth")):
            response.headers["Cache-Control"] = "no-store"
        return response
    finally:
        route = request.scope.get("route")
        request_logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(route, "path", "/unmatched"),
                    "status": status,
                    "latency_ms": round((perf_counter() - started) * 1000, 2),
                }
            )
        )


def admin_change(
    request: Request,
    db: Db,
    x_admin_key: Annotated[str | None, Header()] = None,
    x_actor: Annotated[str | None, Header()] = None,
    x_reason: Annotated[str | None, Header()] = None,
) -> AdminChange:
    session = auth.resolve_session(db, request.cookies.get("brew67_session"))
    if session and session.customer.role in {"operations", "admin"}:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            auth.enforce_csrf(request, session)
        return AdminChange(actor=session.customer.email, reason=x_reason or "Operational change")
    if settings.environment != "local" or not settings.web_origin.startswith("http://localhost"):
        raise HTTPException(403, "Admin authorization required")
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
    availability: Literal["concept", "available"] | None = None,
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
    total = db.scalar(select(func.count()).select_from(count_query.subquery())) or 0
    return ProductPage(
        items=[public_product(db, p) for p in products], total=total, page=page, page_size=page_size
    )


@app.get("/api/v1/products/facets", response_model=list[str])
def product_type_facets(db: Db):
    return db.scalars(
        select(models.Product.product_type)
        .where(models.Product.active.is_(True))
        .distinct()
        .order_by(models.Product.product_type)
    ).all()


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


@app.post(
    "/api/v1/recommendations", response_model=RecommendationOut, dependencies=[Depends(limited)]
)
def recommend(payload: RecommendationInput, db: Db):
    return evaluate_recommendation(db, payload)


@app.post("/api/v1/carts", response_model=CartOut, status_code=201, dependencies=[Depends(limited)])
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


@app.post("/api/v1/admin/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Db, change: Admin):
    biome = db.scalar(select(models.Biome).where(models.Biome.slug == payload.biome_slug))
    if not biome or not biome.active:
        raise HTTPException(422, "Unknown or inactive biome")
    product = models.Product(
        brew_number=payload.brew_number,
        slug=payload.slug,
        name=payload.name,
        subtitle="Concept under review",
        biome_id=biome.id,
        product_type="Concept under review",
        form_factor="Concept under review",
        unit_size="Concept under review",
        description="Concept under review. Final product details are pending approval.",
        price_cents=0,
        availability_status="concept",
        ingredients=[],
        usage_instructions="Pending review",
        warnings="Pending review",
        storage_instructions="Pending review",
        packaging="Pending review",
        shipping_details="Pending review",
        active=False,
    )
    try:
        db.add(product)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Brew number or slug already exists") from exc
    audit(db, change, "create", "product", product.id, None, payload.model_dump())
    db.commit()
    db.refresh(product)
    return public_product(db, product)


@app.get("/api/v1/admin/products/{product_id}", response_model=ProductOut)
def admin_product_detail(product_id: str, db: Db, _change: Admin):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return public_product(db, product)


@app.patch("/api/v1/admin/products/{product_id}", response_model=ProductOut)
def edit_product(product_id: str, payload: ProductAdminPatch, db: Db, change: Admin):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    updates = payload.model_dump(exclude_unset=True)
    if any(value is None for key, value in updates.items() if key != "stripe_recurring_price_id"):
        raise HTTPException(422, "Product fields cannot be null")
    before = {key: getattr(product, key) for key in updates}
    for key, value in updates.items():
        setattr(product, key, value)
    if product.availability_status == "available":
        errors = commerce_service.release_errors(db, product, require_published=False)
        if errors:
            raise HTTPException(409, {"release_errors": errors})
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
