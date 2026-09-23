"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { money } from "@/lib/api";
import { request } from "@/lib/client";
import type { Product as PublicProduct } from "@/lib/types";

type Product = { id: string; name: string; slug: string; active: boolean; availability_status: string;
  release_errors: string[]; inventory: { sku: string; on_hand: number; reserved: number; available: number } | null;
  approvals: { gate: string; status: string; evidence_reference: string | null }[] };
type Order = { id: string; customer_id: string; status: string; payment_status: string;
  fulfillment_status: string; total_cents: number | null; created_at: string;
  items: { name: string; quantity: number }[] };
type Evidence = { formulations: { id: string; version_label: string; status: string;
  safety_document_reference: string | null }[]; claims: { id: string; claim_text: string;
  status: string; source_reference: string }[]; impacts: { id: string; metric_type: string;
  status: string; source_reference: string }[] };
type PrivacyRequest = { id: string; customer_id: string; type: string; status: string;
  provider_customer_id: string | null; created_at: string };
type Metrics = { window_days: number; funnel_events: Record<string, number>;
  orders_by_status: Record<string, number>; low_stock_skus: number;
  failed_email: number; pending_email: number; processed_payment_events: number };
const gates = ["formulation", "safety", "label", "claims", "shipping", "tax", "fulfillment", "support"];

export default function OperationsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [privacyRequests, setPrivacyRequests] = useState<PrivacyRequest[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selected, setSelected] = useState("");
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [gate, setGate] = useState(gates[0]);
  const [reference, setReference] = useState("");
  const [reason, setReason] = useState("");
  const [sku, setSku] = useState("");
  const [adjustment, setAdjustment] = useState(0);
  const [threshold, setThreshold] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [allowed, setAllowed] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [staffEmail, setStaffEmail] = useState("");
  const [staffRole, setStaffRole] = useState("support");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [formulationLabel, setFormulationLabel] = useState("");
  const [formulationSafety, setFormulationSafety] = useState("");
  const [claimText, setClaimText] = useState("");
  const [claimSource, setClaimSource] = useState("");
  const [impactMetric, setImpactMetric] = useState("");
  const [impactValue, setImpactValue] = useState("");
  const [impactUnit, setImpactUnit] = useState("");
  const [impactBaseline, setImpactBaseline] = useState("");
  const [impactComparison, setImpactComparison] = useState("");
  const [impactMethod, setImpactMethod] = useState("");
  const [impactQualification, setImpactQualification] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [newBrewNumber, setNewBrewNumber] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newName, setNewName] = useState("");
  const [newBiome, setNewBiome] = useState("forest");

  const load = useCallback(async () => {
    try {
      const user = await request<{ role: string }>("/auth/me");
      if (!["admin", "operations", "support"].includes(user.role)) return;
      setAllowed(true); setCanEdit(user.role !== "support");
      setIsAdmin(user.role === "admin");
      const [productList, orderList, privacyList, metricsSnapshot] = await Promise.all([
        request<Product[]>("/admin/products"), request<Order[]>("/admin/orders"),
        user.role === "admin" ? request<PrivacyRequest[]>("/admin/privacy-requests") : Promise.resolve([]),
        request<Metrics>("/admin/metrics"),
      ]);
      setProducts(productList); setOrders(orderList); setPrivacyRequests(privacyList);
      setMetrics(metricsSnapshot);
      setSelected((current) => current || productList[0]?.id || "");
      setSku(productList.find((item) => item.id === selected)?.inventory?.sku ?? productList[0]?.inventory?.sku ?? "");
    } catch { setAllowed(false); }
  }, [selected]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  useEffect(() => {
    if (!selected) return;
    void request<Evidence>(`/admin/products/${selected}/evidence`).then(setEvidence).catch(() => setEvidence(null));
    if (products.some((row) => row.id === selected)) void request<PublicProduct>(`/admin/products/${selected}`).then((publicProduct) => setDraft({
      name: publicProduct.name, subtitle: publicProduct.subtitle,
      description: publicProduct.description, product_type: publicProduct.product_type,
      form_factor: publicProduct.form_factor, unit_size: publicProduct.unit_size,
      price_cents: String(publicProduct.price_cents),
      ingredients: publicProduct.ingredients.join(", "),
      usage_instructions: publicProduct.usage_instructions, warnings: publicProduct.warnings,
      storage_instructions: publicProduct.storage_instructions,
      packaging: publicProduct.packaging, shipping_details: publicProduct.shipping_details,
    })).catch(() => setDraft({}));
  }, [selected, products]);
  const product = products.find((item) => item.id === selected);

  async function action(fn: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await fn(); setMessage(success); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Operation failed."); }
    finally { setBusy(false); }
  }

  async function approveGate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}/release/${gate}`, {
      method: "PUT", body: JSON.stringify({ status: "approved", evidence_reference: reference, reason }),
    }), `${gate} gate recorded.`);
  }

  async function adjustStock(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}/inventory`, {
      method: "PUT", body: JSON.stringify({ sku, adjustment, low_stock_threshold: threshold, reason }),
    }), "Inventory updated.");
    setAdjustment(0);
  }

  async function publish(status: "available" | "concept") {
    if (!product) return;
    await action(() => request(`/admin/products/${product.id}`, {
      method: "PATCH", headers: { "X-Reason": reason || "Product publication review" },
      body: JSON.stringify({ availability_status: status }),
    }), status === "available" ? "Product published." : "Product returned to concept status.");
  }

  async function setVisibility(active: boolean) {
    if (!product) return;
    await action(() => request(`/admin/products/${product.id}`, {
      method: "PATCH", headers: { "X-Reason": reason || "Product visibility review" },
      body: JSON.stringify({ active, ...(active ? {} : { availability_status: "concept" }) }),
    }), active ? "Concept is visible in the catalog." : "Product hidden from the catalog.");
  }

  async function createDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setMessage("");
    try {
      const created = await request<PublicProduct>("/admin/products", {
        method: "POST", headers: { "X-Reason": reason || "New product concept draft" },
        body: JSON.stringify({ brew_number: Number(newBrewNumber), slug: newSlug,
          name: newName, biome_slug: newBiome }),
      });
      setNewBrewNumber(""); setNewSlug(""); setNewName("");
      setSelected(created.id);
      setMessage("Private concept draft created. Complete the record before showing it in the catalog.");
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create draft."); }
    finally { setBusy(false); }
  }

  async function review(kind: "formulations" | "claims" | "impact", id: string) {
    const path = kind === "formulations" ? `/admin/formulations/${id}/review`
      : kind === "claims" ? `/admin/claims/${id}/review` : `/admin/impact/${id}/review`;
    await action(() => request(path, { method: "PATCH",
      body: JSON.stringify({ status: "approved", reason,
        ...(kind === "formulations" ? {} : { evidence_reference: reference }) }),
    }), "Evidence approved.");
    if (selected) setEvidence(await request<Evidence>(`/admin/products/${selected}/evidence`));
  }

  async function fulfill(orderId: string) {
    await action(() => request(`/admin/orders/${orderId}/fulfillment`, {
      method: "PATCH", body: JSON.stringify({ status: "shipped", reason }),
    }), "Order marked shipped.");
  }

  async function refund(orderId: string) {
    await action(() => request(`/admin/orders/${orderId}/refunds`, { method: "POST",
      body: JSON.stringify({ amount_cents: Number(refundAmount), reason }),
    }), "Refund request recorded.");
    setRefundAmount("");
  }

  async function allocate(orderId: string) {
    await action(() => request(`/admin/orders/${orderId}/allocate`, { method: "POST" }),
      "Paid refill order allocated.");
  }

  async function processPrivacy(item: PrivacyRequest) {
    const step = item.status === "pending" ? "redact" : "complete";
    await action(() => request(`/admin/privacy-requests/${item.id}/${step}`, { method: "POST",
      body: JSON.stringify({ reason, evidence_reference: reference }),
    }), step === "redact" ? "Local account redaction completed." : "External provider follow-up completed.");
  }

  async function changeRole(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await action(() => request("/admin/staff/role", { method: "PATCH",
      body: JSON.stringify({ email: staffEmail, role: staffRole, reason }),
    }), "Staff role updated; existing sessions were revoked.");
  }

  async function saveProduct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}`, { method: "PATCH",
      headers: { "X-Reason": reason }, body: JSON.stringify({ ...draft,
        price_cents: Number(draft.price_cents),
        ingredients: draft.ingredients.split(",").map((item) => item.trim()).filter(Boolean),
      }),
    }), "Product record saved.");
  }

  async function addFormulation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}/formulations`, { method: "POST",
      headers: { "X-Reason": reason }, body: JSON.stringify({ version_label: formulationLabel,
        ingredients: draft.ingredients?.split(",").map((item) => item.trim()).filter(Boolean) ?? [],
        safety_document_reference: formulationSafety }),
    }), "Formulation draft created.");
    setEvidence(await request<Evidence>(`/admin/products/${product.id}/evidence`));
  }

  async function addClaim(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}/claims`, { method: "POST",
      headers: { "X-Reason": reason }, body: JSON.stringify({ claim_text: claimText,
        evidence_type: "reviewed documentation", source_reference: claimSource }),
    }), "Claim draft created.");
    setEvidence(await request<Evidence>(`/admin/products/${product.id}/evidence`));
  }

  async function addImpact(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!product) return;
    await action(() => request(`/admin/products/${product.id}/impact`, { method: "POST",
      body: JSON.stringify({ metric_type: impactMetric, factor_value: impactValue,
        unit: impactUnit, baseline: impactBaseline, comparison_scenario: impactComparison,
        methodology_version: impactMethod, source_reference: reference,
        qualification: impactQualification }),
    }), "Impact factor draft created.");
    setEvidence(await request<Evidence>(`/admin/products/${product.id}/evidence`));
  }

  return <main id="main" className="shell operations-page"><p className="section-number">OPERATIONS / 006</p>
    <h1>Release and <em>operations.</em></h1>
    {!allowed ? <p>This dashboard requires a staff account. <Link className="text-link" href="/account">Go to account →</Link></p>
      : <><p className="operations-note">Review each evidence reference against its source before approving a gate. Concepts remain unavailable for sale until all release gates pass.</p>
        {error && <p className="alert" role="alert">{error}</p>}
        {message && <p className="success" role="status">{message}</p>}
        <div className="operations-grid">{metrics && <section className="operations-panel operations-panel--wide"><h2>Operational pulse</h2>
          <p>Last {metrics.window_days} days · {metrics.processed_payment_events} verified payment events</p>
          <p>{metrics.low_stock_skus} low stock SKUs · {metrics.pending_email} pending emails · {metrics.failed_email} failed emails</p>
          <h3>Funnel events</h3><ul className="account-list">{Object.entries(metrics.funnel_events).map(([name, count]) =>
            <li key={name}>{name.replaceAll("_", " ")}: {count}</li>)}</ul>
          <h3>Orders by status</h3><ul className="account-list">{Object.entries(metrics.orders_by_status).map(([name, count]) =>
            <li key={name}>{name.replaceAll("_", " ")}: {count}</li>)}</ul>
        </section>}
        {canEdit && <section className="operations-panel"><h2>Create product draft</h2>
          <p>A new product stays private and cannot be sold until its record and release evidence are approved.</p>
          <form onSubmit={createDraft}>
            <div className="field"><label htmlFor="new-brew-number">Brew number</label><input id="new-brew-number" type="number" min={1} required value={newBrewNumber} onChange={(event) => setNewBrewNumber(event.target.value)} /></div>
            <div className="field"><label htmlFor="new-slug">URL slug</label><input id="new-slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" value={newSlug} onChange={(event) => setNewSlug(event.target.value)} /></div>
            <div className="field"><label htmlFor="new-name">Name</label><input id="new-name" required minLength={2} value={newName} onChange={(event) => setNewName(event.target.value)} /></div>
            <div className="field"><label htmlFor="new-biome">Biome</label><select id="new-biome" value={newBiome} onChange={(event) => setNewBiome(event.target.value)}><option value="forest">Forest</option><option value="ocean">Ocean</option><option value="mountain">Mountain</option></select></div>
            <button className="button button--outline" disabled={busy}>Create private draft →</button>
          </form>
        </section>}
        <section className="operations-panel"><h2>Products and release</h2>
          <div className="field"><label htmlFor="ops-product">Product</label><select id="ops-product" value={selected} onChange={(event) => { setSelected(event.target.value); setSku(products.find((item) => item.id === event.target.value)?.inventory?.sku ?? ""); }}>
            {products.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.active ? item.availability_status : "private draft"}</option>)}</select></div>
          {product && <><p>Status: <strong>{product.active ? product.availability_status : "private draft"}</strong></p>
            {product.release_errors.length ? <ul>{product.release_errors.map((item) => <li key={item}>{item}</li>)}</ul>
              : <p className="success">All recorded release checks pass.</p>}
            <p>Stock: {product.inventory ? `${product.inventory.available} available (${product.inventory.reserved} reserved)` : "No inventory record"}</p>
            {canEdit && <><form onSubmit={approveGate}><h3>Record gate approval</h3>
              <div className="field"><label htmlFor="gate">Gate</label><select id="gate" value={gate} onChange={(event) => setGate(event.target.value)}>
                {gates.map((item) => <option key={item}>{item}</option>)}</select></div>
              <div className="field"><label htmlFor="reference">Evidence reference</label><input id="reference" required minLength={8} value={reference} onChange={(event) => setReference(event.target.value)} /></div>
              <div className="field"><label htmlFor="reason">Review reason</label><textarea id="reason" required minLength={5} value={reason} onChange={(event) => setReason(event.target.value)} /></div>
              <button className="button button--outline" disabled={busy}>Approve gate</button></form>
              {!product.active && <button className="button button--outline" disabled={busy} onClick={() => setVisibility(true)}>Show concept in catalog</button>}
              {product.active && <button className="button button--outline" disabled={busy} onClick={() => setVisibility(false)}>Hide product</button>}
              <button className="button button--gold" disabled={busy || product.release_errors.length > 0} onClick={() => publish("available")}>Publish product →</button>
              <button className="button button--outline" disabled={busy} onClick={() => publish("concept")}>Return to concept</button></>}
          </>}
        </section><section className="operations-panel"><h2>Inventory</h2>
          {product && <form onSubmit={adjustStock}><p>Each adjustment creates an inventory movement and audit event.</p>
            <div className="field"><label htmlFor="sku">SKU</label><input id="sku" required minLength={2} disabled={!canEdit} value={sku} onChange={(event) => setSku(event.target.value)} /></div>
            <div className="field"><label htmlFor="adjustment">Quantity adjustment</label><input id="adjustment" type="number" disabled={!canEdit} value={adjustment} onChange={(event) => setAdjustment(Number(event.target.value))} /></div>
            <div className="field"><label htmlFor="threshold">Low stock threshold</label><input id="threshold" type="number" min={0} disabled={!canEdit} value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} /></div>
            <button className="button button--outline" disabled={!canEdit || busy || reason.length < 5}>Record movement →</button>
          </form>}
        </section>{canEdit && product && <section className="operations-panel operations-panel--wide"><h2>Product record</h2>
          <p>Replace all concept copy with final reviewed information before publication.</p>
          <form onSubmit={saveProduct}><div className="operations-fields">
            {[
              ["name", "Name"], ["subtitle", "Subtitle"], ["description", "Description"],
              ["product_type", "Product type"], ["form_factor", "Form factor"],
              ["unit_size", "Unit size"], ["price_cents", "Price in cents"],
              ["ingredients", "Ingredients, comma separated"],
              ["usage_instructions", "Usage instructions"], ["warnings", "Warnings"],
              ["storage_instructions", "Storage instructions"], ["packaging", "Packaging"],
              ["shipping_details", "Shipping details"],
            ].map(([key, label]) => <div className="field" key={key}><label htmlFor={`draft-${key}`}>{label}</label>
              {key === "description" || key.endsWith("instructions") || key === "warnings" || key === "packaging" || key === "shipping_details"
                ? <textarea id={`draft-${key}`} required value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
                : <input id={`draft-${key}`} required type={key === "price_cents" ? "number" : "text"}
                    min={key === "price_cents" ? 1 : undefined} value={draft[key] ?? ""}
                    onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />}</div>)}
          </div><button className="button button--gold" disabled={busy || reason.length < 5 || !draft.name}>Save product record →</button></form>
        </section>}
        <section className="operations-panel"><h2>Evidence records</h2>
          {!evidence ? <p>Select a product to see evidence.</p> : <>
            <h3>Formulations</h3><ul>{evidence.formulations.map((row) => <li key={row.id}>{row.version_label} · {row.status}<br />{row.safety_document_reference}
              {canEdit && row.status === "draft" && <button className="text-link" disabled={busy || reason.length < 5} onClick={() => review("formulations", row.id)}>Approve</button>}</li>)}</ul>
            <h3>Claims</h3><ul>{evidence.claims.map((row) => <li key={row.id}>{row.claim_text} · {row.status}<br />{row.source_reference}
              {canEdit && row.status === "draft" && <button className="text-link" disabled={busy || reason.length < 5 || reference.length < 8} onClick={() => review("claims", row.id)}>Approve</button>}</li>)}</ul>
            <h3>Impact factors</h3><ul>{evidence.impacts.map((row) => <li key={row.id}>{row.metric_type} · {row.status}<br />{row.source_reference}
              {canEdit && row.status === "draft" && <button className="text-link" disabled={busy || reason.length < 5 || reference.length < 8} onClick={() => review("impact", row.id)}>Approve</button>}</li>)}</ul>
            <p className="muted">Approvals require a reason and, for claims and impact, an evidence reference in the release form.</p>
          </>}
          {canEdit && product && <><form onSubmit={addFormulation}><h3>New formulation draft</h3>
            <div className="field"><label htmlFor="formulation-label">Version</label><input id="formulation-label" required value={formulationLabel} onChange={(event) => setFormulationLabel(event.target.value)} /></div>
            <div className="field"><label htmlFor="formulation-safety">Safety document reference</label><input id="formulation-safety" required value={formulationSafety} onChange={(event) => setFormulationSafety(event.target.value)} /></div>
            <button className="button button--outline" disabled={busy || reason.length < 5}>Create draft</button></form>
            <form onSubmit={addClaim}><h3>New claim draft</h3>
              <div className="field"><label htmlFor="claim-text">Claim</label><textarea id="claim-text" required minLength={5} value={claimText} onChange={(event) => setClaimText(event.target.value)} /></div>
              <div className="field"><label htmlFor="claim-source">Source reference</label><input id="claim-source" required minLength={5} value={claimSource} onChange={(event) => setClaimSource(event.target.value)} /></div>
              <button className="button button--outline" disabled={busy || reason.length < 5}>Create draft</button></form>
            <form onSubmit={addImpact}><h3>New impact factor draft</h3>
              {[
                ["impact-metric", "Metric", impactMetric, setImpactMetric],
                ["impact-value", "Factor value per product unit", impactValue, setImpactValue],
                ["impact-unit", "Unit", impactUnit, setImpactUnit],
                ["impact-baseline", "Baseline", impactBaseline, setImpactBaseline],
                ["impact-comparison", "Comparison scenario", impactComparison, setImpactComparison],
                ["impact-method", "Methodology version", impactMethod, setImpactMethod],
                ["impact-qualification", "Qualification", impactQualification, setImpactQualification],
              ].map(([id, label, value, setter]) => <div className="field" key={id as string}><label htmlFor={id as string}>{label as string}</label>
                <input id={id as string} required value={value as string} onChange={(event) => (setter as (value: string) => void)(event.target.value)} /></div>)}
              <button className="button button--outline" disabled={busy || reference.length < 8}>Create draft</button></form></>}
        </section><section className="operations-panel"><h2>Orders</h2>
          {orders.length === 0 ? <p>No orders yet.</p> : <ul className="account-list">{orders.map((order) => <li key={order.id}>
            <strong>{order.id.slice(0, 8)}</strong> · {order.payment_status} · {order.fulfillment_status}
            <p>{order.items.map((item) => `${item.quantity} × ${item.name}`).join(", ")}</p>
            <p>{money(order.total_cents ?? 0)} · {new Date(order.created_at).toLocaleDateString()}</p>
            {canEdit && order.payment_status === "paid" && order.fulfillment_status === "unfulfilled" &&
              <button className="button button--outline" disabled={busy || reason.length < 5} onClick={() => fulfill(order.id)}>Mark shipped</button>}
            {canEdit && order.status === "paid_stock_hold" && <button className="button button--outline" disabled={busy} onClick={() => allocate(order.id)}>Allocate stock</button>}
            {canEdit && ["paid", "partially_refunded"].includes(order.payment_status) && <div className="field">
              <label htmlFor={`refund-${order.id}`}>Refund amount in cents</label>
              <input id={`refund-${order.id}`} type="number" min={1} value={refundAmount} onChange={(event) => setRefundAmount(event.target.value)} />
              <button className="button button--outline" disabled={busy || reason.length < 5 || Number(refundAmount) <= 0} onClick={() => refund(order.id)}>Request refund</button>
            </div>}
          </li>)}</ul>}
        </section>{isAdmin && <section className="operations-panel"><h2>Privacy requests</h2>
          <p>Close active orders and subscriptions before redaction. Complete provider follow-up with an evidence reference.</p>
          {privacyRequests.length === 0 ? <p>No pending requests.</p> : <ul className="account-list">{privacyRequests.map((item) => <li key={item.id}>
            <strong>{item.type}</strong> · {item.status}<p>Account {item.customer_id.slice(0, 8)} · {new Date(item.created_at).toLocaleDateString()}</p>
            {item.provider_customer_id && <p>Provider customer: {item.provider_customer_id}</p>}
            <button className="button button--outline" disabled={busy || reason.length < 5 || reference.length < 8}
              onClick={() => processPrivacy(item)}>{item.status === "pending" ? "Redact local data" : "Mark provider follow-up complete"}</button>
          </li>)}</ul>}
        </section>}{isAdmin && <section className="operations-panel"><h2>Staff access</h2>
          <p>Change the role of an existing account. The account must sign in again afterward.</p>
          <form onSubmit={changeRole}><div className="field"><label htmlFor="staff-email">Account email</label>
            <input id="staff-email" type="email" required value={staffEmail} onChange={(event) => setStaffEmail(event.target.value)} /></div>
            <div className="field"><label htmlFor="staff-role">Role</label><select id="staff-role" value={staffRole} onChange={(event) => setStaffRole(event.target.value)}>
              <option value="customer">Customer</option><option value="support">Support</option>
              <option value="operations">Operations</option><option value="admin">Administrator</option></select></div>
            <button className="button button--outline" disabled={busy || reason.length < 5}>Update role →</button>
          </form></section>}</div>
      </>}
  </main>;
}
