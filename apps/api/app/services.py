import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.schemas import CartItemOut, CartOut, ProductOut, RecommendationInput, RecommendationOut


def public_product(db: Session, product: models.Product) -> ProductOut:
    approved_claims = db.scalars(
        select(models.ClaimEvidence.claim_text).where(
            models.ClaimEvidence.product_id == product.id,
            models.ClaimEvidence.status == "approved",
        )
    ).all()
    return ProductOut(
        id=product.id,
        brew_number=product.brew_number,
        slug=product.slug,
        name=product.name,
        subtitle=product.subtitle,
        biome=product.biome.slug,
        product_type=product.product_type,
        form_factor=product.form_factor,
        unit_size=product.unit_size,
        description=product.description,
        price_cents=product.price_cents,
        currency=product.currency,
        refillable=product.refillable,
        availability_status=product.availability_status,
        ingredients=product.ingredients,
        usage_instructions=product.usage_instructions,
        warnings=product.warnings,
        storage_instructions=product.storage_instructions,
        packaging=product.packaging,
        shipping_details=product.shipping_details,
        claims=approved_claims,
        version=product.version,
    )


def evaluate_recommendation(db: Session, inputs: RecommendationInput) -> RecommendationOut:
    rule_set = db.scalar(
        select(models.RecommendationRuleSet)
        .where(models.RecommendationRuleSet.active.is_(True))
        .order_by(models.RecommendationRuleSet.created_at.desc())
    )
    if not rule_set:
        raise HTTPException(503, "Recommendation rules are not configured")
    if inputs.usage_area != "general_surfaces":
        return RecommendationOut(
            rule_set_version=rule_set.version,
            inputs=inputs,
            product_slug=None,
            quantity=0,
            rationale="This concept configurator currently supports general household surfaces only.",
            assumptions=["No formulation is changed based on these answers."],
            warnings=[
                "Choose general surfaces or review product information without a recommendation."
            ],
            supported=False,
        )
    if inputs.purchase_type == "refill":
        return RecommendationOut(
            rule_set_version=rule_set.version,
            inputs=inputs,
            product_slug=None,
            quantity=0,
            rationale="Refill compatibility has not been validated for the concept kit.",
            assumptions=["The starter kit is the only concept format in this POC."],
            warnings=["Refill recommendations will be available after compatibility review."],
            supported=False,
        )
    quantity = 1 if inputs.household_size <= rule_set.rules["small_household_max"] else 2
    warnings = ["Product formulation and usage instructions are awaiting validation."]
    if inputs.water_hardness in {"hard", "unknown"}:
        warnings.append("Water hardness effects have not been validated; do not alter dilution.")
    product = db.scalar(select(models.Product).where(models.Product.slug == "tri-realm-catalyst"))
    if not product or not product.active:
        return RecommendationOut(
            rule_set_version=rule_set.version,
            inputs=inputs,
            product_slug=None,
            quantity=0,
            rationale="The concept kit is unavailable.",
            assumptions=[],
            warnings=["No alternative formulation is inferred."],
            supported=False,
        )
    return RecommendationOut(
        rule_set_version=rule_set.version,
        inputs=inputs,
        product_slug=product.slug,
        quantity=quantity,
        rationale=(
            "The starter concept matches the selected general-surface use. "
            f"{quantity} kit{'s are' if quantity > 1 else ' is'} suggested for the selected household size."
        ),
        assumptions=[
            "Quantity is a POC planning suggestion, not a performance or coverage guarantee.",
            "The same concept formulation is shown for every water hardness answer.",
        ],
        warnings=warnings,
        supported=True,
    )


def cart_view(cart: models.Cart) -> CartOut:
    items = [
        CartItemOut(
            id=item.id,
            product_id=item.product_id,
            name=item.product.name,
            slug=item.product.slug,
            quantity=item.quantity,
            price_cents=item.price_snapshot_cents,
            line_total_cents=item.quantity * item.price_snapshot_cents,
        )
        for item in cart.items
    ]
    return CartOut(
        id=cart.id,
        token=cart.token,
        items=items,
        subtotal_cents=sum(item.line_total_cents for item in items),
        shipping_estimate_cents=None,
        tax_estimate_cents=None,
        total_cents=None,
        currency="USD",
    )


def create_cart(db: Session) -> models.Cart:
    cart = models.Cart(token=secrets.token_urlsafe(32))
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def get_cart(db: Session, cart_id: str, token: str | None) -> models.Cart:
    cart = db.get(models.Cart, cart_id)
    if not cart or not token or not secrets.compare_digest(cart.token, token):
        raise HTTPException(404, "Cart not found")
    return cart


def total_products(db: Session) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(models.Product).where(models.Product.active.is_(True))
        )
        or 0
    )
