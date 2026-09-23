# Quality evidence and remaining validation

## Local mobile audit, 2026-09-23

Lighthouse 13.5.0 ran against the production Next.js build with the seeded local API. Scores are single-run lab measurements under Lighthouse's default mobile profile, so repeat them in staging on realistic mobile and desktop networks before launch.

| Route | Performance | Accessibility |
| --- | ---: | ---: |
| `/` | 93 | 100 |
| `/catalog` | 97 | 100 |
| `/catalog/tri-realm-catalyst` | 94 | 100 |
| `/configure` | 97 | 100 |
| `/cart` | 92 | 100 |
| `/account` (signed out) | 97 | 100 |

The account page initially scored 86 because the footer moved while session state loaded. Reserving stable page space removed the measured layout shift. Contrast, heading sequence, and accessible-link labels were corrected on catalog and product pages. Total raw built JavaScript and CSS in `.next/static` was about 678 KB, below the PDD's 1.5 MB bundle budget; this is not a per-route transfer measurement.

The Windows Lighthouse process returned a temporary Chrome profile cleanup error after writing each valid JSON report. The scores above were read from those reports. The generated reports live under the ignored `apps/web/.next/` directory and are reproducible with `pnpm dlx lighthouse http://localhost:3000/<route> --chrome-flags="--headless" --output=json` while the production web build and seeded API are running.

## Automated checks

The API suite covers catalog filtering, recommendations, consent and analytics validation, role and CSRF enforcement, production release gates, checkout reservations, signed and replayed provider events, refunds, subscription invoices, privacy redaction, impact estimates, and the shared rate limiter. CI also checks lint, typecheck, builds, PostgreSQL migrations, container image builds, and pinned dependency advisories. The local `pnpm audit --audit-level high` and `pip-audit --requirement apps/api/requirements.lock --disable-pip --no-deps --strict` scans reported no known vulnerabilities on 2026-09-23.

## Release validation still required

- A manual WCAG 2.1 AA review with keyboard and assistive technology, including authenticated staff and checkout handoff flows.
- A realistic staging load test, database query review, and repeat Lighthouse runs on representative devices and networks.
- Stripe test-mode paid, delayed, expired, refund, subscription, and replay drills against a real webhook endpoint.
- A PostgreSQL backup restore drill with recorded recovery time and point objectives, plus monitoring alert routing.
- Product safety, manufacturing, legal, tax, privacy, and claim-evidence signoffs described in [release-gates.md](release-gates.md).

The local Docker daemon was unavailable for a running Compose topology. GitHub CI builds both images and exercises the PostgreSQL migration path; a live staging deployment and restore drill require a destination and credentials.
