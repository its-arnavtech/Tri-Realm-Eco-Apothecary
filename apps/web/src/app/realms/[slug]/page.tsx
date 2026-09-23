import Link from "next/link";
import { notFound } from "next/navigation";
import { Analytics } from "@/components/Analytics";
import { ProductCard } from "@/components/ProductCard";
import { RealmArt } from "@/components/RealmArt";
import { getProducts } from "@/lib/api";

const realmCopy: Record<string, { name: string; tagline: string; description: string; caveat: string }> = {
  forest: { name: "Forest", tagline: "Rooted in renewal", description: "Explore a canopy and soil inspired point of view for future home care. The concept ingredients and intended use remain under review.", caveat: "Source, safety and performance information will be published only when validated." },
  ocean: { name: "Ocean", tagline: "Moved by tides", description: "Discover compact product ideas inspired by the coast. The story does not establish aquatic safety or biodegradability.", caveat: "Any claim about waterways, microplastics or biodegradability requires specific evidence." },
  mountain: { name: "Mountain", tagline: "Made for clarity", description: "Meet mineral inspired care concepts and a design language shaped by elevation and simplicity.", caveat: "Final household use and water related claims require product-specific testing." },
};

export default async function RealmPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const realm = realmCopy[slug];
  if (!realm) notFound();
  const products = await getProducts(`?biome=${slug}`);
  return <main id="main"><Analytics page={`realm-${slug}`} biome={slug} />
    <section className={`page-hero page-hero--dark realm-hero realm-hero--${slug}`}><div className="shell two-column"><div><div className="breadcrumb"><Link href="/realms">All realms</Link> / {realm.name}</div><p className="section-number">THE {realm.name.toUpperCase()} REALM</p><h1>{realm.name}<br /><em>{realm.tagline}.</em></h1><p>{realm.description}</p></div><RealmArt realm={slug} /></div></section>
    <section className="content-section shell"><p className="section-number">FROM THIS REALM</p><h2>Concept brews</h2><div className="product-grid">{products.items.map((product) => <ProductCard key={product.id} product={product} />)}</div><div className="note-panel"><p>{realm.caveat}</p></div><Link href="/catalog" className="text-link">Browse every brew <span aria-hidden="true">↗</span></Link></section>
  </main>;
}
