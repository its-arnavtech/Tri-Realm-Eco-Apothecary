# Commerce and operations runbook

## Deployment boundary

`compose.full.yaml` is a local integration stack. A production deployment needs a managed PostgreSQL database with encrypted backups, HTTPS at the web edge, private API connectivity, a secret manager, an SMTP service, a one-minute job scheduler, monitoring, and an operator on call. Build the API and web images from their Dockerfiles. Build the web image with `API_INTERNAL_URL` set to the private API origin because Next.js rewrites are compiled into its build. Run Alembic migrations before rolling API instances. Roll back the application version if a migration or health probe fails; treat data migrations as forward-only and restore from a verified backup for destructive recovery.

Local Stripe test-mode checkout requires `COMMERCE_ENABLED=true`, `LOCAL_TEST_COMMERCE=true`, a `sk_test_` API key, webhook signing secret, and test shipping rate. Production ignores `LOCAL_TEST_COMMERCE` and requires the full launch configuration below.

The web process exposes port 3000. The API exposes port 8000 with `/health/live` and `/health/ready`. The worker runs `python -m app.jobs` every minute. Run `python -m app.retention` daily. Alert on nonzero job exits, failed outbox rows, old `pending_payment` orders, `paid_stock_hold` orders, webhook 4xx/5xx spikes, low stock, database errors, and API readiness failure.

The API emits JSON request records with route template, status, latency, and a response `X-Request-ID`. Its container disables Uvicorn's raw URL access log so query strings are not copied into request telemetry. `/api/v1/admin/metrics` provides a seven-day funnel and current stock/email/payment snapshot to authenticated staff. Collect these logs and poll the metrics and readiness endpoints from the chosen monitoring service; external alert routing remains a deployment prerequisite.

## First operator and access

Apply migrations, then run `python -m app.bootstrap_admin` in a private API terminal. It prompts for the first administrator email and a password without putting the password in process arguments. The account email is treated as verified because the operator is provisioning it directly. Staff sign in at `/account`; the dashboard is at `/operations`. Only administrators can grant roles or process deletion requests. Operations staff can review product evidence, stock, orders and refunds. Support staff have read-only dashboard access. Role changes revoke the affected account's sessions and produce an audit event. The POC `ADMIN_API_KEY` path is unavailable in production.

## Product publication

1. Create final product copy, ingredients, size, usage, warnings, packaging and shipping information. The API rejects placeholder concept language when a product is published.
2. Create a formulation version with a safety document reference and approve it after actual review. Record draft claims and impact factors; public endpoints expose only approved records. Impact factors require a baseline, comparison, unit, methodology version, source and qualification.
3. Create inventory with a stable SKU and record physical quantities through the movement endpoint. Review each release gate: `formulation`, `safety`, `label`, `claims`, `shipping`, `tax`, `fulfillment`, and `support`. Each approval needs an evidence reference and reviewer.
4. Publish the product from operations. The API rechecks all product gates. Seed products remain concepts until this work is complete.
5. Obtain legal, safety, manufacturing, tax, privacy, shipping, refund, customer support, backup, and monitoring signoffs outside the software. Record a nonempty `LAUNCH_APPROVAL_REFERENCE`. Set `SUPPORT_EMAIL`, HTTPS `TERMS_URL`, HTTPS `REFUND_POLICY_URL`, HTTPS `PUBLIC_WEB_URL`, Stripe keys and shipping rate, SMTP with STARTTLS, and `OPERATIONS_EMAIL`. Only then set `COMMERCE_ENABLED=true` in a nonlocal environment. Keep `SUBSCRIPTIONS_ENABLED=false` until recurring price, stock planning, shipping and renewal handling have been verified in Stripe test mode.

Do not use invented evidence references to pass a gate. The API records approvals; it cannot determine whether a product is safe or a claim is legally substantiated.

## Payment and inventory

Register the Stripe webhook at `/api/v1/webhooks/stripe` on the API origin. Subscribe to `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `refund.created`, and `refund.updated`. Configure the endpoint signing secret as `STRIPE_WEBHOOK_SECRET`.

Checkout snapshots server prices and approved formulation versions, locks inventory rows and reserves units. Checkout sessions expire after about 31 minutes. A signed paid event turns reservations into inventory movements and an order. Duplicate event IDs are recorded once. The job checks Stripe session state before releasing expired reservations, so it never frees stock based solely on a local clock. A customer who returns from Stripe should check `/account`; the redirect is not proof of payment.

Each paid subscription invoice creates one refill order. If stock or release approval is unavailable, it becomes `paid_stock_hold` with fulfillment `hold` and sends an operations message. Replenish inventory, recheck gates, and use the allocation action before shipping. Refunds are initiated by operations, use a provider idempotency key, and update payment status from the provider result and refund events. Refunds do not automatically restock physical goods; record a separate inventory adjustment after inspection.

Before launch, use Stripe test mode to exercise paid, delayed, failed, expired, replayed and out-of-order events; partial and full refunds; subscription creation, renewal, cancellation, and stock hold. Reconcile order totals and inventory movement sums against Stripe and a physical count. The automated tests cover the local state transitions; they do not replace a provider sandbox drill.

## Privacy and retention

An account can export its data and submit a deletion request with password confirmation. An administrator reviews it in operations. The API blocks redaction while paid orders are open, subscriptions are active, or refunds are pending. Redaction removes interest submissions and recovery tokens, revokes sessions, replaces account identifiers, and clears completed order shipping snapshots while retaining minimal financial and audit records. If a Stripe customer reference exists, the request remains `external_pending` until an operator completes the provider follow-up and records evidence. Review statutory retention and Stripe deletion obligations with counsel before processing real requests.

The daily retention job removes interest submissions after 90 days and analytics events after 30 days. The minute worker removes expired account tokens and old completed outbox rows. Access to database backups and audit records must be limited to operations roles.

## Backup and incident checks

For a self-managed PostgreSQL deployment, schedule encrypted `pg_dump` backups outside the application and retain them according to the approved retention policy. Restore a backup to an isolated database at least once before launch and periodically afterward, run `alembic check`, compare order and inventory counts, and record the drill. A managed database may provide point-in-time restore instead; verify it with the same checks.

On a checkout or webhook incident, leave `COMMERCE_ENABLED=false` while investigating. Do not mark orders paid from a browser redirect. Replay signed provider events after fixing the fault; the event ledger prevents repeat stock movements. If mail delivery fails, inspect `email_outbox` status and SMTP configuration; retry failed rows only after confirming no message was delivered. Escalate any paid stock hold before accepting further subscription renewals.
