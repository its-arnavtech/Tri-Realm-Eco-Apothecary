import type { Biome, Product, ProductPage } from "./types";

const base = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${base}/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const getBiomes = () => get<Biome[]>("/biomes");
export const getProducts = (query = "") => get<ProductPage>(`/products${query}`);
export async function getProduct(slug: string): Promise<Product | null> {
  const response = await fetch(`${base}/api/v1/products/${encodeURIComponent(slug)}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Product request failed: ${response.status}`);
  return response.json() as Promise<Product>;
}

export function money(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}
