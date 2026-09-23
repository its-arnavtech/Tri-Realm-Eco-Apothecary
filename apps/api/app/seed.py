from sqlalchemy import select

from app import models
from app.db import SessionLocal

BIOMES = [
    ("forest", "Forest Realm", "Explore concepts inspired by canopy, soil and renewal.", 1),
    (
        "ocean",
        "Ocean Realm",
        "Explore concepts inspired by tides and careful water stewardship.",
        2,
    ),
    ("mountain", "Mountain Realm", "Explore concepts inspired by stone, altitude and clarity.", 3),
    ("tri-realm", "The Tri-Realm", "A concept bridge between all three realms.", 4),
]

PRODUCTS = [
    {
        "brew_number": 14,
        "slug": "pine-mycelium-grounding-drops",
        "name": "Pine & Mycelium Grounding Drops",
        "subtitle": "Brew No. 14 · Forest Realm",
        "biome": "forest",
        "product_type": "home-care concept",
        "form_factor": "concentrated drops",
        "unit_size": "Size to be confirmed",
        "price_cents": 1800,
        "refillable": False,
        "description": "A forest-inspired concept exploring concentrated care for the home. Its final purpose and formulation are under review.",
        "packaging": "Packaging concept under review.",
    },
    {
        "brew_number": 45,
        "slug": "tidal-dissolving-pods",
        "name": "Tidal Dissolving Pods",
        "subtitle": "Brew No. 45 · Ocean Realm",
        "biome": "ocean",
        "product_type": "home-care concept",
        "form_factor": "dissolving pods",
        "unit_size": "Size to be confirmed",
        "price_cents": 2200,
        "refillable": False,
        "description": "An ocean-inspired concept for a compact product format. Performance and environmental properties are unverified.",
        "packaging": "Packaging concept under review.",
    },
    {
        "brew_number": 61,
        "slug": "glacial-mineral-elixir",
        "name": "Glacial Mineral Elixir",
        "subtitle": "Brew No. 61 · Mountain Realm",
        "biome": "mountain",
        "product_type": "home-care concept",
        "form_factor": "concentrate",
        "unit_size": "Size to be confirmed",
        "price_cents": 2000,
        "refillable": False,
        "description": "A mountain-inspired concept. Its final use, compatibility and instructions require product testing.",
        "packaging": "Packaging concept under review.",
    },
    {
        "brew_number": 67,
        "slug": "tri-realm-catalyst",
        "name": "The Tri-Realm Catalyst",
        "subtitle": "Brew No. 67 · Flagship concept",
        "biome": "tri-realm",
        "product_type": "multi-surface concept",
        "form_factor": "tablet kit",
        "unit_size": "Proposed: three tablets and one bottle",
        "price_cents": 3400,
        "refillable": True,
        "description": "A proposed starter kit bringing Forest, Ocean and Mountain into one general-surface care ritual. The final formulation and instructions are not approved.",
        "packaging": "Proposed reusable glass spray bottle with three tablets; final materials unconfirmed.",
    },
]


def seed() -> None:
    with SessionLocal() as db:
        biomes = {}
        for slug, name, description, order in BIOMES:
            biome = db.scalar(select(models.Biome).where(models.Biome.slug == slug))
            if not biome:
                biome = models.Biome(
                    slug=slug, name=name, description=description, display_order=order
                )
                db.add(biome)
                db.flush()
            biomes[slug] = biome
        for item in PRODUCTS:
            if db.scalar(select(models.Product).where(models.Product.slug == item["slug"])):
                continue
            data = dict(item)
            biome_slug = data.pop("biome")
            db.add(
                models.Product(
                    biome_id=biomes[biome_slug].id,
                    ingredients=["Ingredient list pending formulation validation"],
                    usage_instructions="Do not prepare or use this concept product. Final instructions are pending safety review.",
                    warnings="Concept only. Not tested or approved for use or sale.",
                    storage_instructions="Storage guidance pending stability testing.",
                    shipping_details="Shipping is not available during the proof of concept.",
                    availability_status="concept",
                    currency="USD",
                    **data,
                )
            )
        if not db.scalar(
            select(models.RecommendationRuleSet).where(
                models.RecommendationRuleSet.version == "poc-1.0.0"
            )
        ):
            db.add(
                models.RecommendationRuleSet(
                    version="poc-1.0.0",
                    active=True,
                    rules={"small_household_max": 4, "supported_usage_area": "general_surfaces"},
                )
            )
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seeded concept catalog and recommendation rules")
