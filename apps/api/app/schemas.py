from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BiomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    description: str
    display_order: int


class ProductOut(BaseModel):
    id: str
    brew_number: int
    slug: str
    name: str
    subtitle: str
    biome: str
    product_type: str
    form_factor: str
    unit_size: str
    description: str
    price_cents: int
    currency: str
    refillable: bool
    availability_status: str
    ingredients: list[str]
    usage_instructions: str
    warnings: str
    storage_instructions: str
    packaging: str
    shipping_details: str
    claims: list[str]
    version: int


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class RecommendationInput(BaseModel):
    water_hardness: Literal["soft", "moderate", "hard", "unknown"]
    household_size: int = Field(ge=1, le=12)
    usage_area: Literal["general_surfaces", "garden", "personal_care", "water_treatment"]
    purchase_type: Literal["starter", "refill"]


class RecommendationOut(BaseModel):
    rule_set_version: str
    inputs: RecommendationInput
    product_slug: str | None
    quantity: int
    rationale: str
    assumptions: list[str]
    warnings: list[str]
    supported: bool


class CartCreate(BaseModel):
    token: str | None = Field(default=None, min_length=32, max_length=64)


class CartItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=20)


class CartItemPatch(BaseModel):
    quantity: int = Field(ge=1, le=20)


class CartItemOut(BaseModel):
    id: str
    product_id: str
    name: str
    slug: str
    quantity: int
    price_cents: int
    line_total_cents: int


class CartOut(BaseModel):
    id: str
    token: str
    items: list[CartItemOut]
    subtotal_cents: int
    shipping_estimate_cents: int | None
    tax_estimate_cents: int | None
    total_cents: int | None
    currency: str
    simulated: bool = True
    notice: str = "Concept cart only. Prices are illustrative; no payment or order is created."


class IntentSignupIn(BaseModel):
    email: EmailStr
    interest: Literal["general", "forest", "ocean", "mountain", "brew-67"] = "general"
    contact_consent: Literal[True]
    marketing_consent: bool = False


class IntentSignupOut(BaseModel):
    id: str
    interest: str
    consent_policy_version: str
    created_at: datetime


EVENT_NAMES = {
    "page_view",
    "biome_viewed",
    "product_viewed",
    "configurator_started",
    "configurator_step_completed",
    "recommendation_generated",
    "add_to_cart",
    "checkout_started",
    "intent_submitted",
    "refill_viewed",
    "cta_clicked",
}
EVENT_CONTEXT_KEYS = {
    "page",
    "biome",
    "product_slug",
    "step",
    "experiment_version",
    "traffic_source",
}


class AnalyticsEventIn(BaseModel):
    event_name: str
    anonymous_id: str = Field(min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    session_id: str = Field(min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    context: dict[str, str] = Field(default_factory=dict)
    schema_version: Literal["1"] = "1"


class ProductAdminPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    subtitle: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    product_type: str | None = Field(default=None, min_length=2, max_length=60)
    form_factor: str | None = Field(default=None, min_length=2, max_length=100)
    price_cents: int | None = Field(default=None, ge=0)
    unit_size: str | None = Field(default=None, min_length=2, max_length=80)
    availability_status: Literal["concept", "available", "unavailable"] | None = None
    stripe_recurring_price_id: str | None = Field(default=None, max_length=160)
    refillable: bool | None = None
    ingredients: list[str] | None = None
    usage_instructions: str | None = None
    warnings: str | None = None
    storage_instructions: str | None = None
    packaging: str | None = None
    shipping_details: str | None = None


class FormulationCreate(BaseModel):
    version_label: str = Field(min_length=1, max_length=60)
    ingredients: list[str]
    safety_document_reference: str | None = None


class ClaimEvidenceCreate(BaseModel):
    claim_text: str = Field(min_length=5)
    evidence_type: str = Field(min_length=2, max_length=80)
    source_reference: str = Field(min_length=5, max_length=500)


class AdminChange(BaseModel):
    actor: str = Field(min_length=2, max_length=160)
    reason: str = Field(min_length=5, max_length=500)
