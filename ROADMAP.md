# TableSignal roadmap — v0.13 Sandbox integration milestone

**Status: local developer preview, not production-ready.** Updated 2026-11-22.

## Product direction

**Connect → Discover → Investigate → Decide → Track.** A restaurant operator sees evidence-linked changes in orders, identified guests and promotion spending, investigates uncertainty, saves a decision and revisits the outcome. Do not promise causal lift without an appropriate experiment.

## Current capabilities (source exists; external operation needs verification)

- Next.js marketing site, synthetic sample workspace, animated walkthrough, sign-up/sign-in, onboarding, analyst, connection and billing screens.
- FastAPI, PostgreSQL local account/session prototype, Square Sandbox integration code, Stripe TEST subscription scaffolding, and evidence-based analytical functions.
- Pure v0.12 provider-location quote rules remain a standalone reference. v0.13 introduces a separate **flagged Sandbox-only** monitored-location selection linked to order scoping and Stripe TEST quantity; this is not a production entitlement or live billing service.
- Existing ZIP archives and dated milestone docs are historical artifacts, **not an installation method or evidence of release readiness**.

## Current acceptance priorities (in order)

1. Pass automated CI: Node tests, TypeScript, Next production build, Python tests, browser smoke, and secret scanning on the *same* commit.
2. Test end-to-end: sign up → verify session/onboarding → authorize own Square Sandbox → sync synthetic orders → isolated analysis → Stripe TEST checkout → reconcile → cancel.
3. Eliminate public/demo reset and untrusted-upload paths from any hosted configuration; move to a production identity and tenant isolation model.
4. Build and test *server-derived* canonical location entitlements, scoped data access, and Stripe quantity/invoice reconciliation. No paid-location claims before this.
5. Stage with HTTPS, migrations, managed secrets/DB/backups, monitoring, incident and support processes, terms and privacy consent.
6. Pilot with one consenting Square merchant after the relevant security gates pass; measure whether the recurring workflow changes a real decision.

## Commercial assumptions (not active billing)

- Growth **$99/selected monitored location/month**, provisional. This is **not** the Stripe TEST price: TEST amounts come from `STRIPE_GROWTH_PRICE_ID`.
- A proposed 14-day no-card trial starts only after first verified healthy sync; **not implemented**.
- Square production OAuth and Stripe LIVE are **disabled / unverified**. Toast production support is out of scope for the first launch.

## Launch gate references

- [Production readiness status and evidence](docs/PRODUCTION_READINESS.md) — authoritative pass/fail checklist.
- [Full v0.13→v1.0 acceptance criteria](docs/V013_TO_V1_PRODUCTION_GATES.md).
- [Location, signup and pricing design](docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md).

Do not enable real merchant data or payments until all applicable gates have independently verified evidence and owner approval.

## v0.13 implementation milestone — Sandbox location selection → Stripe TEST quantity

- **Implemented behind `TABLESIGNAL_SANDBOX_LOCATION_BILLING=1` (default OFF):** authenticated Square Sandbox location discovery, owner selection of eligible physical locations, persisted per-workspace selections, scoped order synchronization and analytics, and checkout quantity derived from server records.
- Stripe TEST reconciliation checks the selected location digest and quantity reported by the verified subscription. Selection changes are blocked for active/trialing plans pending proration support.
- `GET /api/saas/billing/quote` is a **proposed-price preview only**, not Stripe's actual charge amount or an invoice. The existing Stripe TEST Price ID controls actual TEST checkout values.
- New backend tests must pass in CI; **a real Square Sandbox seller and Stripe TEST checkout/webhook/cancel flow still require live developer verification** before claiming v0.13 gate completion.
- This does not enable real merchant OAuth, real subscriptions, secure hosted auth, automatic refresh, refunds reconciliation, migrations, production-grade locations or production deployment.

**To test locally:** set `TABLESIGNAL_SANDBOX_LOCATION_BILLING=1` in local `.env`, run `docker compose up -d --build`, then visit `/connections` to select locations before sync and `/billing` to view and test the quantity. Do not set this flag in any public deployment; the entire stack remains local-dev-only.
