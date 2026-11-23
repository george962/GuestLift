# TableSignal customer product plan

**This is the working plan for the customer-facing product. Every change PR cites the milestone it advances and updates the status table below in the same PR.**

Owner: product owner (repo admin). Last updated: 2026-11-22 (M4).

## The promise we are building toward

A restaurant owner with 1–10 Square locations signs up, connects Square, and within 10 minutes sees one evidence-backed thing worth acting on. Every week after that, TableSignal tells them what changed, why it might have changed, and how the decision they made last time turned out. They pay per monitored location because this weekly loop saves or makes them more than it costs.

**Core loop:** Connect → Discover → Investigate → Decide → Track. If any step fails silently, the product isn't useful.

### Success metrics (instrumented in M6)
| Metric | Definition | Target for pilot |
|---|---|---|
| Activation | Sign-up → first insight viewed, same day | ≥ 60% |
| Time to first insight | Sign-up → first insight rendered | ≤ 10 min (excluding Square backfill wait) |
| Weekly loop | Workspaces that open the weekly brief in ≥ 3 of 4 weeks | ≥ 50% |
| Decision follow-through | Saved decisions that get an outcome readout | ≥ 70% |
| Trial → paid | Trials converting at day 14 | Measured, no target until pilot |
| Data trust | Synced revenue within ±0.5% of the Square sales report, per location per week | 100% of pilot locations |

## The golden-path journey (the acceptance test)

Every milestone must keep this journey passing end to end in CI (Playwright, against a mock Square API and Stripe test mode):

1. Visitor lands on `/`, opens the sample workspace, understands the value in < 2 min.
2. Signs up (managed identity), verifies email, and lands in onboarding.
3. Connects Square via OAuth, sees their locations, selects which to monitor.
4. Sees the backfill progress, then a "first insight ready" state.
5. Opens the weekly brief: changes, evidence, data coverage and caveats.
6. Investigates one opportunity and asks the analyst a follow-up question.
7. Saves a decision with a metric, a baseline and a follow-up date.
8. Trial starts after the first healthy sync; converts via Checkout; quantity = monitored locations.
9. After the follow-up date, sees an outcome readout for the decision (and receives it by email).
10. Adds a location (proration preview → confirm), cancels, keeps read-only access until period end, exports or deletes their data.

## Milestones

Ordered by dependency. Each milestone is one or more PRs; it's "done" only when its verification checks pass in CI and on staging.

### M1 — Journey harness (foundation for everything else)
- Mock Square API service (OAuth, ListLocations, SearchOrders/Payments/Refunds with pagination and 429s) used by tests and local dev.
- Playwright suite for an authenticated journey; each run signs up a fresh account; runs in CI on localhost processes (`scripts/journey.sh`) — the `docker` job already covers the images.
- Contract tests that pin the frontend ↔ backend API shapes.
- **Verify:** the CI job `journey` passes steps 2–7 using local auth; it fails if any step breaks.

### M2 — Real identity in the product
- Frontend OIDC integration (provider-agnostic, Clerk first) alongside dev local auth; workspace created on first sign-in.
- Email verification and password reset delegated to the provider; sign-out everywhere; session expiry handling in the UI.
- Account settings: profile, team member invite (owner + manager roles), delete account.
- **Verify:** journey step 2 passes in OIDC mode against the provider's test instance; cross-tenant isolation tests cover every endpoint (an automated route inventory fails CI if a new route has no isolation test).

### M3 — Data pipeline you can trust
- Square environment switch (`sandbox` | `production`), production stays gated off until the go-live checklist passes.
- OAuth token refresh, revocation handling and reconnect prompts.
- Background worker (a separate process with a DB-backed job queue, no new infrastructure): initial backfill (default 13 months), incremental sync every few hours, retries with backoff, 429 handling, checkpoints, idempotent upserts.
- Reconcile sales, refunds, discounts, tax and tips per location per day; flag gaps instead of hiding them.
- Data health surfaced to users: last sync, coverage %, known gaps, "data is stale" banners.
- **Verify:** pipeline tests against the mock (pagination, 429, mid-sync crash then resume, duplicate delivery); a reconciliation test asserts totals equal the fixture's Square report; a Square Sandbox seller syncs on staging.

### M4 — Insight → Decision → Track (the core value)
- Weekly brief per workspace: top changes vs. the trailing baseline, each with evidence (the numbers and query behind them), coverage, and confidence language. No causal claims.
- Opportunities ranked by estimated impact, with "why we think this" and "what would change our mind".
- Decision plans: metric, baseline window, target, follow-up date, notes.
- Automatic outcome readout on the follow-up date: before/after with seasonality-aware comparison and an honest uncertainty statement.
- Analyst answers are grounded in the same verified aggregates; responses cite evidence keys; evaluation suite (missing data, skew, refunds, partial sync).
- Email: weekly brief digest and outcome readouts (transactional email provider), with unsubscribe controls.
- **Verify:** golden-path steps 5–7 and 9 in CI with time travel; analyst eval suite runs in CI with a pass threshold; digest renders correctly in an email preview test.

### M5 — Billing that matches the product
- 14-day no-card trial that starts after the first healthy sync; trial-ending reminders.
- Checkout quantity derived from monitored locations on the server; add or remove locations with a Stripe proration preview, then confirmation.
- Single entitlement service: active / trialing / past_due (grace) / read-only / canceled, enforced on every paid endpoint and reflected in the UI.
- Dunning: failed payment → banner + email → grace → read-only; recovery restores access.
- Billing portal for invoices, payment method and cancellation; cancel keeps access until period end.
- LIVE mode remains a config gate behind a written go-live checklist; until then everything is Stripe TEST.
- **Verify:** Stripe test clocks drive trial-end, renewal, failed payment and cancellation in CI; journey steps 8 and 10 pass; an entitlement matrix test covers every state × paid endpoint.

### M6 — UI/UX quality and customer readiness
- First-run checklist (connect → select locations → first sync → first insight → first decision) that is always visible until it's done.
- Every page has designed loading, empty, error and stale-data states; no dead ends.
- One coherent app shell for signed-in users (nav, workspace switcher, data-health indicator) that is clearly separate from the public demo.
- Mobile (owners check on phones), keyboard navigation and screen readers: axe checks in Playwright on every journey page.
- Help center pages for connecting, data coverage, pricing, tax, invoices and cancellation; in-app "contact support".
- Data export (CSV) and workspace deletion with confirmation.
- Terms of Service and Privacy Policy pages (drafts, marked for legal review), consent captured at signup.
- Product analytics for the funnel above (privacy-respecting, no PII), plus error tracking in frontend and backend.
- **Verify:** an axe run reports zero serious violations; Lighthouse ≥ 90 on mobile for the public pages; a usability test with 3 people who've never seen the product (finding: ≤ 2 min, connection: unassisted).

### M7 — Pilot and go-live
- Staging that mirrors prod; Square production app review; Stripe LIVE account and tax settings; legal sign-off.
- One consenting pilot merchant runs the loop for 4 weeks; we measure the success metrics above.
- Go/no-go review against `docs/V013_TO_V1_PRODUCTION_GATES.md`.
- **Verify:** pilot merchant completes a real Checkout, receives an invoice, and later cancels successfully; data-trust metric holds every week.

## Status

| Milestone | Status | PRs | Notes |
|---|---|---|---|
| Infra checkpoints 0–4 | Done | #4 | CI, audits, prod config guard, webhook tests, rate limit |
| M1 Journey harness | Done | #23 | Mock Square, pipeline + contract tests, browser journey steps 2–7 in CI. Steps 8–10 arrive with M4/M5 |
| M2 Identity | Done | #26 | Clerk mode, owner/manager roles, invites, workspace deletion, route-inventory isolation test; journey passes against the real Clerk dev instance. CI needs the Clerk test secrets added |
| M3 Pipeline | Done | #27 | Checkpointed worker, no order cap, refunds, local days, reconnect/revocation, data health, Check against Square. Remaining: verify with a real Square Sandbox seller on staging (needs hosting) |
| M4 Insight loop | Done (pending merge) | M4 PR | Weekly brief with confidence + evidence, decisions with metric/location/follow-up, seasonal-aware outcome readouts, digest/outcome/trial emails with unsubscribe, 168-check analyst eval. P2: email outbox retries pending mail once Resend is configured (idempotency keys, no duplicates), preferences re-checked at send time, accurate counts, 422 for bad dates; schema follow-up proposed in `docs/EMAIL_OUTBOX_MIGRATION.md`. Remaining: Resend account to deliver email; owner interviews to tune what the brief prioritizes |
| M5 Billing | Done | #28 | One entitlement service; no-card trial after first sync; grace + read-only; proration preview/confirm; verified on Stripe test clocks. Trial-ending emails added in M4. Remaining: Stripe keys in CI secrets, a manual hosted-Checkout check |
| M6 UI/UX and readiness | Not started | | Needs legal review of drafts |
| M7 Pilot | Not started | | Needs pilot merchant, hosting, LIVE accounts |

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-11-22 | Square first; Toast out of scope for launch | Existing integration work and a single OAuth surface |
| 2026-11-22 | No causal-lift claims; outcomes reported as before/after with uncertainty | Owners make money decisions on these numbers |
| 2026-11-22 | Stack: Clerk (identity), Resend (email), Render + Neon Postgres (hosting), Sentry (errors) | Owner accepted recommendations; Clerk already supported by the backend OIDC path |
| 2026-11-22 | Customer validation runs alongside M4 (owner interviews + concierge pilot), see `docs/PILOT_TRUST_PLAN.md` | Prove the insights change real decisions before investing in billing polish |
| 2026-11-22 | Journey test signs up via the UI rather than seeding accounts | Tests the real signup path; no test-only backdoor endpoints |
| 2026-11-22 | Teams live in TableSignal (owner/manager), not Clerk Organizations | Keeps roles next to the data they protect and works with any OIDC provider |

## Working agreement
- Every PR names its milestone, keeps the golden-path journey green, and updates the Status table.
- No feature is "done" without a test that would fail if it broke, and without its designed empty, loading and error states.
- Nothing touches real merchant data or real money until the M7 go-live checklist passes.
