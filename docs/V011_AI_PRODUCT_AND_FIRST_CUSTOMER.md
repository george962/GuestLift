# TableSignal v0.11 — Evidence Intelligence and First Customer Readiness

**Release status: Local development release candidate. NOT production-ready.**

This release implements the product's first genuine read-only LLM analyst. It does not yet authorize live merchants or accept live Stripe charges. The user must configure the OpenAI API key and model on the backend. Do not expose this app to the public Internet or import real merchant/customer data.

## Product promise

> TableSignal helps restaurant operators understand who comes back, where discount spending may be wasteful, and what to investigate or test next.

The distinctive experience is **Connect → Understand → Ask → Decide → Track**.

1. Connect a Square **Sandbox** seller to test the approved integration flow.
2. Synchronize orders for that authenticated workspace. Verify the source and identity coverage.
3. Open `/analyst` and inspect the **evidence graph**: orders → observed order value, orders → identity coverage → recognized guests → repeat buyers, and discounts → saved decisions.
4. Ask natural-language questions through the OpenAI Responses API; it receives **server-generated aggregate statistics** and user-typed questions, never automatically forwards raw transaction/customer IDs, and cannot run arbitrary SQL or change restaurant data. `store=False` is set on every request.
5. Open `/opportunities` to model a percentage/fixed/no-offer scenario with disclosed assumptions.
6. Save an experiment in `/experiments`; revisit later and change its tracking status.

The model must not claim causal lift, forecast lost revenue, invent customer identity, claim a campaign was sent, or pretend an unavailable connection works.

## Free versus Growth — proposed commercial model

| Capability | Free Explore | Growth ($99/location/month, **not yet available live**) |
|---|---|---|
| Interactive sample restaurant | Yes | Yes |
| Live authorized POS connection | No | Target feature, not launched |
| Scheduled sync, freshness and health monitoring | No | Target feature, not launched |
| Individual restaurant's verified aggregates and evidence graph | No | Yes after supported integration |
| Read-only natural-language model Q&A | Sample, deterministic | Yes, when backend model is configured and subscription verified |
| Save experiment drafts | No in public demo | Yes |
| Send messages, deploy campaigns, guaranteed uplift | No | No |

**Current local reality:** Square Sandbox only, Stripe test billing only (the configured test Price may still be $149), proposed live Growth price $99 per restaurant location. Existing Sandbox purchases do not authorize real charges.

## Why live payments and live merchant connections are still blocked

The project cannot be represented to a first real customer as production-ready until the following evidence exists. These are deployment and security deliverables, not merely code toggles.

### 1. Production identity/security
- Independent secure hosted frontend/backend with HTTPS, managed database, restricted networks, backups/recovery tests, monitored logs and alerts.
- Remove or fully isolate all publicly writable demo endpoints. Today local demo import/reset APIs are unauthenticated; this must not be exposed on the Internet.
- Replace developer-local sessions with production account identity: email verification/recovery, secure cookie domain/origin, short-lived or rotated sessions, MFA for admins, organization roles, workspace authorization tests, robust distributed rate-limiting and audit events.
- Migrations with rollback; scoped encryption at rest/key rotation; secrets manager; tested incident-response and deletion flows.
- Confirm terms of service, privacy policy, DPA/subprocessor disclosures, retention window, customer consent and data processing scope with qualified advisers.

### 2. Square production seller OAuth
- Register live Square app, approved redirect URLs, least-privilege scopes and authorization policies. Do not collect Square usernames/passwords or seller personal access tokens.
- Build a production-only Square adapter with per-merchant production connection records and database migrations; ensure no mixing of sandbox/real data.
- Authorize/revoke real seller, refresh tokens, handle expiry and auth failures, verify webhooks/signatures, implement durable idempotent incremental synchronization, retries/checkpoints, payment/refund reconciliation, volume pagination, and data freshness alerts.
- Validate all workflows with a consenting pilot restaurant in secure staging, with a signed data use/processing agreement.
- Toast is **not** a generic "Sign in with Toast" provider for us: read-only API access and the broader partner program are subject to eligibility/approval. Do not advertise Toast as connected until contracts and access are confirmed.

### 3. Stripe live subscription billing
- Keep test and live credentials in separate environments; move off test keys only in a dedicated reviewed deployment.
- Create a $99/location/month live recurring Price, verify tax/receipts/invoices and location counts, webhook signature verification and idempotent subscription state reconciliation; test failed payment, cancellation, grace periods, refunds, portal access, and customer support.
- Make sure paid entitlement is derived from Stripe verified state, not a redirect URL or client boolean.
- Do not flip live billing flags in a localhost deployment.

### 4. LLM privacy, quality and economics
- Get explicit merchant authorization for any aggregate data sent to a model provider; disclose subprocessors and retention.
- Set supported model and credentials on backend only; OpenAI Responses calls explicitly set `store=False` (this does not remove all provider-side abuse-monitoring retention obligations).
- Add durable rate limits/quotas, usage spending caps, request-size limits, privacy filters for typed questions, and a full evaluation suite for false claims, prompt injection, cross-tenant access, and unsupported recommendations.
- Audit and clarify metrics: current sales are observed order value, not reconciled net revenue; anonymous guests prevent complete retention measurement.

### First customer acceptance scenario
1. Customer creates **verified** account and consents to data processing.
2. Customer authorizes Square on Square's official domain; returning to TableSignal shows seller identity, permissions and a valid source-health status.
3. Historical and subsequent orders sync automatically and match POS reports to preagreed tolerance; missing customer identity is visible.
4. Analyst connects metrics using evidence; unsupported claims are refused; no other restaurant's data is accessible.
5. Customer models and saves a return-visit experiment; follow-up remains available after logout/re-login/redeploy.
6. Customer receives a clear price and tax disclosure, completes a *real* hosted Stripe payment (with their consent), sees confirmation, has a billing portal and receives invoice/receipt; cancellation updates access correctly.
7. Customer can revoke the POS connection, export/delete eligible data, contact support, and receive an incident notification under the agreed policy.

**Go/no-go:** Do not accept the first real merchant's live data or collect real subscription payments until every applicable prerequisite has been implemented, reviewed, and proven by actual staging/production acceptance tests.

## References checked in November 2026
- Square OAuth API: https://developer.squareup.com/reference/square/o-auth-api
- Toast integration partner process: https://doc.toasttab.com/doc/devguide/integrationDevProcess.html
- OpenAI Responses API (use `store: false`): https://developers.openai.com/api/docs/guides/migrate-to-responses

## Verification summary

See [V011_TEST_REPORT.md](V011_TEST_REPORT.md). Application logic and test simulations passed locally. Full Next.js build, real model calls, Square live and Stripe live still need independent deployment testing.
