import Link from "next/link";
import { money } from "@/lib/api";
import type { Product } from "@/lib/types";
import { RealmArt } from "./RealmArt";

export function ProductCard({ product }: { product: Product }) {
  return <article className={`product-card product-card--${product.biome}`}>
    <Link href={`/catalog/${product.slug}`} className="product-card__art" aria-label={`Explore ${product.name}`}><RealmArt realm={product.biome} /></Link>
    <div className="product-card__body"><div className="eyebrow">Brew No. {product.brew_number} <span>·</span> {product.biome.replace("-", " ")}</div>
      <h3><Link href={`/catalog/${product.slug}`}>{product.name}</Link></h3>
      <p>{product.description}</p>
      <div className="product-card__bottom"><span>Illustrative {money(product.price_cents)}</span><Link href={`/catalog/${product.slug}`} aria-label={`View details for ${product.name}`}>View brew <span aria-hidden="true">↗</span></Link></div>
    </div>
  </article>;
}
