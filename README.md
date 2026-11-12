# GuestLift — Restaurant Intelligence Workspace

**Version 0.5.0 · SaaS foundation + evidence-based AI analysis · November 2026**

GuestLift helps restaurant operators explore sales, returning customers and promotion economics in a **single workspace**. Beneath the interface, fabricated Toast-style CSV and Square-shaped JSON orders flow through a provider-neutral data model. The new workspace exposes *what the data shows*, *what it cannot show*, and *what to investigate next*.

> **IMPORTANT:** This is a synthetic-data prototype, **not** a production merchant service. Do not upload real customer data, payment card data, POS credentials, or live restaurant records. The old FastAPI demo endpoints are not authenticated. Do not expose the API or Docker services publicly. Stripe is **TEST MODE ONLY** and pricing is exploratory.

## Try GuestLift immediately

From the repository root on a Mac with Docker Desktop running:

```bash
docker compose up --build -d
docker compose ps
```

- Homepage: http://localhost:3000
- Unified workspace: http://localhost:3000/workspace
- Pricing concept: http://localhost:3000/pricing
- Sign-in (requires optional Supabase configuration): http://localhost:3000/account
- FastAPI test documentation: http://localhost:8000/docs

**No account or API key is required** for the public-safe sandbox. Choose **Overview → Customers → Campaigns → Ask GuestLift**. The workspace uses **56 fictional sample orders** and two coupon campaigns. Import your own **synthetic** fixture files from the Data Sources tab; the browser-only workspace can then use your last synthetic import.

## What's new in v0.5

| Area | Implementation |
|---|---|
| Product design | New coherent workspace with 6 in-app sections; public top nav reduced to Why GuestLift / Product / Pricing |
| Operator overview | Data-calculated sales, order count, customer coverage, discounts, location bars, and detected descriptive patterns |
| Customers | Provider-scoped synthetic identity, repeat customers, anonymous-order coverage and methodological limits |
| Campaigns | Recorded fictional redemptions **and** a separate future-offer cost scenario |
| Ask GuestLift | Verified metric tools and evidence fields; optional actual LLM wording over aggregated data (server key required) |
| Accounts | Optional **real Supabase email/password sign-up**; bearer token checked with Supabase Auth on every private API request |
| Workspace data | Per-account synthetic data stored in tenant-scoped PostgreSQL rows; business profile settings |
| Subscription | Stripe **test** Checkout + portal + signature-verified webhook skeleton; account-based AI plan checked server-side |
| Monetization | Proposed free sandbox / per-location Growth subscription / enterprise onboarding model |
| Branding | Restaurant ontology mark: guests, locations and campaigns linked to one validated record |

**Terminology:** This is an *ontology-inspired*, entity-centric architecture, **not** an implementation of Palantir Foundry or a Palantir integration.

## Optional account + subscription setup

Supabase, Stripe, and OpenAI are **independent, optional integrations**. They require your own credentials and are intentionally off by default. See **[docs/ACCOUNT_BILLING_SETUP.md](docs/ACCOUNT_BILLING_SETUP.md)** for exact steps, configuration and Stripe CLI webhook testing.

1. Create a Supabase project; configure email/password Auth, and obtain the public project URL and publishable key.
2. Create `./.env` from `.env.example`; fill in both the frontend and backend Supabase settings. **Never commit `.env`.**
3. For payment testing, create a recurring Growth price **in Stripe TEST mode**, configure `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_GROWTH_PRICE_ID=price_...`, and a webhook secret from Stripe CLI.
4. Run Docker and visit `/account` to sign up. Once signed in, your account gets an individual fictional workspace. No real merchant uploads are allowed.
5. The account-based analyst is gated: only a verified Growth subscription in `active` / `trialing` status can access `/api/saas/analyst`. Checkout success alone never unlocks features; verified subscription webhook status does.
6. **Optional LLM:** configure `GUESTLIFT_ENABLE_LLM=1`, `OPENAI_API_KEY` and `OPENAI_MODEL` for read-only model summaries over **aggregated synthetic metrics only**. Otherwise the evidence-first rules analyst continues to work.

### Pricing model (proposal, not a live offer)

- **Sandbox — $0**: frictionless public synthetic demonstration with deterministic insights.
- **Growth — illustrative $149 per location per month**: private workspace, reporting, planned account-based AI analyst. Actual Stripe Price ID controls checkout pricing and must be checked for consistency.
- **Enterprise — custom**: multi-location integrations, governance, implementation and pilot support.

Do not use live Stripe keys or advertise working real billing with this version. The code explicitly rejects non-`sk_test_` keys.

## Run tests

```bash
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
```

Local validation for this release: **23 Python tests and 23 JavaScript tests passed**. TypeScript/TSX syntax transpilation was also checked. A complete Next.js typecheck and production build still require Docker/npm on your Mac; do not describe the app as production-ready based on tests alone.

## Source map

```text
frontend/app/                   Marketing site, unified workspace, pricing, account pages
frontend/lib/workspace-analytics.mjs
                                Evidence-backed rules and pattern discovery
frontend/lib/supabase-client.ts Optional hosted Auth browser client + API helper
backend/app/saas.py             Workspace ownership, synthetic tenant rows, test billing, protected analyst
backend/app/insights.py         Server-side aggregate metrics and controlled read-only questions
backend/app/database.py        Original canonical POS and coupon tables
backend/app/adapters.py        Synthetic Toast/Square parsers
backend/tests/                  Reconciliation, auth gates, workspace isolation, campaign tests
frontend/tests/                 JS metrics, imports, campaign and patterns tests
docs/                           Architecture, billing, pilot, AI and roadmap evidence
ROADMAP.md                      Current scope, what shipped, what remains
```

## Deployment boundary

- **Public today:** publish the static frontend sandbox with **no real data and no backend**, using the instructions in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- **Locally:** accounts, Supabase user verification and Stripe test checkout can be exercised through Docker after configuration.
- **NOT ready for production:** merchant uploads, live payments, multi-user organizations, SOC 2 posture, production authentication/security review, authorized vendor synchronization, measured uplift or live AI over customer PII.

The API includes legacy public demo routes such as `/api/reset`; those must be removed or isolated in a separate hardened private service before any public backend deployment.

All providers, customers, coupons and sales figures used in GuestLift's demonstration are fictional. GuestLift is not affiliated with Toast, Square, Supabase, Stripe, OpenAI or Palantir.
