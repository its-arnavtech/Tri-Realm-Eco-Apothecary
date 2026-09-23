import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy", description: "How this informational website handles visitor information." };

export default function PrivacyPage() {
  return <main id="main"><section className="page-hero"><div className="shell"><p className="section-number">SITE INFORMATION</p><h1>A simple site.<br /><em>A clear notice.</em></h1><p>This is an informational, static website. It does not offer accounts, checkout, forms, or an email list.</p></div></section>
    <section className="content-section shell privacy-content"><h2>What this site collects</h2><p>The website itself does not ask you to submit personal information, set its own tracking cookies, or send behavior analytics to an application database.</p><h2>Hosting</h2><p>Like most websites, our hosting provider may process basic request information, such as an IP address and browser details, to deliver and protect the site. See the hosting provider’s privacy information for details of that processing.</p><h2>External links</h2><p>If a future version links to another service, that service’s own privacy practices will apply when you visit it.</p><p className="note-panel">This page describes the current static concept website. It will be updated before any new data collection feature is introduced.</p></section>
  </main>;
}
