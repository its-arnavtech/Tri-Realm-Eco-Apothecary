# Risk register

| Risk | Status | Control or exit evidence |
| --- | --- | --- |
| Product safety and formulation | Open | Final specifications, testing, approved safety documents and instructions before sale. |
| Environmental and performance claims | Open | Evidence records and reviewer approval before public display; API excludes draft claims. |
| Manufacturing and traceability | Open | Qualified supplier, batch and quality records, capacity and lead-time review. |
| Customer comprehension | In validation | Test concept wording, configurator explanations and usage directions with target users. |
| Inventory mismatch | Software control implemented; operational proof open | Transactional reservations, movement ledger, expiry reconciliation and stock holds. Exercise concurrent checkout and physical count reconciliation before enablement. |
| Payment and refund reliability | Software control implemented; provider proof open | Hosted checkout, signed idempotent webhooks, refund records and replay tests. Run live sandbox webhooks and refund drills before enablement. |
| Privacy and consent | Software workflow implemented; legal review open | Consent metadata, limited analytics, retention, export and audited redaction. Review notice, retention policy and provider deletion obligations. |
| Platform complexity | Controlled for POC | Deterministic rules, narrow API boundary, no real checkout. |
| Brand trust | Controlled for POC | Concept status and illustrative pricing shown prominently; no unsupported impact number. |
