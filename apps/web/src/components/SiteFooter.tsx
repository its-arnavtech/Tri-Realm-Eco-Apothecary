import Link from "next/link";

export function SiteFooter() {
  return <footer className="site-footer">
    <div className="shell site-footer__grid">
      <div><div className="footer-brand">✦ brew67potions</div><p>An exploration of care, place, and possibility. Inspired by Forest, Ocean, and Mountain.</p></div>
      <div><h2>Explore</h2><Link href="/realms">The realms</Link><Link href="/catalog">Concept gallery</Link><Link href="/about">Our approach</Link></div>
      <div><h2>Information</h2><Link href="/privacy">Privacy</Link><p>Every brew shown here is a concept. Nothing is offered for sale.</p></div>
    </div>
    <div className="shell site-footer__bottom"><span>© 2026 brew67potions</span><span>Imagery and concepts are illustrative.</span></div>
  </footer>;
}
