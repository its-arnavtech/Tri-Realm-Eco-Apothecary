# Requirements traceability

| Requirement | Implementation target |
| --- | --- |
| FR-01–03 | Biome landing, filterable catalog, product detail pages and `/api/v1/biomes`, `/api/v1/products`. |
| FR-04–05 | Configurator UI and versioned recommendation service. |
| FR-06–07 | Server-priced simulated cart and consented intent signup. |
| FR-08–10 | `/checkout/session`, transactional inventory reservations, orders, Stripe hosted Checkout, signed event ledger, reconciliation worker, refunds and invoice based subscription orders. Disabled by default. |
| FR-11 | Draft/review impact factors with baseline, comparison, method, source, validity dates, reviewer and public approved-only API. |
| FR-12 | Registration, verification, recovery, login, preferences, order history, subscriptions, privacy export and deletion request UI/API. |
| FR-13–14 | Staff dashboard, role control, release and evidence review, inventory, fulfillment, refund, privacy workflow and audit records. |

The source PDD's production acceptance criteria remain gates even when the corresponding software path exists. An implemented endpoint alone does not imply permission to launch a product or claim.

The release-gated code is in `codex/commerce-operations`. Product validation, independent claim/legal review, manufacturing, real provider credentials, backup restore drills and production observability require real-world evidence before `COMMERCE_ENABLED` may be enabled.
