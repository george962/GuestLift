# TableSignal v0.12 — Product experience, signup, and billing design

**Decision record · 2026-11-12**

**This is an implementation specification, not a production certification.** Keep all preview order figures synthetic. Do not collect real merchant information, enable live payments, or advertise live integrations from these source files. The website UI is implemented as a portable v0.12 drop-in; the production connections and billing logic below remain to be implemented and independently tested.

## 1. Product direction — locked

TableSignal is the restaurant decision intelligence workspace: **Connect → Discover → Investigate → Decide → Track**.

Our customer promise is not "AI for restaurants." It is: **Know what matters. Know what to do.** An owner opens a recurring business review, sees prioritized changes, traces each finding to defensible data, chooses an action/test, and can later inspect the outcome. The existing guest, opportunity, AI analyst, and experiment capabilities are not discarded; they become stages of this workflow.

**Initial audience:** growing fast-casual restaurant groups and individual operators with meaningful sales/promotion activity. **First automated connector:** Square production OAuth when it passes security and reconciliation. Toast and other connectors remain planned, not promised. **Initial outcome:** promotion spending and repeat-guest questions, limited by source coverage; no unsupported incremental-profit claims.

The current v0.12 public homepage is a fictional demonstration of the *target experience*. It must not be presented as a live data product.

## 2. Commercial decisions for launch

| Question | Decision for implementation |
|---|---|
| Require sales calls before signup? | **No** for standard Square accounts. Self-service by default. Offer optional demos and assisted onboarding for special cases. |
| What is bought? | A subscription to monitor **specific provider-verified, eligible locations** and use TableSignal's core decision workflow. |
| What is the location price? | Provisional **$99 per selected monitored location per month**, one Growth plan. Validate before production publishing. |
| How is count verified? | Server fetches provider locations after OAuth; user cannot type a billing quantity. Server bills on chosen entitled location IDs. |
| Can a seller with seven locations select three? | **Yes.** That is not underreporting: only the three selected are synced, analyzed and billed. The other four remain visible as "Not monitored" with no included insights. |
| Can they analyze seven but pay for three? | **No.** All analytics, queues, jobs, AI and reporting must enforce entitlements by canonical location ID on the backend. |
| Is trial available? | **Proposed 14-day no-card trial**, triggered by first valid sync rather than initial account creation. During trial, monitor selected locations within rate/usage limits. No automatic charges. |
| When do they pay? | After seeing the first trustworthy business review (or trial before expiry), they explicitly approve the location list, terms, total and Stripe Checkout. No covert subscriptions. |
| Complex onboarding? | Offer optional booked call for multiple POS merchant accounts, non-Square integrations, identity mapping, migration, unusual location entities or custom integrations. |
| Can users upload customer data into public demo? | **No.** Public preview is isolated, fictional and requires no account. |

## 3. Proposed exact self-serve journey (v1.0 target)

1. **Public demo**: owner views a realistic sample weekly review and its evidence, without signing in or connecting anything.
2. **Create account**: work email, strong password or supported secure sign-in method, email verification, accept policies; create organization and owner role. Default empty workspace, never sample orders inside a private customer account.
3. **Tell us about the business**: name, type, primary goal, optional locations context **for personalization only**; this field does not control price.
4. **Connect Square**: click "Connect with Square," redirect to the official Square OAuth domain, request minimal approved read scopes, verify signed state/PKCE as supported, exchange token on server, encrypt credentials, never see or store owner passwords.
5. **Discover locations**: backend calls `GET /v2/locations`, scopes `MERCHANT_PROFILE_READ`, collects IDs/status/type/capabilities/name and tests supported data availability. Do not assume every ACTIVE Square object is a billable restaurant location (virtual/catering/administrative locations exist). Present **all discovered** locations and mark eligible, unavailable, or needs review.
6. **Choose monitored locations**: user selects which verified eligible locations to activate. Show "7 discovered / 6 eligible / 3 selected". The UI cannot supply arbitrary IDs or quantities. No auto-select all, and no auto-billing on discovery.
7. **Initial synchronization**: perform bounded backfill for **selected** locations, reconcile against documented source totals and surface missing identifiers, refunds and data limitations. If no useful data, clearly explain it and provide reconnect/support options; do not start the paid trial clock until agreed minimum health criteria succeed.
8. **First business review**: show evidence-grounded findings, identify known-guest coverage, ask the analyst and save a decision. Show explicit uncertainty and source status. Trial start/expiry visible.
9. **Subscription confirmation**: show selected location names and quantity, price per location, estimated subtotal, discounts if any, trial remaining, billing cadence and Stripe-calculated tax. Explicit button "Subscribe to X monitored locations" launches Stripe-hosted Checkout, never an embedded self-built card form.
10. **Verified activation**: server takes Stripe customer, subscription and subscription item quantity from signed/verified events and reconciles them to the internal selected entitlement. The browser redirect alone **never** activates an account. Receipt/invoice, billing portal and cancellation instructions available.
11. **Recurring use**: schedule monitored sync, freshness alerts, weekly review, investigations, saved experiment plans and subsequent outcome checks. Let owner manage team access and location selection with a visible billing impact.

No human call is required in the standard path. The owner should never need to upload CSVs to repeatedly refresh data.

## 4. Canonical commercial data model

- `organization` (tenant, owner, billing country, verification)
- `organization_membership` (role, verified identity)
- `provider_connection` (Square merchant ID, approved scopes, token storage reference, status, last verification)
- `provider_location` (connection + immutable Square location ID + status/type/capabilities)
- `canonical_location` and `location_mapping` (avoid charging twice for the same physical site connected by multiple providers; mapping changes require audit)
- `location_entitlement` (canonical ID, selected by, selected_at, state `trial|active|pending_add|pending_remove|inactive`, provider verification timestamp, no manual quantity)
- `source_sync_run` (per-location checkpoints, idempotency, reconciliation and freshness)
- `billing_account` (Stripe customer ID and organization)
- `billing_subscription` and `billing_subscription_item` (Stripe references, period, status, price ID, verified quantity, received webhook version)
- `billing_change_request` (explicit addition/removal, price preview, user authorization, idempotency key, effective date)
- `audit_event` (who selected/revoked access, billing changes, provider updates, admin actions)

**Invariant:** billable quantity = number of unique enabled, eligible *canonical locations* under the active subscribed entitlement. **Never** use the account profile's self-reported location count, a client-side total, or the raw number of Square locations as the Stripe quantity.

**Important subtlety:** some Square locations are virtual or administrative; and some restaurant groups have multiple Square merchant accounts. Only confirmed eligible, deliberately selected and actually monitored locations are billable. Distinct merchant IDs are not necessarily distinct physical locations. Never trust a frontend-provided `quantity` without checking authoritative entitlement state.

## 5. Location changes and invoice rules

- **New Square location detected**: show "New location available". No sync, analysis or charge until explicitly selected; then preview any proration and require confirmation.
- **Add during billing period**: require location entitlement check, show Stripe's proration preview and confirm before updating the subscription item quantity. Provision access only when verified billing state permits it.
- **Remove during period**: recommend scheduling downgrade at next renewal; keep monitoring through paid-through period unless owner explicitly requests earlier disconnection; show effective date and expected next invoice. Define refund/cancel policy before launch.
- **Square marks location inactive/closed**: notify owner, suspend further data collection as appropriate, offer move/replace/removal and avoid silently continuing to charge indefinitely. Define a bounded resolution policy and automatic renewal reduction only after customer notice, honoring billing terms.
- **Provider connection revoked/expired**: stop jobs safely, flag stale data, provide reconnect. Billing treatment must be visible and fair; recommend a documented grace period before charging for an unusable service. Do not expose raw credentials or fall back to another tenant's connection.
- **Multiple providers covering same physical restaurant**: owner reviews mapping; prevent duplicate `canonical_location` billing while preserving distinct data source IDs.
- **Unselected location appears in orders**: exclude its rows from analysis and AI context and block backfill/queue execution unless entitled. Never derive metrics across the full merchant just because OAuth can see them.
- **Payment fails**: Stripe webhook sets `past_due`; notify, provide portal and grace, then suspend paid functionality after policy-defined period. On recovery, reconcile rather than trust a client redirect.
- **Canceled**: confirm effective end date, stop future renewal, retain read-only access for contracted grace/retention period, provide export and deletion under published policy.
- **Trial expires without card**: no auto-charge; workspace becomes limited/read-only while inviting explicit checkout.
- **Stripe webhook duplicated/out-of-order**: verify signature and event identity, reconcile subscription state from Stripe API when necessary, keep billing and entitlements idempotent.

## 6. What exactly does $99 buy?

**One Growth plan**, per monitored location, containing the core recurring workflow:
- Supported live Square POS connection; automated scheduled order import, freshness and reconciliation status.
- Core sales/discount/location comparisons using verified definitions, with clear data caveats.
- Known-guest coverage, observed repeat behavior and cohorts when identifiers support it.
- Prioritized, explainable business findings and linked evidence.
- Read-only AI analyst over curated, scoped aggregates with defined fair-use limits and cost controls.
- Promotion-cost exploration, saved decision/test plans, and tracked follow-ups.
- Owner self-service billing portal, managed locations, cancellation and data export/delete controls.

**Not included / never imply**: guaranteed incremental profits, automatically deployed marketing campaigns, unlimited AI credits, loyalty points issuance, direct credit-card access, or access to unsupported providers. If locations lack guest identifiers, guest analysis may be limited.

## 7. Website scope for v0.12

Implemented in this package:
- Outcome-driven hero: "Know what matters. Know what to do."
- Interactive fictional weekly review with three switchable findings.
- Evidence, limitations, recommended test and tracking explanation for each.
- Five-stage workflow and pricing calculator for sample discovered locations.
- Self-service-vs-assisted onboarding explanation, transparent preview labels, honest FAQ.

**Pending for a genuinely publicly deployed v0.12:** domain, hosting, actual public URL, full current v0.11 source reconciliation, mobile cross-browser QA, analytics, working privacy-compliant early-access lead intake with spam protection/consent and business contact, and a successful production/static build. Until lead capture exists, do not render a dead "Join waitlist" button.

## 8. Readiness boundary

**v0.12:** Shareable product sample. No merchant live credentials or charges.

**v0.13:** Secure closed-pilot production candidate. Real integration and Stripe test cases pass on staging; every safety requirement is independently demonstrated with explicit consent before any limited real data. Do not pretend test billing is paid billing.

**v1.0:** Public commercial availability, only after real Stripe live and Square live end-to-end acceptance, tenant security review, compliance/legal coverage, self-service support, billing accuracy, source reconciliation and failure recovery pass. Owners can truly sign up, pay and use TableSignal on their own data.

## 9. Acceptance scenarios to automate

1. Square has seven locations, one virtual/ineligible; customer selects three physical. Checkout quantity is three, price is 3 × $99 monthly before tax, and only those three enter sync and analyst scopes.
2. Customer selects zero: no trial start and no checkout; explain the minimum one monitored location.
3. A customer tampers with the POST body to select an unrelated Square location or quantity 1 for three entitled locations: backend rejects; audit event recorded.
4. New fourth eligible Square location appears: no surprise bill until explicit add and proration confirmation.
5. Same physical location mapped through two POS connections: one canonical entitlement unless clearly distinct sites.
6. Trial clock starts after first successful verified sync, not signup, OAuth callback or an empty source.
7. Checkout completes but webhook is missing: no paid activation; transparent pending state until server reconciliation.
8. Duplicate/out-of-order webhooks do not create duplicate subscriptions or reverse a newer state.
9. Payment failure/grace/recovery, changes mid-cycle, cancellation and refunds are tested with Stripe's test clocks/fixtures.
10. Every account and role is isolated; cross-tenant IDs and AI evidence cannot leak.
11. Revoke OAuth mid-sync and disconnect: stop future imports, rotate/revoke tokens and show source status honestly.
12. Real private source has unknown guest IDs or promo assignment: analyst explains limitations, no fictional profit proof.
13. Owner can recover account, export eligible data, revoke access, delete according to policy, and get support without contacting a developer.
14. Accessibility/mobile, privacy/terms, email verification, fraud/rate-limit, password reset and error paths pass in production-like hosting.

## References

- Square locations: https://developer.squareup.com/reference/square/locations/list-locations
- Square OAuth: https://developer.squareup.com/reference/square/o-auth-api
- Stripe subscription update/proration: https://docs.stripe.com/api/subscriptions/update
