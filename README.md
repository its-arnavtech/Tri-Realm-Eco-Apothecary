# brew67potions

A biome-led product experience and release-gated commerce platform. Forest, Ocean and Mountain seed products are **concepts**, not products currently approved for sale. Visitors can explore them, receive an explainable Brew No. 67 recommendation, assemble a simulated cart and optionally register interest with consent. The production paths for accounts, orders, inventory, payments, subscriptions, operations, and evidence review remain disabled for sales until the release gates pass.

The source requirements are in `brew67potions_POC_PDD.docx` and `.pdf`. Implementation choices and release gates are recorded in `docs/`.
Local performance and accessibility measurements, plus remaining launch validation, are recorded in [quality evidence](docs/quality-evidence.md).
For public hosting, see [Vercel deployment and domain setup](docs/deployment-vercel.md).

## Local development

1. Copy `.env.example` to `.env`. Keep `COMMERCE_ENABLED=false` until all release gates pass.
2. Start PostgreSQL: `docker compose up -d db`.
3. Install API dependencies: `python -m pip install -e "apps/api[dev]"`.
4. Apply schema: `cd apps/api && alembic upgrade head`.
5. Seed concept catalog: `python -m app.seed` from `apps/api`.
6. Start API: `cd apps/api && uvicorn app.main:app --reload`.
7. Install and start web: `cd apps/web && pnpm install && pnpm dev`.

Visit `http://localhost:3000`. API docs are at `http://localhost:8000/docs` in local development.

To run the full local container topology on Windows PowerShell, use `Copy-Item .env.example .env` once, then `docker compose -f compose.full.yaml up --build -d`. It includes PostgreSQL, migrations, the API, web app, worker, and a local Mailpit inbox at `http://localhost:8026`. The Docker daemon must be running. Set `MAILPIT_UI_PORT` in `.env` if that host port is occupied. View status with `docker compose -f compose.full.yaml ps`; stop with `docker compose -f compose.full.yaml down` (the database volume is retained). The local Compose database password is for development only.

Create the first administrator from an interactive API terminal with `python -m app.bootstrap_admin` after migrations. Subsequent staff roles are assigned through the audited admin API or operations dashboard. Registration and password recovery require the email worker: run `python -m app.jobs` every minute, with SMTP settings configured. Run `python -m app.retention` daily.

## Checks

- API: `cd apps/api && pytest` and `ruff check .`.
- Web: `cd apps/web && pnpm lint && pnpm typecheck && pnpm build`.

The concept experience does not collect payment data or process real orders. Real checkout uses hosted Stripe pages only after global and product gates pass. See [architecture](docs/architecture.md), [release gates](docs/release-gates.md), and the [commerce runbook](docs/commerce-runbook.md) before enabling it.

Interest signups are scheduled for deletion after 90 days and analytics events after 30 days. A public deployment additionally needs a reviewed privacy notice, terms and refund policies, verified support channel, provider configuration, production monitoring, and a tested backup restore.
