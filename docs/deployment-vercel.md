# Deploy the concept site on Vercel

The public web app runs on Vercel. The existing FastAPI app and PostgreSQL database must be hosted separately: catalog pages fetch API data on the server, and browser actions use the web app's `/api/v1` proxy. Keep `COMMERCE_ENABLED=false`; this deployment presents concepts and does not authorize sales.

## Hosting plan and cost

Vercel's free Hobby plan is restricted to personal, noncommercial use. If this is the public site for a business or future product brand, use Vercel Pro even while checkout is disabled. As of September 2026, its platform fee is $20/month for one deploying seat, with additional usage billed according to the plan. Render's smallest paid API web service is $7/month and its smallest paid PostgreSQL instance is $6/month, before database storage, a mail worker/provider, and any usage charges. This makes the basic durable web + API + database setup about **$33/month** before extras. Check each provider's checkout summary before accepting a paid plan.

## 1. Deploy the database and API

Render is a straightforward host for the existing API container and a managed PostgreSQL database. Choose a paid PostgreSQL plan with backups for a durable public site. Render's free PostgreSQL plan expires after 30 days and is suitable only for a temporary demonstration.

1. In Render, create a PostgreSQL database and a Docker **Web Service** from this GitHub repository. Put both in the same region so the API can use the database's **internal** connection URL.
2. Set the web service's **Root Directory** to `apps/api`, **Dockerfile Path** to `Dockerfile`, and **Docker Build Context** to `.`. The container accepts Render's `PORT` automatically.
3. Set the **Pre-Deploy Command** to `alembic upgrade head && python -m app.seed`. This requires a paid web service. The seed is idempotent and adds the four concept products and recommendation rules after migrations.
4. Set the **Health Check Path** to `/health/ready`.
5. Add these Render environment variables. Enter the database URL and any mail credentials through Render's secret settings, never in Git:

   | Name | Value |
   | --- | --- |
   | `DATABASE_URL` | The Render PostgreSQL **internal** URL; the API accepts `postgresql://` and `postgres://` URLs. |
   | `ENVIRONMENT` | `production` |
   | `WEB_ORIGIN` | `https://www.brew67potions.us` |
   | `PUBLIC_WEB_URL` | `https://www.brew67potions.us` |
   | `SESSION_COOKIE_SECURE` | `true` |
   | `COMMERCE_ENABLED` | `false` |
   | `LOCAL_TEST_COMMERCE` | `false` |
   | `SUBSCRIPTIONS_ENABLED` | `false` |

6. Deploy and verify `https://<your-api-host>/health/ready` returns `{"status":"ok"}` and `https://<your-api-host>/api/v1/products` returns the seeded catalog. Record the actual API origin for the Vercel configuration below.

Account verification and recovery require an SMTP provider plus the one-minute `python -m app.jobs` worker. Interest and analytics retention require a daily `python -m app.retention` job. Configure these jobs and `SMTP_HOST`, `SMTP_PORT`, `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM` before presenting account signup as operational. The local Mailpit address is not a production SMTP provider. Do not publish the site as fully operational until the privacy notice, support address, and backup restore have been reviewed.

## 2. Deploy the web app on Vercel

1. In Vercel, choose **Add New → Project**, import `its-arnavtech/Tri-Realm-Eco-Apothecary`, and deploy the `main` branch after the deployment PR is merged.
2. Set **Framework Preset** to **Next.js** and **Root Directory** to `apps/web`.
3. Leave the build, install, and output settings at their detected defaults. Use Node.js 24. Do not select a static site preset: these pages render API data on the server.
4. Set these Vercel environment variables for **Production** before the first deployment:

   | Name | Value |
   | --- | --- |
   | `API_INTERNAL_URL` | The public HTTPS origin of the FastAPI service, without a trailing slash. |
   | `ENABLE_EXPERIMENTAL_COREPACK` | `1` (uses the pinned `pnpm@11.19.0`). |

   `NEXT_PUBLIC_API_BASE` defaults to `/api/v1`; leave it unset. Set `SUPPORT_EMAIL` only to a verified support mailbox. Add the same `API_INTERNAL_URL` to Preview if preview deployments should access the production API. Preview writes then reach production data, so use a separate preview API/database if testing mutations.

5. Deploy. Check the generated `*.vercel.app` URL: `/`, `/catalog`, `/realms`, and `/configure` should load. A successful build alone does not prove the API is reachable.

## 3. Connect `brew67potions.us`

Keep the domain registered with its current registrar and use an **external domain** in Vercel. A transfer is unnecessary. The current DNS points to Porkbun's parked page; the domain uses Porkbun nameservers.

1. In the Vercel project, open **Settings → Domains**. Add both `www.brew67potions.us` and `brew67potions.us`. Set `www.brew67potions.us` as the primary domain and redirect the apex domain to it.
2. Copy the **exact** DNS records Vercel displays for this project. In Porkbun, open **Domain Management → Details → DNS Records** for `brew67potions.us`. Replace the parked apex `A` records with Vercel's required apex record, and replace the parked `www` CNAME with Vercel's required CNAME. Remove conflicting parked records for those same hosts. Preserve MX, TXT, and unrelated records.
3. Wait for Vercel to verify both domains and issue HTTPS certificates. Use Vercel's domain page to diagnose any remaining DNS mismatch. Verify that `https://brew67potions.us` redirects to `https://www.brew67potions.us` and that the catalog loads over HTTPS.

## 4. Final checks

- Open the homepage and catalog on the custom domain, then exercise the configurator and simulated cart. Confirm the browser's `/api/v1/*` calls succeed on the same domain.
- Confirm a concept product cannot enter real checkout and `COMMERCE_ENABLED=false` remains set on the API.
- Confirm API readiness, error logs, database backups, and a tested restore. Configure account email delivery and data retention jobs before accepting signups.
- After changing `API_INTERNAL_URL`, redeploy the Vercel project so its rewrite configuration uses the new API origin.

References: [Vercel Git deployments](https://vercel.com/docs/git), [Vercel monorepo root directories](https://vercel.com/docs/monorepos), [Vercel Corepack](https://vercel.com/docs/builds/configure-a-build), [Vercel custom domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain), [Vercel Hobby restrictions](https://vercel.com/docs/plans/hobby), [Vercel Pro pricing](https://vercel.com/docs/plans/pro-plan), [Porkbun DNS records](https://kb.porkbun.com/article/68-how-to-edit-dns-records), [Render pricing](https://render.com/pricing), [Render Docker services](https://render.com/docs/docker), [Render pre-deploy commands](https://render.com/docs/deploys), and [Render free tier limits](https://render.com/docs/free).
