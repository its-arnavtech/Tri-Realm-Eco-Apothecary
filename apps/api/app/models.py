from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Biome(Base):
    __tablename__ = "biomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    conservation_partner_reference: Mapped[str | None] = mapped_column(String(500))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_product_price"),
        Index("ix_products_filters", "biome_id", "availability_status", "product_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    brew_number: Mapped[int] = mapped_column(Integer, unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    subtitle: Mapped[str] = mapped_column(String(200))
    biome_id: Mapped[str] = mapped_column(ForeignKey("biomes.id"), index=True)
    product_type: Mapped[str] = mapped_column(String(60))
    form_factor: Mapped[str] = mapped_column(String(100))
    unit_size: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    price_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    refillable: Mapped[bool] = mapped_column(Boolean, default=False)
    availability_status: Mapped[str] = mapped_column(String(30), default="concept")
    ingredients: Mapped[list] = mapped_column(JSON, default=list)
    usage_instructions: Mapped[str] = mapped_column(Text)
    warnings: Mapped[str] = mapped_column(Text)
    storage_instructions: Mapped[str] = mapped_column(Text)
    packaging: Mapped[str] = mapped_column(Text)
    shipping_details: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    biome: Mapped[Biome] = relationship()


class FormulationVersion(Base):
    __tablename__ = "formulation_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    version_label: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    ingredients: Mapped[list] = mapped_column(JSON, default=list)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(160))
    safety_document_reference: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    claim_text: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(80))
    source_reference: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    reviewer: Mapped[str | None] = mapped_column(String(160))
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationRuleSet(Base):
    __tablename__ = "recommendation_rule_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version: Mapped[str] = mapped_column(String(40), unique=True)
    rules: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    items: Mapped[list["CartItem"]] = relationship(cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (CheckConstraint("quantity BETWEEN 1 AND 20", name="ck_cart_quantity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    price_snapshot_cents: Mapped[int] = mapped_column(Integer)
    product: Mapped[Product] = relationship()


class IntentSignup(Base):
    __tablename__ = "intent_signups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), index=True)
    interest: Mapped[str] = mapped_column(String(60))
    contact_consent: Mapped[bool] = mapped_column(Boolean)
    marketing_consent: Mapped[bool] = mapped_column(Boolean)
    consent_policy_version: Mapped[str] = mapped_column(String(60))
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_name: Mapped[str] = mapped_column(String(60), index=True)
    anonymous_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(String(64))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    schema_version: Mapped[str] = mapped_column(String(16), default="1")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    before_snapshot: Mapped[dict | None] = mapped_column(JSON)
    after_snapshot: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
