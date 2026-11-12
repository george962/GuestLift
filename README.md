# TableSignal v0.7 — Restaurant intelligence SaaS prototype

**Know your guests. Grow with clarity.**

This release builds directly on **GuestLift v0.1–v0.5 / TableSignal v0.6**. It preserves the Toast-shaped and Square-shaped synthetic data adapters, shared GRDC order model, campaign/redemption matching, workspace analytics, and account-backed read-only analyst.

**This is a developer prototype.** All example data are fictional. Real customer files, merchant credentials and live charges must not be used. `TableSignal` is a provisional working name; trademark/domain availability has not been verified.

## What changed in v0.7

1. **Expanded animated homepage**: richer product hero, looping capability marquee, hover motion, 4-step interactive import-to-decision story, moving data visuals, interactive analyst questions, evidence-based insight cards, account-journey section, FAQs, and closing CTA. Accessible controls and reduced-motion preference supported.
2. **Actual customer-facing account pages**: `/sign-in`, `/sign-up`, `/forgot-password`, `/reset-password`, `/onboarding`, `/account`, `/settings`; all based on Supabase Auth when the developer supplies credentials. Sign-up and sign-in preserve a safe onward destination, e.g., a pricing visitor can reach Billing.
3. **Test subscription flow**: `/pricing` → `/sign-up?next=%2Fbilling` → `/onboarding` → `/billing`; the server creates a Stripe **test-mode** Checkout session and provides access to a test customer portal. Signed subscription webhooks, not a browser redirect, determine Growth access.
4. **Visible account state in navigation** when a Supabase session exists, plus a consolidated account hub.
5. **Safe readiness endpoint** at `/api/saas/config` returns only feature booleans, not keys or emails, and advertises that real payments/uploads are disabled.
6. No new third-party animation dependencies: the moving website is built with React interactions, CSS and native browser APIs.

## Quickstart — existing folder on Mac

If the entire v0.7 source is already copied over your existing `~/GuestLift` repository (preserve `.git` and existing `.env`), run:

```bash
cd "$HOME/GuestLift" || exit 1
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

- Homepage: http://localhost:3000
- Free demo: http://localhost:3000/workspace
- Sign in: http://localhost:3000/sign-in
- Create account: http://localhost:3000/sign-up
- Pricing: http://localhost:3000/pricing
- Billing: http://localhost:3000/billing
- Safe integration state: http://localhost:8000/api/saas/config

**Important:** pages are present immediately, but a real sign-up requires a Supabase project and the root `.env` values. Stripe test Checkout requires Stripe test keys and its webhook signing secret. Follow [Account and billing setup](docs/ACCOUNT_BILLING_SETUP.md). Without configuration, buttons will explain why access is unavailable rather than pretending an account or charge exists.

## Route map

| Route | Purpose | Needs credentials? |
|---|---|---|
| `/` | Animated, scrollable public product website | No |
| `/start`, `/workspace` | Guided fictional demo and analytics | No |
| `/product`, `/help`, `/pricing` | Product tour, help and plans | No |
| `/sign-up`, `/sign-in`, `/forgot-password`, `/reset-password` | Email/password identity and recovery | Yes, Supabase |
| `/onboarding`, `/account`, `/settings` | Saved restaurant profile and account | Yes, Supabase + local API |
| `/billing` | Subscription status, Stripe test Checkout, customer portal | Yes, Supabase + Stripe test settings |
| `/connect`, `/import`, `/campaigns`, `/offers`, `/demo` | Synthetic-data technical workflows retained for testing | No; no real merchant files |

## Verifications

- **25 Python tests pass** using the container-side version of pytest.
- **29 JavaScript tests pass** using Node's test runner.
- Updated TypeScript/TSX files pass TypeScript *syntax parsing*; a full production Next.js build was **not run** because the package registry was unreachable in this environment.
- Browser review of the standalone HTML preview is not a substitute for a built Next.js browser acceptance test.

## Architecture and boundaries

- Frontend: Next.js 15 / React 19 / TypeScript; new animation UI uses CSS, not a video or stock footage.
- Local API: FastAPI backed by PostgreSQL, identity verification against Supabase Auth, owner-scoped *synthetic* workspace data.
- Billing: Stripe server-created **test-only** subscriptions and signed webhooks; no live keys accepted.
- AI: Rules-based evidence-linked analyst in public sandbox; optional LLM explanations over synthetic **aggregates** only if configured, with subscription gate.
- Security: Legacy demo fixture APIs remain unauthenticated and bound to localhost. The backend is **not safe to deploy publicly** as it stands. No real merchant or cardholder data should enter this prototype.

For the next steps, see the [roadmap](ROADMAP.md), [billing setup](docs/ACCOUNT_BILLING_SETUP.md), and [implementation status](docs/IMPLEMENTATION_STATUS.md).
