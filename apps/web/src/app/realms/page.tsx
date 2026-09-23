import type { Metadata } from "next";
import Link from "next/link";
import { RealmArt } from "@/components/RealmArt";
import { realms } from "@/lib/content";

export const metadata: Metadata = { title: "The three realms", description: "Explore the Forest, Ocean, and Mountain worlds behind brew67potions." };

export default function RealmsPage() {
  return <main id="main"><section className="page-hero page-hero--dark"><div className="shell"><p className="section-number">WORLD OF BREW67 / 001</p><h1>Three realms.<br /><em>One point of view.</em></h1><p>Each realm offers a place to begin: a mood, a material language, and a set of ideas still taking shape.</p></div></section>
    <section className="content-section shell"><div className="realm-grid">{realms.map((realm) => <Link key={realm.slug} className={`realm-tile realm-tile--${realm.slug}`} href={`/realms/${realm.slug}`}><div className="realm-tile__top"><span>{realm.number} / REALM</span><span aria-hidden="true">↗</span></div><RealmArt realm={realm.slug} /><div className="realm-tile__bottom"><span>{realm.tagline}</span><h3>{realm.name}</h3><p>{realm.introduction}</p></div></Link>)}</div></section>
  </main>;
}
