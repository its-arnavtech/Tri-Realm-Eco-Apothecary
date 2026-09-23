import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Our approach", description: "The thinking behind the brew67potions concept world." };

export default function AboutPage() {
  return <main id="main"><section className="page-hero page-hero--about"><div className="shell"><p className="section-number">OUR APPROACH / 003</p><h1>Imagination, with<br /><em>room for truth.</em></h1><p>brew67potions begins with a simple idea: a world can be enchanting and still be clear about what is real, what is possible, and what remains to be learned.</p></div></section>
    <section className="content-section shell"><div className="about-intro"><p className="section-number">THE THINKING BEHIND THE WORLD</p><h2>Inspired by place.<br />Guided by questions.</h2><p>Forest, Ocean, and Mountain are creative lenses. They shape the atmosphere of each concept; they are not claims about ingredients, performance, or impact.</p></div><div className="info-grid"><div className="info-card"><p className="section-number">01 / IMAGINE</p><h2>Start with a story</h2><p>Every brew begins as a question about an everyday ritual, a format, or a material direction.</p></div><div className="info-card"><p className="section-number">02 / EXPLAIN</p><h2>Show what’s open</h2><p>We label early concepts plainly and share the practical details that would need validation.</p></div><div className="info-card"><p className="section-number">03 / EARN TRUST</p><h2>Let evidence speak</h2><p>Specific safety, performance, and environmental claims belong only after a documented review.</p></div></div></section>
    <section className="about-statement"><div className="shell"><p className="section-number">WHERE WE ARE TODAY</p><h2>For now, this is a place to explore.</h2><p>Nothing on this website is available to buy or use. The imagery and product ideas are conceptual. If the ideas become real products, formulation, safety, labeling, instructions, and evidence would come first.</p><Link href="/catalog" className="button button--gold">Explore the concepts <span aria-hidden="true">↗</span></Link></div></section>
  </main>;
}
