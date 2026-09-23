export default function PrivacyPage() {
  return <main id="main">
    <section className="page-hero"><div className="shell">
      <p className="section-number">PRIVACY / POC</p>
      <h1>Privacy & <em>consent.</em></h1>
      <p>This notice describes data collected by the proof of concept. It requires legal review before a public launch.</p>
    </div></section>
    <section className="content-section shell two-column">
      <div>
        <h2>Interest submissions</h2>
        <p>If you register interest, we store your email address, selected interest, contact and marketing choices, and the consent policy version and time. Marketing is optional. POC signups are retained for at most 90 days unless an earlier deletion request applies.</p>
        <h2>How to make a request</h2>
        <p>Before public deployment, the operator must publish a contact address and a working process for access, deletion and withdrawal requests. This local proof of concept has no public support channel.</p>
      </div>
      <div>
        <h2>Experience analytics</h2>
        <p>We measure page visits and product interactions with random session identifiers and a restricted event schema. Event payloads do not include email or payment information.</p>
        <h2>Payments</h2>
        <p>The POC does not accept payment or create orders.</p>
      </div>
    </section>
  </main>;
}
