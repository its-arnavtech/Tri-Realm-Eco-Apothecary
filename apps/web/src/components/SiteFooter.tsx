import Link from "next/link";

export function SiteFooter() {
  return <footer className="site-footer">
    <div className="shell site-footer__grid">
      <div><div className="footer-brand">✦ brew67potions</div><p>Three realms. One thoughtful way to explore what comes next.</p></div>
      <div><h2>Explore</h2><Link href="/realms">The realms</Link><Link href="/catalog">The brews</Link><Link href="/configure">The configurator</Link></div>
      <div><h2>Information</h2><Link href="/about">Our approach</Link><Link href="/privacy">Privacy & consent</Link><Link href="/cart">Concept cart</Link></div>
    </div>
    <div className="shell site-footer__bottom"><span>© 2026 brew67potions</span><span>Proof of concept · Products shown are not approved for sale or use.</span></div>
  </footer>;
}
