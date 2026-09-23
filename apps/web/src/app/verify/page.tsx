"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "@/lib/client";

export default function VerifyPage() {
  const [status, setStatus] = useState("Verifying your email…");
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) { queueMicrotask(() => setStatus("Verification link is missing a token.")); return; }
    void request("/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) })
      .then(() => setStatus("Your email is verified. You can return to your account."))
      .catch(() => setStatus("This verification link is invalid or expired."));
  }, []);
  return <main id="main" className="shell account-page"><p className="section-number">ACCOUNT / VERIFY</p>
    <h1>Email <em>verification.</em></h1><p role="status">{status}</p>
    <Link className="button button--outline" href="/account">Go to account →</Link></main>;
}
