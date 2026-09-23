import Link from "next/link";
import { Analytics } from "@/components/Analytics";
import { ProductCard } from "@/components/ProductCard";
import { getProducts, getProductTypes } from "@/lib/api";

type Search = { biome?: string; product_type?: string; availability?: string; refillable?: string; page?: string };

export default async function CatalogPage({ searchParams }: { searchParams: Promise<Search> }) {
  const filters = await searchParams;
  const query = new URLSearchParams();
  for (const key of ["biome", "product_type", "availability", "refillable", "page"] as const) {
    const value = filters[key]; if (value) query.set(key, value);
  }
  const [products, productTypes] = await Promise.all([getProducts(`?${query.toString()}`), getProductTypes()]);
  const nextQuery = new URLSearchParams(query);
  nextQuery.set("page", String(products.page + 1));
  const previousQuery = new URLSearchParams(query);
  previousQuery.set("page", String(products.page - 1));
  return <main id="main"><Analytics page="catalog" /><section className="page-hero"><div className="shell"><p className="section-number">THE APOTHECARY / 002</p><h1>Explore the <em>brews.</em></h1><p>Explore each brew’s ingredients, use, availability and evidence. Concept products are clearly marked and cannot be purchased.</p></div></section>
    <section className="content-section shell"><div className="catalog-toolbar"><div><h2 className="section-number">THE COLLECTION</h2><p>{products.total} brew{products.total === 1 ? "" : "s"}</p></div>
      <form className="filter-form" action="/catalog"><div className="field"><label htmlFor="biome">Realm</label><select id="biome" name="biome" defaultValue={filters.biome ?? ""}><option value="">All realms</option><option value="forest">Forest</option><option value="ocean">Ocean</option><option value="mountain">Mountain</option><option value="tri-realm">Tri-Realm</option></select></div>
        <div className="field"><label htmlFor="product_type">Type</label><select id="product_type" name="product_type" defaultValue={filters.product_type ?? ""}><option value="">All types</option>{productTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></div>
        <div className="field"><label htmlFor="availability">Availability</label><select id="availability" name="availability" defaultValue={filters.availability ?? ""}><option value="">All statuses</option><option value="available">Available</option><option value="concept">Concept</option></select></div>
        <div className="field"><label htmlFor="refillable">Refillable</label><select id="refillable" name="refillable" defaultValue={filters.refillable ?? ""}><option value="">Any</option><option value="true">Yes</option><option value="false">No</option></select></div><button type="submit">Apply filters</button></form></div>
      {products.items.length ? <div className="product-grid">{products.items.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <div className="empty-state"><h2>No brews match those filters.</h2><Link className="text-link" href="/catalog">Clear filters →</Link></div>}
      <nav className="pagination" aria-label="Catalog pages">{products.page > 1 && <Link href={`/catalog?${previousQuery}`}>← Previous</Link>}{products.page * products.page_size < products.total && <Link href={`/catalog?${nextQuery}`}>Next →</Link>}</nav>
    </section>
  </main>;
}
