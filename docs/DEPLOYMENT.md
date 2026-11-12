# Publish GuestLift on a real website

> **Public-launch scope:** A static marketing site and interactive fictional-data demos. **Not** a merchant-facing service for customer data yet.

## Recommended first launch: Cloudflare Pages + GitHub

This approach publishes the **frontend only**, safely keeping the unauthenticated local Python/SQL API off the public internet. The operator can explore the website, follow a mock Toast/Square ingestion, and test a coupon scenario in their browser. No real restaurant files are sent to a server.

### Step A — verify the site on your Mac

From the repository root:

```bash
# Option 1 — local Docker stack, including Python + PostgreSQL
docker compose up --build

# Visit http://localhost:3000
# Try /demo and /offers
```

Or use the separate frontend dev server for design work:

```bash
cd frontend
npm install
npm run dev
```

Run the offer calculation tests:

```bash
cd frontend
npm run test:offers
```

Verify the **static export** that will be published:

```bash
cd frontend
GUESTLIFT_STATIC_EXPORT=1 npm run build
# Output should be in frontend/out/
```

The static-build command works because `frontend/next.config.ts` enables Next.js `output: 'export'` only when `GUESTLIFT_STATIC_EXPORT=1`. The local Docker path leaves the setting off, allowing `next start` as before.

### Step B — commit to GitHub

From the repository root, after copying in the updated files:

```bash
git status
git add .
git commit -m "feat: add operator offer studio and public site design"
git push origin main
```

Check that your GitHub repository contains `frontend/`, `backend/`, `docs/`, and the new `/offers` page. Do not commit `.env`, `node_modules`, local database files, or credentials.

### Step C — connect Cloudflare Pages

1. Open https://dash.cloudflare.com/ and select **Workers & Pages**.
2. Select **Create application**, choose **Pages**, then **Import an existing Git repository**.
3. Authorize GitHub and select `george962/GuestLift`.
4. Configure the build:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | `Next.js (Static HTML Export)` |
| Root directory | `frontend` |
| Build command | `GUESTLIFT_STATIC_EXPORT=1 npm run build` |
| Build output directory | `out` |
| Node version (if configurable) | `22` |

5. Deploy. Cloudflare assigns a `*.pages.dev` URL once a deployment succeeds. **We cannot provide your URL until you complete this step.**
6. Test `/`, `/offers`, `/demo`, and `/how-it-works` on the public URL, including a phone-sized browser window.
7. Push future commits to `main` to trigger automatic deployment.

The root-directory and output settings match Cloudflare's official static Next.js instructions: https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/.

### What works on the public site?

- Homepage and architecture story.
- Browser-only Toast/Square *sample* pipeline and source record inspection.
- Browser-only coupon/offer scenario with editable code, threshold, discount and margin assumptions.
- No FastAPI, PostgreSQL, real merchant uploads, private data, or persistent customer accounts.

**Important:** The browser demo can be useful even though it does not connect to a publicly hosted Python API; the page explicitly labels the mode. The public site never tries to call `localhost:8000`.

### Optional: custom domain and professional business identity

After publishing the `pages.dev` version, purchase a domain you control. In Cloudflare Pages, select **Custom domains** and follow the DNS verification prompts. Set up a legitimate business contact address with an email provider *before* adding a contact/pilot form or `mailto` link. Do not add a form that appears to submit if nothing is receiving the messages.

## Why not deploy the current backend publicly?

The local backend presently uses public unauthenticated import and reset endpoints and a demo database. A public backend could be abused to erase or alter data; CORS is not an authentication boundary. Do not publish it unchanged.

A real restaurant pilot requires, at minimum:

- Merchant registration and authorization, user authentication, tenant isolation and access rules.
- Properly protected file uploads, size/rate limits, validation, per-tenant storage, encryption and retention policies.
- A private production database with backups and operational monitoring.
- Restaurant-approved Toast exports or Square OAuth access and review of platform terms.
- Explicit definitions for matching coupon redemptions to individual order records and a plan to handle missing codes/identifiers.
- A pilot agreement, privacy review, and security testing before receiving real customer data.

For a future hosted Python API, Render is one option but its **free services spin down after inactivity** and free web-service files are ephemeral; free Render Postgres databases also expire after 30 days. It is suitable for testing, not a production merchant system. See https://render.com/docs/free. If using Vercel for a real business website, note that the free Hobby plan is limited to non-commercial personal use; Pro is the commercial option (see https://vercel.com/docs/plans/hobby).

## Launch checklist

- [ ] `npm run test:offers` passes.
- [ ] `GUESTLIFT_STATIC_EXPORT=1 npm run build` succeeds.
- [ ] Homepage describes the product in restaurant terms.
- [ ] Offer studio calculations respond to input changes.
- [ ] Demo shows source format, GRDC, quality and metrics; clearly says it is sample data.
- [ ] No live uploads or unauthenticated API is publicly exposed.
- [ ] All four public URLs work after deployment.
- [ ] Domain and contact channels are configured only when genuinely operational.
