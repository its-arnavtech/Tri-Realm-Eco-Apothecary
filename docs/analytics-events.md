# POC analytics contract

The POC emits schema version `1` events through `POST /api/v1/events`. Each event contains an allowed event name, a random anonymous identifier, a random session identifier, an occurrence time assigned by the API, and an allowlisted string context. Every web event currently carries `experiment_version=narrative-v1`.

| Event | Trigger | Context |
| --- | --- | --- |
| `page_view` | Page opened | `page` |
| `biome_viewed` | Realm page opened | `page`, `biome` |
| `product_viewed` | Product detail opened | `page`, `product_slug` |
| `configurator_started` | Recommendation form submitted | `page` |
| `configurator_step_completed` | Valid recommendation response | `page`, `step` |
| `recommendation_generated` | Recommendation response | `page`, `product_slug` or `none` |
| `add_to_cart` | Server confirms cart add | `page` when applicable, `product_slug` |
| `intent_submitted` | Server confirms consented signup | `page` |

The API rejects context keys outside `page`, `biome`, `product_slug`, `step`, `experiment_version`, and `traffic_source`; values are restricted to simple identifiers. Email and free-text fields are never sent to analytics. The in-process rate limiter is suitable only for a single POC process and must be replaced with a shared limiter before scaled deployment.

This code does not assert a causal lift. An experiment report must record audience, variant assignment, traffic source, sample size, and uncertainty. A baseline landing page and user comprehension study remain validation activities.
