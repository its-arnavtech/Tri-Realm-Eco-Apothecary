export const dynamic = "force-dynamic";

export default function PrivacyPage() {
  const support = process.env.SUPPORT_EMAIL;
  const terms = process.env.TERMS_URL;
  const refunds = process.env.REFUND_POLICY_URL;
  return <main id="main">
    <section className="page-hero"><div className="shell">
      <p className="section-number">PRIVACY & POLICIES</p>
      <h1>Privacy & <em>consent.</em></h1>
      <p>This implementation notice describes the data used by the current experience. A legal review and a published support channel are required before a commercial launch.</p>
    </div></section>
    <section className="content-section shell two-column"><div>
      <h2>Interest submissions</h2>
      <p>When you register interest, we store your email, selected interest, contact and optional marketing choices, and the consent version and time. Interest submissions are scheduled for deletion after 90 days unless an earlier request applies.</p>
      <h2>Accounts and orders</h2>
      <p>If you create an account, we store your email, a protected password hash, verification status, preferences and session records. Approved purchases create order, fulfillment, inventory and payment reference records. Card details are entered only on the payment provider’s hosted page.</p>
      <h2>Requests and withdrawal</h2>
      <p>{support ? <>Contact <a href={`mailto:${support}`}><u>{support}</u></a> for access, deletion, correction or consent withdrawal requests.</> : "A public request channel has not been configured. Commercial launch remains disabled until it is published."}</p>
    </div><div>
      <h2>Experience analytics</h2>
      <p>We measure page visits and product interactions with random session identifiers and restricted event fields. Event payloads exclude email and payment information. Analytics events are scheduled for deletion after 30 days.</p>
      <h2>Messages and payments</h2>
      <p>We send account verification, recovery and order messages from an operational email outbox. Payments and subscriptions use a hosted provider; the application stores provider references and verified event records for reconciliation.</p>
      <h2>Purchase policies</h2>
      <p>{terms ? <a href={terms}><u>Terms of sale</u></a> : "Terms of sale pending approval"} · {refunds ? <a href={refunds}><u>Refund policy</u></a> : "Refund policy pending approval"}</p>
    </div></section>
  </main>;
}
