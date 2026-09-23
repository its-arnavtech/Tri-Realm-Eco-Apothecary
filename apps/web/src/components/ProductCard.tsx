import Link from "next/link";
import type { Concept } from "@/lib/content";
import { RealmArt } from "./RealmArt";

export function ProductCard({ product }: { product: Concept }) {
  return <article className={`product-card product-card--${product.realm}`}>
    <Link href={`/catalog/${product.slug}`} className="product-card__art" aria-label={`Explore ${product.name}`}><RealmArt realm={product.realm} /></Link>
    <div className="product-card__body"><div className="eyebrow">Brew No. {product.number} <span>·</span> {product.realm.replace("-", " ")}</div>
      <h3><Link href={`/catalog/${product.slug}`}>{product.name}</Link></h3>
      <p>{product.summary}</p>
      <div className="product-card__bottom"><span>Concept / In development</span><Link href={`/catalog/${product.slug}`} aria-label={`View concept: ${product.name}`}>Explore <span aria-hidden="true">↗</span></Link></div>
    </div>
  </article>;
}
