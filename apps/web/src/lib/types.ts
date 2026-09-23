export type Biome = { slug: string; name: string; description: string; display_order: number };

export type Product = {
  id: string;
  brew_number: number;
  slug: string;
  name: string;
  subtitle: string;
  biome: string;
  product_type: string;
  form_factor: string;
  unit_size: string;
  description: string;
  price_cents: number;
  currency: string;
  refillable: boolean;
  availability_status: string;
  ingredients: string[];
  usage_instructions: string;
  warnings: string;
  storage_instructions: string;
  packaging: string;
  shipping_details: string;
  claims: string[];
  version: number;
};

export type ProductPage = { items: Product[]; total: number; page: number; page_size: number };

export type RecommendationInput = {
  water_hardness: "soft" | "moderate" | "hard" | "unknown";
  household_size: number;
  usage_area: "general_surfaces" | "garden" | "personal_care" | "water_treatment";
  purchase_type: "starter" | "refill";
};

export type Recommendation = {
  rule_set_version: string;
  inputs: RecommendationInput;
  product_slug: string | null;
  quantity: number;
  rationale: string;
  assumptions: string[];
  warnings: string[];
  supported: boolean;
};

export type Cart = {
  id: string;
  token: string;
  items: { id: string; product_id: string; name: string; slug: string; quantity: number; price_cents: number; line_total_cents: number }[];
  subtotal_cents: number;
  shipping_estimate_cents: number | null;
  tax_estimate_cents: number | null;
  total_cents: number | null;
  currency: string;
  simulated: boolean;
  notice: string;
};
