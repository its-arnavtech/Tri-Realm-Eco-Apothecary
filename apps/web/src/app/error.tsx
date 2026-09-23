"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return <main id="main" className="content-section shell"><p className="section-number">TEMPORARILY UNAVAILABLE</p><h1>We couldn’t load the apothecary.</h1><p>Please try again in a moment.</p><button className="button button--outline" onClick={reset}>Try again</button></main>;
}
