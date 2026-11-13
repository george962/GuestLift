# Production-readiness gate — NOT complete in v0.9

This package is **production-oriented** in design, but **not production-ready** for real restaurant/consumer data or paying subscribers. The following issues are release blockers:

- [ ] **Securely hosted infrastructure:** HTTPS and `Secure` cookies, authenticated backend separated from publicly reachable legacy fixture/reset endpoints, traffic isolation, security headers, backups/restore drills, operational runbooks, logging/monitoring, rate limits and abuse controls.
- [ ] **Formal migrations & workspace data ownership:** Replace one-owner development model with proper organizations/roles, row-level authorization and audit trails, foreign keys, repeatable schema migrations, deleted-account flow, retention/deletion requests and encrypted backups.
- [ ] **Merchant integration authorization:** Square production OAuth with HTTPS redirect and verified scopes; secret rotation, token refresh/revocation webhooks and reauthorization UX. Toast vendor onboarding/access must be independently approved. Never ask customers for their personal tokens or Square account passwords.
- [ ] **Financial correctness:** Reconcile orders with payment captures, settlement status, refunds/returns, tax/tip/service-charge semantics, reporting business date and currency, idempotent changes, late-arriving corrections, and account-specific POS definitions.
- [ ] **Reliable ingestion:** durable job queue, bounded window/cursors, retries with backoff, background scheduling, alerting, webhook verification and dead-letter investigation, accurate completeness diagnostics, a multi-year historical import policy.
- [ ] **Privacy and AI:** real merchant agreements/consent, data classification, PII minimization, safeguards on model inputs/outputs, model/vendor agreements, valid customer identity resolution, monitoring and AI cost limits; distinguish descriptive analysis from experimental causal lift.
- [ ] **Production billing:** Stripe live-mode onboarding, subscription cancellation/proration and invoice recovery, webhook ordering/event replay safeguards, price/quantity verification, tax obligations, customer support contact, refund/terms/privacy policies and monitoring. Current code is strictly Stripe test only.
- [ ] **Operational readiness:** test the complete flow with a consenting Sandbox seller, verify vendor API behavior against official docs, conduct security penetration review, accessibility/mobile QA and prospective operator usability test.
- [ ] **Business validation:** at least one potential restaurant operator should confirm they would pay for the actual workflow, not just a presentation. $149/location/month and onboarding inclusion are unvalidated hypotheses.

## v0.9 acceptance criteria

1. From existing v0.8 Docker volume, add v0.9 tables without deleting accounts.
2. Sign up account A; its private dashboard shows an **empty state** and no sample sales.
3. Set Square Sandbox env token and connect A's seller; `GET /locations` validates ownership.
4. Use Square API Explorer or the optional `app.dev_seed_square` utility to create paid **Sandbox** orders, then sync and confirm the dashboard changes from zero to imported actual test records.
5. Repeat sync; no duplicate orders. Change a Square test order and verify the update is reflected when supported.
6. Register account B. It has zero orders and cannot attach the same seller or access A's data.
7. Disconnect A; local Sandbox orders and stored OAuth credentials (if any) are deleted. No credentials appear in logs or JSON output.
8. Optional: complete Stripe **test-mode** checkout and webhook, verify the analyst gate, then cancel and confirm entitlement is revoked.
9. Docker/Next.js production build, all Python/JS/TypeScript tests and UI/mobile review pass on Mac. No real merchant/customer files involved.

**Status:** unit/API tests were run with mocked Square. Real live calls to the external Square Sandbox and Stripe test checkout still require the user's developer credentials and testing, which were unavailable in the build environment. Next.js dependency install also requires local npm/Docker access.
