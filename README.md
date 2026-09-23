# brew67potions

A biome-led POC for sustainable product concepts, with a production commerce architecture. Forest, Ocean and Mountain products are **concepts**, not products currently approved for sale. The POC lets visitors explore them, receive an explainable Brew No. 67 recommendation, assemble a simulated cart and optionally register interest with consent.

The source requirements are in `brew67potions_POC_PDD.docx` and `.pdf`. Implementation choices and release gates are recorded in `docs/`.

## Local development

1. Copy `.env.example` to `.env` and set a strong `ADMIN_API_KEY` if using admin routes.
2. Start PostgreSQL: `docker compose up -d db`.
3. Install API dependencies: `python -m pip install -e "apps/api[dev]"`.
4. Apply schema: `cd apps/api && alembic upgrade head`.
5. Seed concept catalog: `python -m app.seed` from `apps/api`.
6. Start API: `cd apps/api && uvicorn app.main:app --reload`.
7. Install and start web: `cd apps/web && pnpm install && pnpm dev`.

Visit `http://localhost:3000`. API docs are at `http://localhost:8000/docs` in local development.

## Checks

- API: `cd apps/api && pytest` and `ruff check .`.
- Web: `cd apps/web && pnpm lint && pnpm typecheck && pnpm build`.

The POC does not collect payment data or process real orders. Production commerce is gated by product, legal, tax, fulfillment, and operations approvals described in `docs/release-gates.md`.

Schedule `python -m app.retention` daily in any environment that captures interest. The POC retains interest signups for at most 90 days and analytics events for at most 30 days. A public deployment additionally needs a reviewed privacy notice and a published contact channel.
