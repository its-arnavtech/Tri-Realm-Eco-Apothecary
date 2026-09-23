import Link from "next/link";
import { RealmArt } from "@/components/RealmArt";
import { realms } from "@/lib/content";

export default function Home() {
  return <main id="main">
    <section className="hero hero--editorial">
      <div className="hero__image" aria-hidden="true" />
      <div className="shell hero__layout"><div className="hero__copy">
        <p className="kicker"><span className="kicker__line" /> An apothecary of ideas</p>
        <h1>Wonder, drawn<br />from the <em>natural world.</em></h1>
        <p>Meet brew67potions: a creative exploration of everyday care through three distinct realms. Discover the stories and early concepts taking shape.</p>
        <div className="hero__actions"><Link className="button button--gold" href="/realms">Enter the realms <span aria-hidden="true">↗</span></Link><Link className="text-link" href="/catalog">Explore the concepts <span aria-hidden="true">→</span></Link></div>
        <p className="hero__note">A concept experience. No products are available for purchase.</p>
      </div></div>
      <div className="hero__index shell"><span>FOREST / OCEAN / MOUNTAIN</span><span>SCROLL TO EXPLORE ↓</span></div>
    </section>

    <div className="story-ribbon"><div className="shell"><span>THREE REALMS</span><span aria-hidden="true">✦</span><span>ONE CREATIVE WORLD</span><span aria-hidden="true">✦</span><span>IDEAS IN DEVELOPMENT</span></div></div>

    <section className="intro-section shell"><p className="section-number">A WORLD TO EXPLORE / 001</p>
      <div className="intro-section__heading"><h2>Every idea<br />begins <em>somewhere.</em></h2><p>Forest, Ocean, and Mountain each bring a different point of view. Together, they shape an imaginative world grounded in careful questions.</p></div>
      <div className="realm-grid">{realms.map((realm) => <Link key={realm.slug} className={`realm-tile realm-tile--${realm.slug}`} href={`/realms/${realm.slug}`}><div className="realm-tile__top"><span>{realm.number} / REALM</span><span aria-hidden="true">↗</span></div><RealmArt realm={realm.slug} /><div className="realm-tile__bottom"><span>{realm.tagline}</span><h3>{realm.name}</h3><p>{realm.introduction}</p></div></Link>)}</div>
    </section>

    <section className="feature-section"><div className="shell feature-section__inner"><div className="feature-section__art"><RealmArt realm="tri-realm" large /><span className="feature-section__seal">BREW<br />67</span></div><div className="feature-section__copy"><p className="section-number">THE TRI-REALM IDEA / 002</p><h2>One idea.<br /><em>Three realms.</em></h2><p>The Tri-Realm Catalyst brings the world of brew67potions together in a proposed starter format. Today it is a concept: a way to explore design, ritual, and the questions a real product would need to answer.</p><Link className="button button--outline" href="/catalog/tri-realm-catalyst">Discover Brew No. 67 <span aria-hidden="true">↗</span></Link></div></div></section>

    <section className="manifesto shell"><p className="section-number">OUR POINT OF VIEW / 003</p><h2>Let curiosity lead.<br /><em>Let clarity follow.</em></h2><div className="manifesto__grid"><p>We believe a compelling story should invite exploration and leave room for honest answers. The concepts here are early ideas, presented with their open questions in plain sight.</p><div><Link href="/about" className="text-link">Read our approach <span aria-hidden="true">↗</span></Link><Link href="/catalog" className="text-link">See every concept <span aria-hidden="true">↗</span></Link></div></div></section>
  </main>;
}
