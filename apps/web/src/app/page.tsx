import Link from "next/link";
import { Analytics } from "@/components/Analytics";
import { RealmArt } from "@/components/RealmArt";
import { getProduct } from "@/lib/api";

const realms = [
  { slug: "forest", number: "01", name: "Forest", line: "Rooted in renewal", description: "Follow the quiet intelligence of canopy and soil." },
  { slug: "ocean", number: "02", name: "Ocean", line: "Moved by tides", description: "Explore compact formats with careful questions about water." },
  { slug: "mountain", number: "03", name: "Mountain", line: "Made for clarity", description: "Ascend into ideas shaped by stone and elevation." },
];

export default async function Home() {
  const flagship = await getProduct("tri-realm-catalyst");
  const flagshipAvailable = flagship?.availability_status === "available";
  return <main id="main"><Analytics page="home" />
    <section className="hero"><div className="hero__glow" /><div className="shell hero__layout">
      <div className="hero__copy"><div className="kicker"><span className="kicker__line" /> A new kind of apothecary</div>
        <h1>Discover the <em>magic</em> in making less.</h1>
        <p>Enter a world inspired by Forest, Ocean and Mountain. Explore each brew’s story, ingredients, current availability and evidence.</p>
        <div className="hero__actions"><Link className="button button--gold" href="/realms">Explore the realms <span aria-hidden="true">↗</span></Link><Link className="text-link" href="/configure">Find your brew <span aria-hidden="true">→</span></Link></div>
        <p className="hero__note">Check each brew page for its approval and availability status.</p>
      </div>
      <div className="hero__visual"><div className="hero__visual-orbit"><RealmArt realm="tri-realm" large /></div><div className="hero__visual-caption"><span>✦</span> THE TRI-REALM CATALYST <small>BREW NO. 67 · {flagshipAvailable ? "AVAILABLE" : "CONCEPT"}</small></div></div>
    </div><div className="hero__index shell"><span>01 / 03</span><span>SCROLL TO EXPLORE ↓</span></div></section>

    <section className="intro-section shell"><p className="section-number">THE THREE REALMS / 001</p><div className="intro-section__heading"><h2>Every great brew<br />begins <em>somewhere.</em></h2><p>Each realm gives our early product ideas a point of view. The practical details still matter: what it is, how it works and what evidence supports it.</p></div>
      <div className="realm-grid">{realms.map((realm) => <Link key={realm.slug} className={`realm-tile realm-tile--${realm.slug}`} href={`/realms/${realm.slug}`}><div className="realm-tile__top"><span>{realm.number} / REALM</span><span aria-hidden="true">↗</span></div><RealmArt realm={realm.slug} /><div className="realm-tile__bottom"><span>{realm.line}</span><h3>{realm.name}</h3><p>{realm.description}</p></div></Link>)}</div>
    </section>

    <section className="feature-section"><div className="shell feature-section__inner"><div className="feature-section__art"><RealmArt realm="tri-realm" large /><span className="feature-section__seal">BREW<br />67</span></div><div className="feature-section__copy"><p className="section-number">THE FLAGSHIP BREW / 002</p><h2>One idea.<br /><em>Three realms.</em></h2><p>{flagshipAvailable ? "Meet the Tri-Realm Catalyst. Read its reviewed formulation, use instructions and availability before checkout." : "The Tri-Realm Catalyst explores a starter format for general household surfaces. Read its concept status and the questions still under review."} Our configurator explains its recommendation rules.</p><Link className="button button--outline" href="/catalog/tri-realm-catalyst">Meet Brew No. 67 <span aria-hidden="true">↗</span></Link></div></div></section>

    <section className="manifesto shell"><p className="section-number">OUR APPROACH / 003</p><h2>Wonder should spark questions.<br /><em>Evidence should answer them.</em></h2><div className="manifesto__grid"><p>We’re building a more engaging way to explore refill-oriented products. The story makes discovery inviting; clear product information and validated evidence must carry the decision.</p><div><Link href="/about" className="text-link">How we think about claims <span aria-hidden="true">↗</span></Link><Link href="/catalog" className="text-link">Browse the brews <span aria-hidden="true">↗</span></Link></div></div></section>
  </main>;
}
