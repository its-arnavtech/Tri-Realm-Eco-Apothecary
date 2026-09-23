import type { Cart } from "./types";

const base = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";
const storageKey = "brew67_cart";

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? `Request failed: ${response.status}`);
  return body as T;
}

export async function obtainCart(): Promise<Cart> {
  const saved = localStorage.getItem(storageKey);
  const token = saved ? JSON.parse(saved).token as string : undefined;
  const cart = await request<Cart>("/carts", { method: "POST", body: JSON.stringify({ token }) });
  localStorage.setItem(storageKey, JSON.stringify({ id: cart.id, token: cart.token }));
  return cart;
}

export async function addToCart(productId: string, quantity = 1): Promise<Cart> {
  const cart = await obtainCart();
  const updated = await request<Cart>(`/carts/${cart.id}/items`, {
    method: "POST",
    headers: { "X-Cart-Token": cart.token },
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  window.dispatchEvent(new Event("brew67-cart-updated"));
  return updated;
}

export async function changeCartItem(cart: Cart, itemId: string, quantity?: number): Promise<Cart> {
  const updated = await request<Cart>(`/carts/${cart.id}/items/${itemId}`, {
    method: quantity === undefined ? "DELETE" : "PATCH",
    headers: { "X-Cart-Token": cart.token },
    ...(quantity === undefined ? {} : { body: JSON.stringify({ quantity }) }),
  });
  window.dispatchEvent(new Event("brew67-cart-updated"));
  return updated;
}
