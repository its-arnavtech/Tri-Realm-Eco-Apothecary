import Link from "next/link";
import { notFound } from "next/navigation";
import { AddToCartButton } from "@/components/AddToCartButton";
import { Analytics } from "@/components/Analytics";
import { RealmArt } from "@/components/RealmArt";
import { SubscribeButton } from "@/components/SubscribeButton";
import { getImpact, getProduct, money } from "@/lib/api";

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) notFound();
  const impact = await getImpact(product.id);
  const available = product.availability_status === "available";
  return <main id="main"><Analytics page="product-detail" product={product.slug} />
    <section className="detail shell"><div className="breadcrumb"><Link href="/catalog">All brews</Link> / {product.name}</div>
      <div className="detail__grid"><div className="detail__art"><RealmArt realm={product.biome} large /></div>
        <div className="detail__copy"><p className="eyebrow">BREW NO. {product.brew_number} · {product.biome.replace("-", " ")} realm</p>
          <h1>{product.name}</h1><span className="status-pill">{available ? "Available" : "Concept · not for sale"}</span>
          <p className="detail__intro">{product.description}</p>
          <p className="detail__price">{available ? "Price" : "Illustrative price"}: {money(product.price_cents)}</p>
          <dl className="detail__facts"><div><dt>Format</dt><dd>{product.form_factor}</dd></div>
            <div><dt>Unit size</dt><dd>{product.unit_size}</dd></div>
            <div><dt>Refill</dt><dd>{product.refillable ? available ? "Available" : "Compatibility pending" : "Not available"}</dd></div>
            <div><dt>Availability</dt><dd>{available ? "Ready for checkout" : "Concept only"}</dd></div></dl>
          <div className="detail__actions"><AddToCartButton productId={product.id} productSlug={product.slug} concept={!available} />
            {available && product.refillable && <SubscribeButton productId={product.id} />}
            <Link href="/configure" className="text-link">Find your brew →</Link></div>
        </div></div>
      <div className="detail__body"><div><h2>What’s inside</h2><ul>{product.ingredients.map((ingredient) => <li key={ingredient}>{ingredient}</li>)}</ul>
        <h2>Packaging</h2><p>{product.packaging}</p></div><div><h2>Use and care</h2><p>{product.usage_instructions}</p>
          <h2>Warnings and storage</h2><p>{product.warnings} {product.storage_instructions}</p>
          <h2>Shipping</h2><p>{product.shipping_details}</p></div></div>
      <div className="note-panel"><p><strong>Claims and evidence:</strong> {product.claims.length ? product.claims.join(" ") : "No product performance or environmental claim has been approved for public display."}</p></div>
      {impact.length > 0 && <div className="detail__body"><div><h2>Reviewed impact method</h2>
        <p>These figures apply only to the stated baseline and comparison scenario.</p></div>
        <div>{impact.map((item) => <div className="note-panel" key={`${item.metric_type}-${item.methodology_version}`}>
          <p><strong>{item.metric_type} ({item.estimate_kind}):</strong> {item.factor_value} {item.unit} {item.basis}</p>
          <p>Baseline: {item.baseline}</p><p>Compared with: {item.comparison_scenario}</p>
          <p>{item.qualification} · Method {item.methodology_version} · Source: {item.source_reference}</p>
        </div>)}</div></div>}
    </section>
  </main>;
}
