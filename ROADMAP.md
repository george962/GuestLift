# TableSignal — active development roadmap (v0.9, November 2026)

## Goal

A restaurant owner securely connects their POS account once, receives a trustworthy private view of sales and known guest behavior, and uses evidence-backed questions to decide which marketing tests may be worthwhile. Subscription billing funds ongoing synchronization, analysis and onboarding support—*after real restaurant value has been validated*.

## Completed milestones

- **v0.1–v0.4:** Synthetic Toast/Square adapters, common restaurant order contract, local SQL persistence, CSV import lab, campaign/redemption example and modeled promotion cost testing.
- **v0.5–v0.7:** Public animated website, more intelligible navigation, account and Stripe test billing page scaffolds, read-only insights and hypothetical pricing.
- **v0.8:** Local PostgreSQL email/password accounts, Argon2id hashes, revocable session cookies, CSRF protection, profile settings, private SQL workspace identity, Stripe test subscription gates.
- **v0.9 (source delivered):** Explicit onboarding/plan selection, private **empty-by-default** dashboard, actual Square **Sandbox API** connection, developer token and Sandbox OAuth modes, encrypted OAuth credentials, per-workspace Square orders and sync runs, idempotent replays, page-limited payment/customer linkage, local assisted setup queue, source-specific financial limitations, mocked API/isolation tests. API calls to a user's actual Square Sandbox remain to be verified.

## Current acceptance work (do this before another big UI build)

- [ ] Confirm full Docker Next.js production build on Mac, TypeScript and mobile layout.
- [ ] Connect the user's own Square Sandbox application; confirm ListLocations, ListPayments and SearchOrders return authorized test records.
- [ ] Create completed fictional paid orders in the Square Sandbox and sync them into the user's individual account dashboard.
- [ ] Repeat import and verify updates, zero cross-account leakage and disconnect/delete behavior.
- [ ] Configure optional Stripe TEST checkout and webhook, verify subscription authorization; do **not** enable live charges.
- [ ] Observe one nontechnical restaurant owner walking through the workflow. Record confusion and willingness to pay.

## v0.10 — dependable ingestion & reporting

- Proper source reconciliation: payments/returns/refunds/service charges and tax/tip/currency.
- Durable, scheduled background ingestion with retry/queue/dead-letter/status alerts and proper date-window backfills.
- Data quality and completeness checks against Square exports, tax methodology and historical corrections.
- Integrations validated against at least one genuinely permissioned Sandbox test merchant.

## v0.11 — security and real customer pilot preparation

- Proper tenant organizations/team roles, formal database migrations, private managed Postgres hosting, encrypted secret manager, HTTPS, verified Square production OAuth access and revocation monitoring, privacy/legal/security review.
- No real merchant data until a secure controlled pilot is authorized and operationally justified.

## v0.12 — AI and marketing decisions (only grounded in evidence)

- Cohort trends, actual campaign assignments/redemptions, experiment/holdout comparisons, natural-language analysis of verified aggregations with citations and uncertainties.
- Account-specific usage quotas and cost limits, private user control and external model privacy decisions.

## Business validation

- Free public demo remains sample-only.
- Proposed Growth plan ($149/location/month) includes standard connection onboarding and automatic sync **when implemented**, not currently available.
- Complex custom connections may require quoted one-time setup fees, based on observed integration effort and operator demand—not arbitrary promised ROI.

## Definition of production-ready

Every blocker in [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) must be independently validated before real paying customers or merchant datasets.
