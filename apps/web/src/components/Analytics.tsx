"use client";

import { useEffect } from "react";

type EventName = "page_view" | "biome_viewed" | "product_viewed" | "configurator_started" |
  "configurator_step_completed" | "recommendation_generated" | "add_to_cart" |
  "checkout_started" | "intent_submitted" | "refill_viewed" | "cta_clicked";

const id = (key: string) => {
  let value = sessionStorage.getItem(key);
  if (!value) {
    value = crypto.randomUUID().replaceAll("-", "");
    sessionStorage.setItem(key, value);
  }
  return value;
};

export function track(event_name: EventName, context: Record<string, string> = {}) {
  if (typeof window === "undefined") return;
  const payload = JSON.stringify({ event_name, anonymous_id: id("brew67_anon"),
    session_id: id("brew67_session"), context: { experiment_version: "narrative-v1", ...context }, schema_version: "1" });
  void fetch("/api/v1/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: payload, keepalive: true });
}

export function Analytics({ page, biome, product }: { page: string; biome?: string; product?: string }) {
  useEffect(() => {
    track("page_view", { page });
    if (biome) track("biome_viewed", { page, biome });
    if (product) track("product_viewed", { page, product_slug: product });
  }, [page, biome, product]);
  return null;
}
