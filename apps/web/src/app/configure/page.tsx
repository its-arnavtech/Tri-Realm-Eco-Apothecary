"use client";

import Link from "next/link";
import { useState } from "react";
import { Analytics, track } from "@/components/Analytics";
import { RealmArt } from "@/components/RealmArt";
import { request, addToCart } from "@/lib/client";
import { useRouter } from "next/navigation";
import type { Product, Recommendation, RecommendationInput } from "@/lib/types";

const initial: RecommendationInput = { water_hardness: "unknown", household_size: 2, usage_area: "general_surfaces", purchase_type: "starter" };

export default function ConfigurePage() {
  const [answers, setAnswers] = useState<RecommendationInput>(initial);
  const [result, setResult] = useState<Recommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setResult(null);
    track("configurator_started", { page: "configure" });
    try {
      const response = await request<Recommendation>("/recommendations", { method: "POST", body: JSON.stringify(answers) });
      setResult(response);
      track("configurator_step_completed", { page: "configure", step: "answers" });
      track("recommendation_generated", { page: "configure", product_slug: response.product_slug ?? "none" });
    } catch (err) { setError(err instanceof Error ? err.message : "Could not generate a recommendation."); }
    finally { setBusy(false); }
  }

  async function addRecommendation() {
    if (!result?.product_slug) return;
    setBusy(true); setError("");
    try {
      const product = await request<Product>(`/products/${result.product_slug}`);
      await addToCart(product.id, result.quantity);
      track("add_to_cart", { page: "configure", product_slug: product.slug });
      router.push("/cart");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update the cart."); }
    finally { setBusy(false); }
  }

  return <main id="main" className="configurator shell"><Analytics page="configure" /><p className="section-number">THE GUIDED PATH / 003</p><div className="configurator__layout"><div><h1>Find your <em>brew.</em></h1><p className="configurator__intro">A few practical questions help us suggest a concept format. These early rules do not change the formulation or claim tested performance.</p>
    <form className="form-panel" onSubmit={submit}><h2>Tell us about your space</h2><div className="form-grid">
      <div className="field"><label htmlFor="usage">Primary usage area</label><select id="usage" value={answers.usage_area} onChange={(event) => setAnswers({ ...answers, usage_area: event.target.value as RecommendationInput["usage_area"] })}><option value="general_surfaces">General household surfaces</option><option value="garden">Garden</option><option value="personal_care">Personal care</option><option value="water_treatment">Water treatment</option></select></div>
      <div className="field"><label htmlFor="household">Household size</label><input id="household" type="number" min="1" max="12" required value={answers.household_size} onChange={(event) => setAnswers({ ...answers, household_size: Number(event.target.value) })} /></div>
      <div className="field"><label htmlFor="hardness">Water hardness</label><select id="hardness" value={answers.water_hardness} onChange={(event) => setAnswers({ ...answers, water_hardness: event.target.value as RecommendationInput["water_hardness"] })}><option value="unknown">I’m not sure</option><option value="soft">Soft</option><option value="moderate">Moderate</option><option value="hard">Hard</option></select></div>
      <div className="field"><label htmlFor="purchase">Preferred format</label><select id="purchase" value={answers.purchase_type} onChange={(event) => setAnswers({ ...answers, purchase_type: event.target.value as RecommendationInput["purchase_type"] })}><option value="starter">Starter concept</option><option value="refill">Refill concept</option></select></div>
    </div><button className="button button--gold" type="submit" disabled={busy}>{busy ? "Finding…" : "See recommendation"} <span aria-hidden="true">→</span></button></form>
    {error && <p className="alert" role="alert">{error}</p>}
    {result && <section className="recommendation" aria-live="polite"><p className="recommendation__meta">Rule set {result.rule_set_version} · {result.supported ? "Supported concept path" : "No supported match"}</p><h2>{result.supported ? "Your concept match" : "A careful pause"}</h2><p>{result.rationale}</p><p><strong>Inputs used:</strong> {result.inputs.household_size} people; {result.inputs.usage_area.replaceAll("_", " ")}; {result.inputs.water_hardness} water; {result.inputs.purchase_type} format.</p><h3>Assumptions</h3><ul>{result.assumptions.map((item) => <li key={item}>{item}</li>)}</ul><h3>Limitations</h3><ul>{result.warnings.map((item) => <li key={item}>{item}</li>)}</ul>{result.supported && result.product_slug && <div className="detail__actions"><button className="button button--gold" disabled={busy} onClick={addRecommendation}>Add {result.quantity} to concept cart →</button><Link className="text-link" href={`/catalog/${result.product_slug}`}>Read product details ↗</Link></div>}</section>}
  </div><aside className="configurator__aside"><RealmArt realm="tri-realm" /><p className="eyebrow">BREW NO. 67</p><h2>The Tri-Realm Catalyst</h2><p>This POC recommends only the proposed starter concept for general household surfaces. The answer is an explanation of a rule, not a safety assessment.</p><ul><li>Unsupported uses return no product recommendation.</li><li>Water hardness never changes the formula.</li><li>Refill compatibility remains unverified.</li></ul></aside></div></main>;
}
