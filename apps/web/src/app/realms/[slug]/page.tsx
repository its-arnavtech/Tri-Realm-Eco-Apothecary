import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProductCard } from "@/components/ProductCard";
import { RealmArt } from "@/components/RealmArt";
import { concepts, realmBySlug, realms } from "@/lib/content";

export function generateStaticParams() { return realms.map(({ slug }) => ({ slug })); }

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const realm = realmBySlug((await params).slug);
  return { title: realm ? `${realm.name} realm` : "Realm", description: realm?.introduction };
}

export default async function RealmPage({ params }: { params: Promise<{ slug: string }> }) {
  const realm = realmBySlug((await params).slug);
  if (!realm) notFound();
  const fromRealm = concepts.filter((concept) => concept.realm === realm.slug);
  return <main id="main"><section className={`page-hero page-hero--dark realm-hero realm-hero--${realm.slug}`}><div className="shell two-column"><div><div className="breadcrumb"><Link href="/realms">All realms</Link> / {realm.name}</div><p className="section-number">REALM {realm.number} / {realm.name.toUpperCase()}</p><h1>{realm.name}<br /><em>{realm.tagline}.</em></h1><p>{realm.introduction}</p></div><RealmArt realm={realm.slug} /></div></section>
    <section className="content-section shell realm-story"><p className="section-number">A PERSPECTIVE ON CARE</p><h2>{realm.perspective}</h2><div className="realm-story__rule" /><p>Explore the concept below to see how this realm might take shape. Its practical details remain under review.</p></section>
    <section className="content-section shell realm-concepts"><p className="section-number">FROM THIS REALM</p><div className="product-grid">{fromRealm.map((concept) => <ProductCard key={concept.slug} product={concept} />)}</div><Link href="/catalog" className="text-link">Explore the full gallery <span aria-hidden="true">↗</span></Link></section>
  </main>;
}
