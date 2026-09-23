import Link from "next/link";

export function SiteHeader() {
  return <header className="site-header">
    <div className="site-header__inner shell">
      <Link href="/" className="brand" aria-label="brew67potions home"><span className="brand__symbol">✦</span><span>brew<span className="brand__number">67</span>potions</span></Link>
      <nav className="main-nav" aria-label="Main navigation">
        <Link href="/realms">The realms</Link>
        <Link href="/catalog">The brews</Link>
        <Link href="/configure">Find your brew</Link>
        <Link href="/about">Our approach</Link>
      </nav>
      <Link href="/cart" className="cart-link" aria-label="View concept cart">Cart <span aria-hidden="true">↗</span></Link>
    </div>
  </header>;
}
