# GuestLift — Product Roadmap (v0.5)

> Updated 2026-11-12 · **Product objective:** Restaurant operators should understand their business and decide what to investigate next. **Technical objective:** verified, provider-neutral data foundations. **Commercial objective:** paid, secure per-location workspaces after an operator pilot.

## The product in one sentence

**A restaurant intelligence workspace connecting transactions, customers, locations and promotions, with an evidence-backed AI analyst.**

## v0.5 — Unified operator workspace and SaaS foundation

### Shipped in the codebase

- [x] Collapse the old six public top-level tabs to **Why GuestLift / Product / Pricing**.
- [x] Build one unified product workspace with Overview, Customers, Campaigns, Ask GuestLift, Data Sources and Account/Billing sections.
- [x] Make business metrics computed from the existing fictional orders, not static screenshot figures.
- [x] Show recorded campaign activity separately from hypothetical new offer costs.
- [x] Add deterministic pattern detection with metric evidence and caveats.
- [x] Build a controlled read-only question engine with evidence keys, no arbitrary generated SQL.
- [x] Add optional Supabase email/password signup and backend authentication verification, default OFF until configured.
- [x] Add per-account tenant-scoped **synthetic** sample order storage and isolated workspace profile.
- [x] Add Stripe TEST Checkout, billing portal and signed webhook handling as an **optional integration foundation**.
- [x] Gate account-based AI analyst access on server-stored active/trialing Growth entitlement.
- [x] Add an optional LLM response path over **aggregated non-identifying synthetic metrics** only.
- [x] Add tests for workspace isolation, plan checks, import/coupon rules and customer summaries.

### Verify locally before publishing

- [ ] Run a complete Next.js TypeScript typecheck and production Docker build on macOS.
- [ ] Run Python tests in Docker and the JavaScript tests in the frontend container.
- [ ] Open the six workspace sections on desktop and mobile. Validate menu, charts, scenarios and insights.
- [ ] Check the last synthetic Import Lab upload is carried into Overview/Customers/Campaigns.
- [ ] Verify static Next.js export and links with no configured backend or credentials.
- [ ] If account testing is desired, configure Supabase Auth and verify email sign-up/login/logout.
- [ ] If payment testing is desired, configure Stripe test product/price and simulate subscriptions/webhooks (never live cards).
- [ ] Confirm user A and user B receive distinct workspace IDs and isolation in PostgreSQL.
- [ ] Have 2–3 restaurant operators complete a 5-minute synthetic demo without technical guidance; record exact objections.

## What a restaurant owner does

1. **Try a sample workspace.** No account required; all records explicitly fictional.
2. **See sales and customer patterns.** Each observation cites which metrics were calculated.
3. **Evaluate a campaign.** Identify recorded redemptions, discounts and modeled cost assumptions.
4. **Ask a question.** Controlled analyst tools explain the evidence and recommend next experiments.
5. **Consider an account.** Supabase account foundation exists; subscription is TEST mode only.

## Monetization hypothesis

| Tier | Proposed model | Product entitlement | Status |
|---|---|---|---|
| Sandbox | Free | Fictional browser workspace and read-only rules analyst | Working |
| Growth | Illustrative **$149/location/month** | Private synthetic workspace + optional model-backed analyst + future merchant data | Supabase configurable; Stripe TEST only |
| Enterprise | Custom | Integration, governance, multi-location roles, pilot services | Concept only |

The monetary figure is a **pricing hypothesis**, not validated willingness to pay. Do not start charging for a service that cannot securely ingest merchant data.

## Next milestones (must pass gates)

### M7 — Production account and data security

- [ ] Replace the legacy unauthenticated API with a separately deployed protected service. Eliminate `/api/reset` and open upload routes from production builds.
- [ ] Add organization memberships/roles, all-tenant authorization enforcement and dedicated database access checks.
- [ ] Implement migration tooling, transaction boundaries, secrets management, security headers, CORS/CSRF protections, rate limits and monitoring.
- [ ] Add secure file lifecycle, malware/content validation, encrypted storage, deletion/retention controls and backups.
- [ ] Complete privacy review, data-sharing agreement and external security assessment before handling real data.
- [ ] Add subscription-event reconciliation, cancellation/downgrade behavior, dunning/failed-payment state and billing test coverage.
- **Gate:** No cross-tenant access in integration tests; security review completed; private API independently deployable.

### M8 — Authorized merchant connectors + data correctness

- [ ] Verify real Toast and Square export/API formats with merchant permission and test accounts.
- [ ] Add connection state, OAuth scope/credential storage and revocation where provider permits it.
- [ ] Implement updated orders, late refunds, historical backfills, timezone/business-day logic, reconciliation and data-quality reports.
- [ ] Design customer identity linking only with documented provenance and lawful data use.
- **Gate:** A permissioned pilot dataset reconciles to source reports, including adjustments, with audited source lineage.

### M9 — Restaurant customer intelligence and campaign economics

- [ ] Add proper time windows, cohort segmentation and retention/lapse definitions with identity coverage and data sufficiency.
- [ ] Include campaign issuance, eligible audiences, redemptions, costs and refund corrections.
- [ ] Build incremental-lift analysis using pre-treatment randomized assignments or another defensible identification strategy.
- [ ] Ask operators what decisions and evidence they would actually pay for; evaluate pricing/ROI on real pilot processes, not simulated profit.
- **Gate:** Pilot operator uses GuestLift to make a documented decision and can reproduce the underlying calculations.

### M10 — AI product and commercialization

- [ ] Add a constrained tool catalog with validated SQL/analytics endpoints (no free-form database actions).
- [ ] Evaluate AI answers against an expert-designed question set: factual accuracy, correct refusals, evidence, no unsupported causality, privacy.
- [ ] Add account usage quotas, cost limits, audit logging, user feedback and opt-in privacy controls.
- [ ] Deploy paid pilot to a properly secured hosting environment with verified billing and support channels.
- **Gate:** External technical/security review and a genuinely interested, permissioned merchant pilot.

## Work order

**Do not build everything at once.** First verify v0.5 on your Mac; then conduct a restaurant-operator walkthrough. Security and authorized data ingestion must come before inviting merchants to upload their real files. New features must improve one of three decisions: customer retention, promotion economics or location operations.

Prior engineering milestones and v0.4 release notes remain documented in `docs/IMPLEMENTATION_STATUS.md` and `docs/RELEASE_NOTES_v0_4.md`.
