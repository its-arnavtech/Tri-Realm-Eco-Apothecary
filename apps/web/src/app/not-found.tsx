import Link from "next/link";

export default function NotFound() {
  return <main id="main" className="content-section shell"><p className="section-number">404 / NOT FOUND</p><h1>This path has no brew.</h1><p>Return to the collection and continue exploring.</p><Link className="button button--outline" href="/catalog">Browse the brews →</Link></main>;
}
