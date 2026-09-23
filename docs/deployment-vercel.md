# Put the static brew67potions site on Vercel

The current website is an informational Next.js static export. `pnpm build` creates HTML, CSS, JavaScript, and images in `apps/web/out`. It does not use the FastAPI service, PostgreSQL, Stripe, SMTP, or any runtime environment variables.

## 1. Deploy from GitHub

1. In Vercel, choose **Add New → Project** and import `its-arnavtech/Tri-Realm-Eco-Apothecary`.
2. Set **Framework Preset** to **Next.js** and **Root Directory** to `apps/web`. Deploy the `main` branch after the static-site PR has merged.
3. Use the detected `next build` build command and Node.js 24. If Vercel asks for an **Output Directory**, enter `out` (relative to `apps/web`). Do not enter `.next/standalone`.
4. Add one build environment variable: `ENABLE_EXPERIMENTAL_COREPACK=1`. Vercel reads the `pnpm@10.32.1` pin from the repository root `package.json`, then installs the `apps/web` lockfile with that supported version. Remove any old `API_INTERNAL_URL`, `DATABASE_URL`, or API-related variables from the web project; the static website does not use them.
5. Deploy and open the generated `*.vercel.app` URL. Check the homepage, concept gallery, each realm, the four concept pages, About, and Privacy. No page should make an `/api/v1` request.

Vercel's free Hobby plan is restricted to personal, noncommercial use. A brand or business site may require Pro even without checkout. Choose the plan that fits the site's actual use; there is **no database charge** for this website.

## 2. Connect `brew67potions.us`

Use the domain as an **external domain**. It can stay registered with Porkbun; no transfer is needed. The current DNS points to Porkbun's parked page.

1. In the Vercel project, open **Settings → Domains**. Add both `www.brew67potions.us` and `brew67potions.us`. Set `www.brew67potions.us` as the primary address and redirect the apex domain to it.
2. Copy the **exact** DNS records Vercel displays for this project. At Porkbun, open **Domain Management → Details → DNS Records**. Replace the parked apex `A` records with Vercel's required apex record, and replace the parked `www` CNAME with Vercel's required CNAME. Remove conflicting parked records for those hosts. Keep MX, TXT, and unrelated records.
3. Wait for Vercel to verify the domain and issue HTTPS certificates. Confirm `https://brew67potions.us` redirects to `https://www.brew67potions.us` and the site loads securely.

## 3. Final check

- Open the site on a phone and desktop. Check navigation, image loading, and links on all pages.
- Confirm every brew says **concept** and there are no cart, account, signup, or checkout links.
- Confirm the deployed build has only static routes and no required API or database service.

References: [Vercel Git deployments](https://vercel.com/docs/git), [Next.js static export](https://nextjs.org/docs/app/guides/static-exports), [Vercel Corepack](https://vercel.com/docs/builds/configure-a-build), [Vercel custom domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain), [Porkbun DNS records](https://kb.porkbun.com/article/68-how-to-edit-dns-records), and [Vercel Hobby rules](https://vercel.com/docs/plans/hobby).
