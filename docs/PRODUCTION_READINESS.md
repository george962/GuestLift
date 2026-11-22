# TableSignal production readiness — evidence log

**Version:** v0.13.0 local Sandbox integration preview. **Last reviewed:** 2026-11-22. **Launch decision: BLOCKED.**

This is the **status board** for [the complete v0.13→v1.0 gates](V013_TO_V1_PRODUCTION_GATES.md). Do not mark a gate passed on code presence alone. Each gate needs a linked CI run, recorded test case or evidence artifact, accountable owner and sign-off date.

| Gate | Status | Verified evidence to collect | Release owner |
|---|---|---|---|
| A. Source and CI | NOT VERIFIED | CI runs Node/TS/Next/Python/browser + secret scan on exact commit; branch protections, dependency policy, rollback | Engineering |
| B. Identity and tenancy | BLOCKED | Hosted email verification/recovery, org roles, adversarial isolation tests, secret manager, privacy and legal review | Security/engineering |
| C. Square production | BLOCKED | Consented production OAuth, token lifecycle, webhook/sync resilience, reconciliation against source exports | Integrations |
| D. AI evidence | NOT VERIFIED | Tenant-scoped sanitized aggregates, prompt-injection tests, evidence and rate-limit evaluations | Data/ML |
| E. Location billing | BLOCKED | Server-owned eligible location selection → entitlements → location-scoped ingestion → Stripe quantity/webhook/proration tests | Billing |
| F. Customer usability | NOT VERIFIED | Uncoached onboarding and accessible mobile E2E with at least one qualified pilot operator | Product |
| G. Operational launch | BLOCKED | HTTPS staging, migrations, backup/restore, monitoring/alerts, incident/support and an authorized LIVE billing test | Operations |

## Important verified implementation limitations

- The `location_billing_rules.py` class and quote tests are **pure domain code**, not an authenticated API or entitlement service. Do not expose its output as a real Stripe billing quantity.
- Stripe TEST checkout still uses **`quantity: 1` by default** for legacy local tests. When the v0.13 Sandbox location flag is enabled, checkout derives quantity from saved provider-verified Sandbox locations and verifies quantity/digest during Stripe TEST reconciliation. This is not a production subscription entitlement, a real merchant location mapping, live invoice or proration implementation.
- Current `local_auth.py` explicitly documents **local development only** and lacks production email verification/recovery and operational access controls.
- `frontend/lib/supabase-client.ts` is a **compatibility alias** for `local-auth.ts`, not a second active Supabase identity provider. Remove the alias only after checking all imports and browser flows.
- `backend/app/dev_admin.py` and `dev_reset_password.py` are **local console utilities**, not exposed admin HTTP endpoints. Reset CLI is opt-in; protect workstation and backend access. Separately, `POST /api/reset` was a publicly addressable local-demo HTTP reset and is now **disabled unless `TABLESIGNAL_ENABLE_DEMO_RESET=1`**. Do not set that flag on any hosted deployment.
- Other demo imports/uploads, campaigns, fixture-only metrics and test-account endpoints are not authenticated production SaaS services. They require explicit isolation or removal before deployment.
- Existing sample reports and test counts cannot establish Square production authorization, financial completeness, causal profit, secure hosting or commercial readiness.

## Next implementation sequence (must follow in this order)

1. **Clean source & tests:** merge reviewed baseline PR, ensure CI green, inspect dependency vulnerabilities, adopt branch protection + CODEOWNERS, set release tags, create staging environment isolated from development.
2. **Identity first:** choose a supported production auth provider or implement audited production auth with verified email, reliable recovery, session/CSRF protections, organization roles and complete tenant isolation tests. Keep sample mode separate.
3. **Square ingestion:** implement approved production OAuth, per-merchant location discovery and secure token lifecycle; durable scheduled data refresh, backfills, refunds/discount reconciliation, health alerts, consent, delete and revoke paths.
4. **Server-backed entitlements:** persist eligible canonical locations authorized per workspace; enforce selected locations at ingestion, dashboard, exports and AI tool boundaries. Add authenticated quote/confirm endpoints and reconcile Stripe TEST line-item quantities **from these persisted entitlements**.
5. **TEST to LIVE billing:** validate every subscription change, signature, webhook retry, tax, trial, invoice, failure and cancellation. Enable Stripe LIVE only behind a separate reviewed deployment and explicit owner approval.
6. **Pilot evidence:** at least one consented operator completes Detect → Investigate → Decide → Track repeatedly and can describe the value; support and privacy operations exercised.

## Evidence record template

`Gate | criterion | owner | exact commit | test/screenshot/log link | date | pass/fail | reviewer | remaining risks`

A checked box is not evidence. Do not promote this preview to production or ingest actual merchant data until **all applicable** gates are PASS with owner sign-off.

## v0.13 Sandbox integration checkpoint (2026-11-22)

- [ ] **Code review:** feature-flagged Square Sandbox owner selection is added; local SQL table `sandbox_monitored_locations` stores selected IDs; no actual merchant data or LIVE Stripe enabled.
- [ ] **Automated verification:** CI passes all backend + frontend tests, including negative cases for unselected/virtual/foreign locations, tenant isolation and Stripe quantity mismatch.
- [ ] **Live test evidence:** operator authorizes an actual Square Sandbox application and discovers active physical locations; selects a subset; only those locations are synced into scoped analytics.
- [ ] **Stripe TEST evidence:** test Checkout line-item quantity equals selected locations, signed webhook and server reconciliation preserve that quantity and subscription metadata; test cancellation and reconnect behavior.
- [ ] **Outstanding production blockers:** auth/email, operational tenant roles, resilient provider sync, reconciled refunds, Alembic migrations, HTTPS hosting, webhook event order/proration, incident/support processes, real Square OAuth and data protection remain OPEN.

**Do not mark Gate E passed:** this milestone verifies only local Sandbox selection-to-test-billing wiring. Changing monitored locations while subscribed is intentionally blocked, not prorated. Never deploy the current demo endpoints to a public network.
