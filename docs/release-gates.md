# Product and release gates

| Gate | Current state | Evidence required to pass |
| --- | --- | --- |
| Formulation and safety | Open | Final specifications, compatibility, stability, safety and batch documents, approved usage and warnings. |
| Environmental claims | Open | Product-specific method, baseline, system boundary, source records, reviewer and review date. |
| Manufacturing | Open | Supplier qualification, quality controls, traceability, lead time and capacity. |
| Commerce | Open | Product approvals, tax and shipping configuration, refund policy, privacy and terms review, customer support procedure. |
| Operations | Open | Backup restore drill, monitoring and alerts, incident procedure, webhook replay tests. |
| Privacy | Open | Legal-reviewed notice, published contact channel, scheduled retention job and tested deletion workflow. |

No seed product is represented as ready for sale. Marketing copy must mark unapproved products as concepts and avoid quantitative environmental, health, aquatic safety, and therapeutic claims without reviewed evidence.

The software records eight per-product approvals: formulation, safety, label, claims, shipping, tax, fulfillment, and support. Publication and checkout revalidate approved formulation evidence, final non-placeholder copy, positive USD price, available stock, and all eight evidence references. Approved impact factors are displayed only within their validity dates.

For production, global checkout also requires `COMMERCE_ENABLED=true`, `LAUNCH_APPROVAL_REFERENCE`, `SUPPORT_EMAIL`, HTTPS terms/refund links and web URL, Stripe credentials and shipping rate, and SMTP/operations email settings. These values represent completed external reviews; setting them without evidence does not satisfy the product, legal or operational gate. The original source POC/PDD remains the acceptance baseline.
