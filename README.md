# brew67potions

A static, informational website inspired by Forest, Ocean, and Mountain. It presents four early brew concepts as ideas in development. There are no accounts, forms, payments, API calls, or database requirements in the public site.

## Run locally

```powershell
cd apps/web
pnpm install
pnpm dev
```

Open `http://localhost:3000`. To produce the deployable static files, run `pnpm build` from `apps/web`; the result is in `apps/web/out`.

## Edit the site

- Realm and concept copy: `apps/web/src/lib/content.ts`
- Pages: `apps/web/src/app`
- Visual styling: `apps/web/src/app/globals.css`
- Hero image: `apps/web/public/images/tri-realm-hero.webp`

The hero image is generated concept artwork. It depicts no actual product. All concept pages state that the ideas are not available for use or sale.

## Deploy

Import this repository into Vercel with the **Next.js** preset and **Root Directory** `apps/web`. The site uses Next.js static export and needs no runtime environment variables, API host, or database. Follow [the deployment and domain guide](docs/deployment-vercel.md) for the exact Vercel and `brew67potions.us` steps.

The original POC/PDD, FastAPI code, and historical commerce documentation remain in the repository for reference. They are not deployed with the static website. The user's current website scope supersedes the earlier full-stack hosting plan.
