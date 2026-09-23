"use client";

import Link from "next/link";
import { useState } from "react";
import { request } from "@/lib/client";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const token = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("token");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      if (token) {
        await request("/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password }) });
        setMessage("Password updated. Sign in with your new password.");
      } else {
        await request("/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) });
        setMessage("If an account exists for this address, a recovery link will be sent.");
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Request failed."); }
    finally { setBusy(false); }
  }
  return <main id="main" className="shell account-page"><p className="section-number">ACCOUNT / RECOVERY</p>
    <h1>Reset your <em>password.</em></h1>
    {message && <p className="success" role="status">{message}</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    <form className="account-panel account-auth" onSubmit={submit}><div className="field">
      <label htmlFor="recovery-input">{token ? "New password" : "Email address"}</label>
      <input id="recovery-input" type={token ? "password" : "email"} required
        autoComplete={token ? "new-password" : "email"} minLength={token ? 12 : undefined}
        value={token ? password : email}
        onChange={(event) => token ? setPassword(event.target.value) : setEmail(event.target.value)} />
    </div><button className="button button--gold" disabled={busy}>{busy ? "Please wait…" : "Continue →"}</button></form>
    <p><Link className="text-link" href="/account">Back to account →</Link></p>
  </main>;
}
