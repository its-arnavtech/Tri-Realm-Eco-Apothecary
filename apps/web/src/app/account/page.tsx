"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { money } from "@/lib/api";
import { request } from "@/lib/client";

type Customer = { id: string; email: string; role: string; email_verified: boolean;
  preferences: { preferred_biome?: string } };
type Order = { id: string; status: string; payment_status: string; fulfillment_status: string;
  total_cents: number | null; subtotal_cents: number; created_at: string;
  items: { name: string; quantity: number }[] };
type Subscription = { id: string; product_id: string; status: string;
  current_period_end: string | null; cancel_at_period_end: boolean };
type PrivacyRequest = { id: string; type: string; status: string; created_at: string };

export default function AccountPage() {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [biome, setBiome] = useState("");
  const [orders, setOrders] = useState<Order[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [privacyRequests, setPrivacyRequests] = useState<PrivacyRequest[]>([]);
  const [deletionPassword, setDeletionPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const user = await request<Customer>("/auth/me");
      setCustomer(user);
      setBiome(user.preferences.preferred_biome ?? "");
      const [orderList, subscriptionList, privacyList] = await Promise.all([
        request<Order[]>("/account/orders"), request<Subscription[]>("/account/subscriptions"),
        request<PrivacyRequest[]>("/account/privacy-requests"),
      ]);
      setOrders(orderList); setSubscriptions(subscriptionList); setPrivacyRequests(privacyList);
    } catch { setCustomer(null); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function authenticate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      await request<Customer>(`/auth/${mode}`, { method: "POST", body: JSON.stringify({ email, password }) });
      setPassword(""); await load();
      if (mode === "register") setMessage("Account created. Please verify your email using the link we sent.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not sign in."); }
    finally { setBusy(false); }
  }

  async function savePreference(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const user = await request<Customer>("/auth/preferences", { method: "PATCH",
        body: JSON.stringify({ preferred_biome: biome || null }) });
      setCustomer(user); setMessage("Preference saved.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save preference."); }
    finally { setBusy(false); }
  }

  async function signOut() {
    setBusy(true); setError("");
    try { await request("/auth/logout", { method: "POST" }); setCustomer(null); setOrders([]); setSubscriptions([]); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not sign out."); }
    finally { setBusy(false); }
  }

  async function resendVerification() {
    setBusy(true); setError("");
    try {
      const result = await request<{ message?: string; sent: boolean }>("/auth/verification/resend", { method: "POST" });
      setMessage(result.sent ? "A new verification link is on its way." : result.message ?? "A verification link was recently sent.");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not resend verification."); }
    finally { setBusy(false); }
  }

  async function billingPortal() {
    setBusy(true); setError("");
    try {
      const response = await request<{ portal_url: string }>("/account/subscriptions/portal", { method: "POST" });
      window.location.assign(response.portal_url);
    } catch (err) { setError(err instanceof Error ? err.message : "Billing portal unavailable."); }
    finally { setBusy(false); }
  }

  async function exportData() {
    setBusy(true); setError("");
    try {
      const data = await request<Record<string, unknown>>("/account/privacy-export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "brew67-account-data.json"; link.click();
      URL.revokeObjectURL(url);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not export data."); }
    finally { setBusy(false); }
  }

  async function requestDeletion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await request("/account/privacy-requests", { method: "POST",
        body: JSON.stringify({ password: deletionPassword }) });
      setDeletionPassword(""); setMessage("Your deletion request was recorded for review.");
      setPrivacyRequests(await request<PrivacyRequest[]>("/account/privacy-requests"));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not submit request."); }
    finally { setBusy(false); }
  }

  return <main id="main" className="shell account-page">
    <p className="section-number">YOUR ACCOUNT / 005</p>
    <h1>Your <em>account.</em></h1>
    {error && <p className="alert" role="alert">{error}</p>}
    {message && <p className="success" role="status">{message}</p>}
    {loading ? <p>Loading account…</p> : customer ? <div className="account-grid">
      <section className="account-panel"><h2>Profile</h2><p><strong>{customer.email}</strong></p>
        <p>{customer.email_verified ? "Email verified" : "Email verification pending. Check your inbox before placing an order."}</p>
        {!customer.email_verified && <button className="text-link" onClick={resendVerification} disabled={busy}>Resend verification link →</button>}
        <form onSubmit={savePreference}><div className="field"><label htmlFor="preferred-biome">Preferred realm</label>
          <select id="preferred-biome" value={biome} onChange={(event) => setBiome(event.target.value)}>
            <option value="">No preference</option><option value="forest">Forest</option>
            <option value="ocean">Ocean</option><option value="mountain">Mountain</option>
            <option value="tri-realm">Tri Realm</option>
          </select></div><button className="button button--outline" disabled={busy}>Save preference</button></form>
        <button className="text-link account-signout" onClick={signOut} disabled={busy}>Sign out →</button>
        {(customer.role === "admin" || customer.role === "operations" || customer.role === "support") &&
          <p><Link className="text-link" href="/operations">Operations dashboard →</Link></p>}
      </section>
      <section className="account-panel"><h2>Orders</h2>
        {orders.length === 0 ? <p>No orders yet. Explore the collection for current availability.</p>
          : <ul className="account-list">{orders.map((order) => <li key={order.id}>
            <strong>Order {order.id.slice(0, 8)}</strong><span>{new Date(order.created_at).toLocaleDateString()}</span>
            <p>{order.items.map((item) => `${item.quantity} × ${item.name}`).join(", ")}</p>
            <p>Payment: {order.payment_status} · Fulfillment: {order.fulfillment_status}</p>
            <b>{money(order.total_cents ?? order.subtotal_cents)}</b>
          </li>)}</ul>}
      </section>
      <section className="account-panel"><h2>Refills and subscriptions</h2>
        {subscriptions.length === 0 ? <p>No subscriptions yet. Refills appear here once approved and available.</p>
          : <ul className="account-list">{subscriptions.map((item) => <li key={item.id}>
            <strong>Subscription {item.id.slice(0, 8)}</strong><p>Status: {item.status}</p>
            {item.current_period_end && <p>Current period ends {new Date(item.current_period_end).toLocaleDateString()}</p>}
          </li>)}</ul>}
        {subscriptions.length > 0 && <button className="button button--outline" disabled={busy} onClick={billingPortal}>Manage billing →</button>}
      </section>
      <section className="account-panel"><h2>Your data</h2>
        <p>Download a copy of your account, order, interest, and subscription records.</p>
        <button className="button button--outline" disabled={busy} onClick={exportData}>Download data →</button>
        <form onSubmit={requestDeletion}><h3>Request account deletion</h3>
          <p>We review open orders and subscriptions before redacting account data. Financial records may need to be retained.</p>
          <div className="field"><label htmlFor="deletion-password">Confirm your password</label>
            <input id="deletion-password" type="password" autoComplete="current-password" required
              value={deletionPassword} onChange={(event) => setDeletionPassword(event.target.value)} /></div>
          <button className="button button--outline" disabled={busy}>Submit deletion request</button></form>
        {privacyRequests.length > 0 && <ul className="account-list">{privacyRequests.map((item) =>
          <li key={item.id}>{item.type} · {item.status} · {new Date(item.created_at).toLocaleDateString()}</li>)}</ul>}
      </section>
    </div> : <section className="account-panel account-auth">
      <div className="account-tabs"><button aria-pressed={mode === "login"} onClick={() => setMode("login")}>Sign in</button>
        <button aria-pressed={mode === "register"} onClick={() => setMode("register")}>Create account</button></div>
      <p>{mode === "register" ? "Create an account for future orders and preferences." : "Sign in to see your orders and preferences."}</p>
      <form onSubmit={authenticate}><div className="field"><label htmlFor="account-email">Email address</label>
        <input id="account-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></div>
        <div className="field"><label htmlFor="account-password">Password</label>
          <input id="account-password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"}
            required minLength={mode === "register" ? 12 : undefined} value={password}
            onChange={(event) => setPassword(event.target.value)} /></div>
        {mode === "register" && <p className="muted">Use at least 12 characters. We will email a verification link.</p>}
        <button className="button button--gold" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account →" : "Sign in →"}</button>
      </form><p><Link className="text-link" href="/reset-password">Forgot your password?</Link></p>
    </section>}
  </main>;
}
