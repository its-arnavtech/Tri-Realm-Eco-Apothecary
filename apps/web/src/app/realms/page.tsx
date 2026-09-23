import Link from "next/link";
import { Analytics } from "@/components/Analytics";
import { RealmArt } from "@/components/RealmArt";

const realms = [
  { slug: "forest", number: "01", name: "Forest", title: "The art of beginning again", description: "Canopy and soil inspire early care concepts and questions about ingredients, sourcing and renewal." },
  { slug: "ocean", number: "02", name: "Ocean", title: "Ideas in motion", description: "The tides inspire compact formats while reminding us that aquatic and biodegradability claims demand evidence." },
  { slug: "mountain", number: "03", name: "Mountain", title: "A clearer perspective", description: "Stone and elevation frame our exploration of minerals, materials and considered household care." },
];

export default function RealmsPage() {
  return <main id="main"><Analytics page="realms" /><section className="page-hero page-hero--dark"><div className="shell"><p className="section-number">WORLD OF BREW67 / 001</p><h1>Three realms.<br /><em>Many possibilities.</em></h1><p>Step into each realm to explore its story and the concept brews it inspires. Every practical detail remains open to testing and review.</p></div></section>
    <section className="content-section shell"><div className="realm-grid">{realms.map((realm) => <Link key={realm.slug} className={`realm-tile realm-tile--${realm.slug}`} href={`/realms/${realm.slug}`}><div className="realm-tile__top"><span>{realm.number} / REALM</span><span aria-hidden="true">↗</span></div><RealmArt realm={realm.slug} /><div className="realm-tile__bottom"><span>{realm.title}</span><h3>{realm.name}</h3><p>{realm.description}</p></div></Link>)}</div></section>
  </main>;
}
