import type { Metadata } from "next";
import { ProductCard } from "@/components/ProductCard";
import { concepts } from "@/lib/content";

export const metadata: Metadata = { title: "Concept gallery", description: "Explore four early brew ideas inspired by Forest, Ocean, and Mountain." };

export default function CatalogPage() {
  return <main id="main">
    <section className="page-hero page-hero--gallery"><div className="shell"><p className="section-number">THE APOTHECARY / 002</p><h1>A gallery of <em>possibility.</em></h1><p>Four early ideas, each with a point of view and questions still to answer. These are concepts, not finished products.</p></div></section>
    <section className="content-section shell"><div className="catalog-intro"><div><p className="section-number">THE CONCEPT COLLECTION</p><h2>Meet the brews</h2></div><p>Follow what inspires each idea and see what remains open before it could become something real.</p></div><div className="product-grid">{concepts.map((concept) => <ProductCard key={concept.slug} product={concept} />)}</div><p className="catalog-disclaimer">Concepts are illustrative. No formulation, performance claim, or product is approved for use or sale.</p></section>
  </main>;
}
