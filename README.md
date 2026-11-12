# TableSignal — Restaurant intelligence for owners (working name)

**v0.6 — UX, interactive motion, and self-service account flow**

> This remains the `george962/GuestLift` GitHub repository internally. **TableSignal is a provisional customer-facing name, not trademark/domain-cleared.** No real restaurant customers, real payments, live integrations, or verified incremental marketing impact are represented.

## The actual product promise

For restaurant operators: **see who comes back, understand which discounts are costing money, and know what to investigate next**. This demonstration uses fabricated records only. The analytical engine computes orders, sales, guest-ID coverage, repeat purchasing among identified guests, and recorded promotion activity. The rules-based sample analyst grounds answers in evidence fields. Optional account-gated OpenAI explanations remain server-configured and off by default.

## What changed in v0.6

- **Clear public landing page:** explicit audience, promise, capabilities and next action.
- **Motion-powered product tour:** three automatic, pauseable, clickable dashboard scenes; calculated *fictional* totals; accessible reduced-motion behavior; no stock video and no external media dependency.
- **Four core product tasks:** Overview → Guests → Promotions → Ask the analyst. Data and account controls are moved into dedicated pages.
- **Getting started** at `/start`, `/onboarding` and `/connect`; the product shows what can happen with or without account setup.
- **Dedicated pages:** `/sign-in`, `/sign-up`, `/forgot-password`, `/reset-password`, `/account`, `/settings`, `/billing`, `/pricing`, `/help`, `/product`.
- **Auth:** Supabase email/password with session-based sign-in, password reset and email confirmation. Requires configuration, not a fake local account.
- **Billing:** Stripe **test-mode only**, using existing authenticated backend endpoints and server-side webhook subscription state. No real charges.
- **Renamed public UI:** TableSignal (provisional). Internal code, sample field names, service environment keys, and existing repo remain GuestLift for backward compatibility.
- **All v0.5 analytics, imports, tests and SQL schema retained.**

## Quickstart (no extracting if files are already in project)

From your **existing** `~/GuestLift` folder after putting the v0.6 source files there:

```bash
cd "$HOME/GuestLift" || exit 1
ls -l frontend/app/page.tsx frontend/app/billing/page.tsx frontend/components/motion-tour.tsx
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

- Home: http://localhost:3000
- Getting started: http://localhost:3000/start
- Product explanation: http://localhost:3000/product
- Workspace: http://localhost:3000/workspace
- Pricing: http://localhost:3000/pricing
- Sign-in: http://localhost:3000/sign-in
- Billing: http://localhost:3000/billing
- Help: http://localhost:3000/help

The public **fictional demo** is accessible without Supabase, Stripe or an API key. Account signup/login will display a configuration notice until Supabase is connected.

## Optional real account infrastructure (still for synthetic workspace)

Read [`docs/ACCOUNT_BILLING_SETUP.md`](docs/ACCOUNT_BILLING_SETUP.md) and [`docs/V06_SITE_OPERATIONS.md`](docs/V06_SITE_OPERATIONS.md).

1. Set up Supabase Auth with email verification, redirects `/sign-in` and `/reset-password`, and public project URL + **publishable** key in `frontend/.env.local` or frontend build environment.
2. Set backend `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` for **remote token validation**.
3. Stripe test mode: configure a test product/recurring Price ID, test secret key and signed test webhook at `/api/saas/billing/webhook` on a **secured test environment**. The backend intentionally rejects non-test keys.
4. Optional OpenAI model-backed aggregate explanations: set server-only credentials after reviewing the data policy. No raw customer IDs are sent to the optional model.
5. Never deploy the current unauthenticated FastAPI demo publicly. It includes demo reset/import endpoints and lacks merchant-grade security.

### Data and billing honesty

- Public website is a **synthetic sandbox**, even when visitors upload local fictional files in the browser.
- Signed-in workspace is seeded from **synthetic fixtures**; it is not a secure merchant account.
- **$149/location/month is a pricing hypothesis, not a live offer.** No live billing or actual per-location usage metering exists.
- Actual billing needs a live checkout integration, metering, entitlement logic, legal pages, refund/cancellation policy and security review.
- We do not infer missing guest identities or claim observed coupon activity proves incremental ROI.

## Validation

- Python backend: 23 tests passing in this environment.
- JavaScript analytics and UI source smoke checks: 26 tests passing in this environment.
- New v0.6 source/navigation smoke test: included.
- TSX syntax: parsed with globally installed TypeScript; no syntax diagnostics.
- **Next.js build and real browser interactions not yet independently verified** because npm package registry access was unavailable in this environment. Run Docker build and check the new routes on your Mac before deployment.

## Legacy and source continuity

This is a **complete replacement source tree** based on v0.5, not patches. It retains `/import`, `/campaigns`, `/offers`, `/demo`, `/how-it-works` as legacy deep links for technical review. They are deliberately absent from main navigation. The underlying database, tests and API continue to use existing filenames, endpoint prefixes and environment names to avoid breaking existing local installations.
