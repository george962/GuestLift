# TableSignal production launch gates — v0.13 and v1.0

**The point of v1.0 is not another polished demo. It's verified public commercial operation.** All applicable gates below require test evidence, an owner and an explicit pass/fail decision before enabling real merchant onboarding and billing.

## Release definitions

| Stage | Public product | Merchant data | Money | Required evidence |
|---|---|---|---|---|
| v0.12 | Marketing/interactive fictional demo; working lead collection only once hosted securely | No real private merchant data | No real charges | Product demo QA, responsive/a11y checks, clear non-production labels, lead intake validation |
| v0.13 | Secure closed-pilot candidate | Controlled, consented, verified pilot data only after security gates | Stripe TEST only unless separately approved pilot policy | Signed pilot scope, production-like staging, red-team and isolation tests, OAuth, reconciliation, operations |
| v1.0 | Public self-service launch | Real authorized owners and approved supported integrations | Stripe LIVE in reviewed deployment | All commercial and operational gates green; end-to-end real signup→data→decision→purchase→cancel |

## Gate A — current source and architecture
- [ ] Reconcile v0.11 Mac workspace with `george962/GuestLift` main, which as inspected on 2026-11-12 reports v0.10. Verify full file inventory, tests and migrations before applying website updates.
- [ ] Source has a protected release branch with review, CI, secret scanning, pinned dependency policy and rollback artifacts.
- [ ] Full TypeScript compilation, Next.js production build, backend tests, browser E2E and security regression pass on the exact deployed commit.
- [ ] Deployed dev/staging/prod use separate secrets, databases, Square apps, Stripe accounts and data.

## Gate B — hosted identity, authorization and data safety
- [ ] HTTPS, managed DB, backups and restore test, secret manager, encryption at rest/rotation, restricted database/Redis access, monitored jobs and errors.
- [ ] Production authentication: verified email, password reset, session and CSRF protections, optional MFA/admin MFA, managed roles, organization/account boundaries, audited admin actions.
- [ ] Test cross-tenant isolation on every API, joins, exports, queue jobs, model input and SQL query. Row-level policy as appropriate.
- [ ] Disable or isolate all insecure dev/demo/reset/upload endpoints. No production secrets or customer data in a public repo or client bundle.
- [ ] Terms, privacy, vendor/subprocessor disclosures, consent, data retention and deletion/export, security/support contacts and incident response reviewed before real onboarding.

## Gate C — real POS operations
- [ ] Square production app/OAuth permissions, callback/state/refresh/revoke, least scopes, encrypted tokens and auth health verified with consenting merchants.
- [ ] Server-side Square `ListLocations` discovery, eligibility rules and canonical per-location entitlement enforced everywhere.
- [ ] Backfills, durable scheduled incremental sync, retries, 429 handling, pagination, checkpointing and idempotency tested. Webhook signature/ordering handling covered where webhooks are used.
- [ ] Payment, refunds, tax/tips and discount arithmetic reconciled against source reports; gaps displayed, not silently counted as net revenue.
- [ ] Source health and alerting, maintenance, credential expiry/revocation, manual re-sync controls and out-of-data behavior tested.

## Gate D — AI/analysis reliability
- [ ] Only provider-authorized, tenant-scoped aggregates sent to model after consent; no unreviewed raw customer identifiers, transcripts or secrets.
- [ ] Input prompt-injection and untrusted source content defenses; strict tool/query restrictions, rate limits, quotas and budget caps.
- [ ] Evidence graph grounded in validated SQL calculations and source coverage; AI does not invent causal lift or claim execution of unrun campaigns.
- [ ] Run evaluation suite on missing IDs, skewed cohorts, promotion attribution, known costs, refunds, incomplete syncs and sample/real separation.
- [ ] Durable decision history, annotations, experiment plans and follow-up outcomes persist through sign-out, redeploy and source reconnection.

## Gate E — location metering and Stripe LIVE
- [ ] Server independently verifies merchant/location IDs and eligibility; UI cannot dictate Stripe item quantity.
- [ ] Selected monitored locations map 1-to-1 to unique canonical entitlements and are the only locations ingested/analyzed.
- [ ] Stripe Checkout LIVE price, tax, receipts, billing portal, email communication and trial policy reviewed.
- [ ] Signed webhook processing idempotent; subscription access from verified backend state, not redirect/query params.
- [ ] Preview/confirm prorations, add/remove locations, downgrade at renewal, trial expiration/no-card, failed payment, recovery, cancellation, dispute/refund and duplicate event paths tested.
- [ ] Support owner can reconcile a billing complaint with provider location and Stripe event audit trail.

## Gate F — actual small-business usability
- [ ] At least one person unfamiliar with the app reaches the sample finding within two minutes without coaching.
- [ ] An eligible Square test seller finishes secure signup, connection, location selection, first sync and useful review without a call.
- [ ] Multi-location count is intelligible, including ineligible and unmonitored stores; pricing shows exact locations and quantity before checkout.
- [ ] Payment and plan can be managed and canceled independently; password recovery, reconnect, settings, data deletion, help and privacy controls work.
- [ ] Mobile, keyboard, screen readers, loading/error/empty states, email delivery and confirmation pages checked.

## Gate G — operational launch
- [ ] Support inbox and clear SLA/response expectations, owner escalation and incident process.
- [ ] Status, logging, alerts, uptime and cost monitors; rollback test and backups restore exercise.
- [ ] Customer-facing help on connecting, missing data, known-guest coverage, prices, tax, invoices, and cancellation.
- [ ] Pilot success criteria: real owner repeatedly completes Detect→Investigate→Decide→Track and can independently explain its value.
- [ ] Owners approve a limited rollout and complete one real authorized live Checkout, later show invoice, entitlement and cancellation functioning correctly before opening broad signup.

## Do not expand scope to v1.0 prematurely

Non-gates for first commercial launch: automated campaign sends, Toast integration when not approved, full labor/inventory integration, automated intervention without owner consent, enterprise SSO, custom analytics consulting, and multi-tier pricing. Keep roadmap concentrated on reliable self-service and a repeatable weekly decision workflow.
