"use client";

import { useEffect, useState } from "react";
import { request } from "@/lib/client";

export function SubscribeButton({ productId }: { productId: string }) {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    void request<{ subscriptions_enabled: boolean }>("/capabilities")
      .then((result) => setEnabled(result.subscriptions_enabled)).catch(() => {});
  }, []);
  async function start() {
    setBusy(true); setError("");
    try {
      const result = await request<{ checkout_url: string }>(`/account/subscriptions/${productId}/checkout`, { method: "POST" });
      if (!result.checkout_url.startsWith("https://")) throw new Error("Invalid checkout URL.");
      window.location.assign(result.checkout_url);
    } catch (err) { setError(err instanceof Error ? err.message : "Subscription unavailable."); }
    finally { setBusy(false); }
  }
  if (!enabled) return null;
  return <span><button className="button button--outline" onClick={start} disabled={busy}>
    {busy ? "Please wait…" : "Start a refill plan →"}</button>
    {error && <span className="alert" role="alert">{error}</span>}</span>;
}
