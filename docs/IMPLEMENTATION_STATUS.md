# CURRENT IMPLEMENTATION STATUS — v0.9, November 2026

**Local prototype, not production merchant software.** Private account dashboard starts empty, Square Sandbox OAuth or developer-token integration is implemented with server-only credentials, API sync per account and bounded data handling. The fictional free demo is separate. Backend test suite and frontend calculation/source tests run locally. Full Next.js build and actual Square Sandbox transactions still require verification on the user's Mac.

**Most important distinction:** The private dashboard is from the authenticated workspace's SQL-backed Square **Sandbox** data, not the same bundled 56 orders for everyone. Paid account AI is still gated behind a verified Stripe TEST subscription. No live payments and no real merchant customer data.

**Remaining gate:** read [Production readiness](PRODUCTION_READINESS.md), [Square Sandbox setup](SQUARE_SANDBOX_SETUP.md), and [v0.9 architecture](V09_ARCHITECTURE.md) before any external onboarding. Documentation below is retained as historical notes for older versions and can be outdated.

---

# TableSignal v0.7 — Implementation status (November 12, 2026)

**Delivered:** complete replacement source, expanded animated landing, Supabase Auth screens, safe pricing-to-account-to-billing path, server-generated Stripe **test** Checkout, signed webhook subscription handling, account page, and synthetic-only analytics.

**Verified:** 25 backend pytest tests, 29 frontend Node tests; TS/TSX source parsed without syntax errors. **Not verified:** full Next.js production build, Supabase/Stripe end-to-end tests using actual test credentials, public deployment, or interactive real-browser acceptance.

**Restrictions:** test/synthetic only. No live merchant data or live charges. Unauthenticated local fixture API must never be exposed publicly. No production security sign-off.

See [setup](ACCOUNT_BILLING_SETUP.md), [v0.7 notes](RELEASE_NOTES_v0_7.md), and [current roadmap](../ROADMAP.md).

---

# GuestLift v0.5 implementation checkpoint — 2026-11-12

The latest version is **v0.5**. It includes a unified fictional restaurant workspace, a controlled evidence-backed analyst, optional Supabase verified account auth and synthetic tenant data, and Stripe **test-only** subscription scaffolding. Billing and a real merchant-data API are **not** production-ready.

**Validation:** 23 Python tests and 23 JavaScript tests passed; 17 TypeScript/TSX files pass source syntax transpilation. The complete Next.js production build still needs to be verified using Docker/npm on the user's Mac.

**Read the current plan:** [ROADMAP.md](../ROADMAP.md) · [Account/billing setup](ACCOUNT_BILLING_SETUP.md) · [SaaS architecture](SAAS_ARCHITECTURE.md) · [AI methodology](AI_ANALYST.md).

---

## Archived v0.4 and earlier notes

# GuestLift — Current implementation status

**Version:** v0.4 · **Date:** November 12, 2026  
**Audience:** Restaurant operators and technical reviewers  
**Status:** Fully synthetic, demo-only application. Not production-ready and not connected to actual Toast or Square merchants.

## What now works (verified in source tests)

- Existing v0.3 Import Lab, with browser parsing of fictional Toast-style CSV and Square-shaped JSON and local SQL persistence, remains in the codebase.
- New `/campaigns` workflow for two campaign CSVs, coupon event-to-order matching, input validation, descriptive financial analysis and record drill-down.
- SQL tables for campaign configuration, coupon redemptions and import runs, with idempotent replay behavior.
- Fictional provider-scoped customer IDs, repeat-customer counts and visibility into anonymous orders; no identity stitching.
- An additional SQL schema column for optional customer ID, with safe additive migration for local older databases.
- New public-static browser campaign calculations; local FastAPI has campaign upload, report and sample-import routes.
- Updated homepage and navigation toward restaurant promotion decisions.

**Tests run:** 19 Python tests passed, 19 JavaScript tests passed, and a cross-language comparison showed identical example totals for both campaigns. The new TSX page passed TypeScript syntax parsing. **Full Next.js compilation, interactive browser visual review and public deployment were not verified in this environment.**

## Remaining limitations / work

- Current API is local-only and has no authentication, tenant isolation, secured storage or real merchant permission. Never expose it publicly.
- Files, names, coupons, costs, and customer identifiers in the public demo are fictional.
- Browser and Python paths both validate the *demo file contract*, not every configuration of a real Toast or Square export.
- Imported order amendments, refunds posted after initial import, campaign corrections, stacked promotions, and reliable source synchronization are not yet supported.
- Repeat detection works only where a stable synthetic ID exists inside a POS provider. It does not prove customer identity across brands, platforms or delivery systems.
- The scenario contribution estimate is based on an assumed margin and manually provided campaign cost assumptions. It is **not** measured incremental profit or promotional ROI.
- Actual restaurant use requires operator interviews, real CSV format validation with permission, and a separate secure onboarding architecture.

See [the new Campaign Import specification](CAMPAIGN_IMPORT.md), [v0.4 release notes](RELEASE_NOTES_v0_4.md), and [ROADMAP](../ROADMAP.md).

---

## Previous engineering checkpoints

# GuestLift — Build v0.2 implementation status

**Updated:** November 12, 2026  
**Type:** Demo-only code release, *not* a production integration.

## v0.2 additions (operator-facing prototype)

- Rebuilt homepage for restaurant owners and marketing leaders, with direct links to a new `/offers` studio.
- Added browser-side synthetic order selection (Toast/Square/both), percentage/fixed/free-item offer modeling, editable coupon code/threshold/unit cost/margin and an order-level cost breakdown.
- Added `frontend/lib/offer-model.mjs` with **four passing calculation tests**; all calculations use integer cents. Nothing measures coupon redemptions or causal lift.
- Updated v0.2 brand semantics: **navy=trust**, **indigo=source records**, **teal=validated canonical records**, **amber=campaign assumptions**, **rose=cost/risk**.
- Added `frontend/next.config.ts` static export mode, docs for Cloudflare Pages deployment, and public-site protection against trying to call a visitor's `localhost:8000`.
- **Not yet verified:** a full Next.js production/static build in this environment (npm dependency installation could not complete). GitHub CI now tests both builds.

## Implemented in this package

| Roadmap | Shipped | Evidence / notes |
|---|---|---|
| M0 | README, proposal, Mermaid architecture | `README.md`, `docs/architecture.md`, `docs/proposal.md` |
| M1 | Responsive Next.js marketing home, How It Works, interactive Demo | `frontend/app/`; browser mode uses bundled pre-normalized synthetic sample |
| M2 | Python parser for Toast order, item and payment CSV fixtures | `backend/app/adapters.py`, `backend/fixtures/toast/`, unit tests |
| M3 | Python parser for Square Orders-shaped JSON, separate payment/refund fixtures | `backend/app/adapters.py`, `backend/fixtures/square/`; **not** a live Square Sandbox API integration |
| M4 | Canonical SQL persistence with unique `(provider, source_order_id)` key and shared reporting; PostgreSQL configured in Docker | `backend/app/database.py`, `compose.yaml`; SQLite default for quick local use; no formal Alembic migrations yet |
| M5 | Demo UI calls local FastAPI to import fixture data and read computed SQL metrics; browser-only preview when API absent | `frontend/app/demo/page.tsx`, `backend/app/main.py` |
| M6 | Python unit/API tests, duplicate replay, CI workflow, Compose, basic documentation | `backend/tests/test_pipeline.py`, `.github/workflows/ci.yml`; deeper failure recovery/security still needed |

## Open items, intentionally not marked complete

- Square Sandbox token-based API client and test account flow.
- Real Toast export compatibility testing with authorized merchant data, including configurable columns and modified/voided orders.
- Robust status updates/upserts when the source order changes after original import.
- File-upload endpoints for untrusted arbitrary CSVs; prototype imports shipped fixture files only.
- Tenant authentication/authorization, least-privilege, audit policy, retention, production secrets management, backups.
- Formal migrations, fuller refunds/taxes/tips/payment reconciliation, currency/locale variants, timezone normalization, business-day policy.
- Customer-level loyalty, campaign assignments, experimental incrementality, restaurant contribution costs and predictive modeling.
- Verified public deployment / hosted API.
- Independent operator feedback and real pilot.

## Important demo semantics

- **Toast** fixtures contain the documented core column names from official Toast data export field reference, using deliberately fabricated rows. Operators can customize exports, so this does not certify arbitrary real Toast files.
- **Square** fixture is API-shaped and synthetic. `orders.json`, `payments.json`, and `refunds.json` represent multiple source objects bundled together for demo purposes. No authenticated API request is performed.
- **GRDC** is a proposed canonical model, with source IDs, order items, payment events, amounts in integer cents and warnings. It is not an adopted industry standard.
- **Net sales** for this demo are item gross minus order discounts minus pretax sale refunds, excluding tax/tip. This is a project-specific example; real vendor financial definitions require careful verification.
- **Browser demo** loads saved pre-normalized examples, showing interactive pipeline stages as a *preview*, not actually running the Python adapter. The API-connected mode runs the adapters and persists results.
- No customer-owned data, credit card numbers, real ROI or claimed causal promotion lift are used.

## Verification performed in this build session

- Seven pytest tests passed for adapters, invalid money, duplicate/missing source headers, USD validation, SQL idempotency, API endpoints and dashboard totals.
- TS/TSX source files passed TypeScript parser/transpilation syntax checks.
- Frontend dependency installation and `next build` could **not** run in this environment because the npm registry was inaccessible. GitHub Actions workflow is included for independent frontend build verification after upload.

**Next engineering priority:** Install dependencies, run the Next.js website, then verify the local frontend-to-FastAPI interaction and fix any issues found before presenting the app to real operators.

**V0.2 verification:** `python -m pytest -q` from `backend/` passed 7 tests, and `node --test frontend/tests/offer-model.test.mjs` passed 4 tests. The Next.js compilation and browser appearance still need confirmation on the user machine / CI.

---

## v0.3 — Import Lab release

- Added a public-safe, **real browser parser** for fabricated Toast CSV and Square JSON fixtures. This processes selected files locally (not just pre-normalized display state), validates headers, types, IDs, relations and cents, and computes unified metrics.
- Added a guided `/import` page with ZIP downloads for valid fixtures and a deliberately broken Toast fixture, file selection, clear errors, audit table, per-location bars, and a link to model a coupon against imported synthetic orders.
- Added a local-only `POST /api/upload/{provider}` FastAPI route: validates three files, enforces small size limits, calls Python adapters and persists canonical records through the existing SQL repository. SQL duplicate detection is unchanged (replays not edits).
- Replaced the generic chart icon with the two-source-to-one-data-model original vector mark. Updated the homepage to show an interactive record-flow demonstration.
- Browser import tests: 6 passing; existing offer tests: 4 passing; backend tests: 10 passing. `next build` must be verified on a machine with npm access (the execution environment could not resolve npmjs.org).

**Still not delivered:** Real seller authentication or authorized vendor integrations, general real-world POS export support, production-grade secure file handling, upserts of corrected orders, customer-level loyalty attribution, and causal experiment analysis. No merchant data should be uploaded to the current application.
