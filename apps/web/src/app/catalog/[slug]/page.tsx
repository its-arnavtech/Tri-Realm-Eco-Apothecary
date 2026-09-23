import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RealmArt } from "@/components/RealmArt";
import { conceptBySlug, concepts } from "@/lib/content";

export function generateStaticParams() { return concepts.map(({ slug }) => ({ slug })); }

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const concept = conceptBySlug((await params).slug);
  return { title: concept?.name ?? "Concept", description: concept?.summary };
}

export default async function ConceptPage({ params }: { params: Promise<{ slug: string }> }) {
  const concept = conceptBySlug((await params).slug);
  if (!concept) notFound();
  const next = concepts[(concepts.indexOf(concept) + 1) % concepts.length];
  return <main id="main"><section className="detail shell"><div className="breadcrumb"><Link href="/catalog">Concept gallery</Link> / Brew No. {concept.number}</div>
    <div className="detail__grid"><div className="detail__art"><RealmArt realm={concept.realm} large /><span className="detail__art-label">BREW NO. {concept.number} / {concept.realm.replace("-", " ")}</span></div><div className="detail__copy"><p className="eyebrow">AN IDEA IN DEVELOPMENT</p><h1>{concept.name}</h1><span className="status-pill">Concept only · Not for sale</span><p className="detail__intro">{concept.summary}</p><p className="detail__story">{concept.story}</p><dl className="detail__facts"><div><dt>Inspiration</dt><dd>{concept.realm.replace("-", " ")}</dd></div><div><dt>Proposed format</dt><dd>{concept.format}</dd></div></dl><Link href="/realms" className="text-link">Explore the realms <span aria-hidden="true">↗</span></Link></div></div>
    <div className="detail__body"><div><p className="section-number">WHAT WE’RE EXPLORING</p><h2>The idea</h2><ul>{concept.exploration.map((item) => <li key={item}>{item}</li>)}</ul></div><div><p className="section-number">WHAT COMES FIRST</p><h2>Open questions</h2><ul>{concept.questions.map((item) => <li key={item}>{item}</li>)}</ul></div></div><div className="note-panel"><p>All imagery and descriptions on this page are conceptual. Ingredients, directions, safety, performance, and availability have not been validated or approved.</p></div><div className="next-concept"><span>CONTINUE EXPLORING</span><Link href={`/catalog/${next.slug}`}>{next.name} <span aria-hidden="true">↗</span></Link></div>
  </section></main>;
}
