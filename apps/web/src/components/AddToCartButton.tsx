"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { addToCart } from "@/lib/client";
import { track } from "./Analytics";

export function AddToCartButton({ productId, productSlug, quantity = 1, concept = true }: { productId: string; productSlug: string; quantity?: number; concept?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  async function add() {
    setBusy(true); setError("");
    try {
      await addToCart(productId, quantity);
      track("add_to_cart", { product_slug: productSlug });
      router.push("/cart");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update cart."); }
    finally { setBusy(false); }
  }
  return <div><button type="button" className="button button--gold" disabled={busy} onClick={add}>{busy ? "Adding…" : concept ? "Add to concept cart" : "Add to cart"} <span aria-hidden="true">↗</span></button>{error && <p className="alert" role="alert">{error}</p>}</div>;
}
