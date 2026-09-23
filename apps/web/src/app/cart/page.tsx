"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Analytics, track } from "@/components/Analytics";
import { RealmArt } from "@/components/RealmArt";
import { changeCartItem, obtainCart, request } from "@/lib/client";
import { money } from "@/lib/api";
import type { Cart } from "@/lib/types";

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [email, setEmail] = useState("");
  const [interest, setInterest] = useState("general");
  const [contactConsent, setContactConsent] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void obtainCart().then(setCart).catch((err) => setError(err.message)); }, []);

  async function update(itemId: string, quantity?: number) {
    if (!cart) return;
    setBusy(true); setError("");
    try { setCart(await changeCartItem(cart, itemId, quantity)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not update cart."); }
    finally { setBusy(false); }
  }

  async function submitInterest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await request("/intent-signups", { method: "POST", body: JSON.stringify({ email, interest,
        contact_consent: contactConsent, marketing_consent: marketingConsent }) });
      setSubmitted(true);
      track("intent_submitted", { page: "cart" });
    } catch (err) { setError(err instanceof Error ? err.message : "Could not submit interest."); }
    finally { setBusy(false); }
  }

  return <main id="main" className="cart-page shell"><Analytics page="cart" /><p className="section-number">YOUR COLLECTION / 004</p><div className="cart-page__layout"><div><h1>Concept <em>cart.</em></h1><p className="muted">This is a simulated cart for exploring product interest. No order or payment will be created.</p>
    {error && <p className="alert" role="alert">{error}</p>}
    {!cart ? <p>Loading your cart…</p> : cart.items.length === 0 ? <div className="empty-state"><h2>Your cart is waiting for a brew.</h2><Link href="/catalog" className="button button--outline">Explore the collection →</Link></div> : <div className="cart-items">{cart.items.map((item) => <div className="cart-item" key={item.id}><RealmArt realm={item.slug === "tri-realm-catalyst" ? "tri-realm" : item.slug.includes("tidal") ? "ocean" : item.slug.includes("glacial") ? "mountain" : "forest"} /><div><h2><Link href={`/catalog/${item.slug}`}>{item.name}</Link></h2><p>Illustrative {money(item.price_cents)} each</p><button className="cart-item__remove" disabled={busy} onClick={() => update(item.id)}>Remove</button></div><div><strong>{money(item.line_total_cents)}</strong><div className="cart-item__controls"><button aria-label={`Decrease ${item.name} quantity`} disabled={busy || item.quantity <= 1} onClick={() => update(item.id, item.quantity - 1)}>−</button><span aria-label={`Quantity ${item.quantity}`}>{item.quantity}</span><button aria-label={`Increase ${item.name} quantity`} disabled={busy || item.quantity >= 20} onClick={() => update(item.id, item.quantity + 1)}>+</button></div></div></div>)}</div>}
  </div><aside className="cart-summary"><h2>Your summary</h2><dl><dt>Illustrative subtotal</dt><dd>{money(cart?.subtotal_cents ?? 0)}</dd><dt>Shipping estimate</dt><dd>Unavailable</dd><dt>Tax estimate</dt><dd>Unavailable</dd><dt className="cart-summary__total">Total</dt><dd className="cart-summary__total">To be determined</dd></dl><p>Shipping and taxes cannot be estimated until a sale region, product details and fulfillment model are approved.</p>
    <div className="interest-form"><h3>Be part of what comes next</h3><p>Leave your email if you want a follow-up about these concepts.</p>{submitted ? <p className="success" role="status">Thank you. Your interest has been recorded with your consent preferences.</p> : <form onSubmit={submitInterest}><div className="field"><label htmlFor="email">Email address</label><input id="email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} /></div><div className="field"><label htmlFor="interest">What interests you?</label><select id="interest" value={interest} onChange={(event) => setInterest(event.target.value)}><option value="general">All concepts</option><option value="forest">Forest</option><option value="ocean">Ocean</option><option value="mountain">Mountain</option><option value="brew-67">Brew No. 67</option></select></div><div className="checkbox-field"><input id="contact-consent" type="checkbox" required checked={contactConsent} onChange={(event) => setContactConsent(event.target.checked)} /><label htmlFor="contact-consent">I agree to be contacted about my product interest.</label></div><div className="checkbox-field"><input id="marketing-consent" type="checkbox" checked={marketingConsent} onChange={(event) => setMarketingConsent(event.target.checked)} /><label htmlFor="marketing-consent">I also agree to receive occasional marketing updates. Optional.</label></div><p className="privacy-copy">We store your email, interest and consent choices. No payment is collected. See our <Link href="/privacy"><u>privacy notice</u></Link>.</p><button className="button button--gold" type="submit" disabled={busy || !contactConsent}>{busy ? "Submitting…" : "Register interest →"}</button></form>}</div>
  </aside></div></main>;
}
