# TableSignal / GuestLift — Current roadmap

**Status as of November 12, 2026:** v0.7 animated SaaS experience prototype, built on the original GuestLift data and campaign engines. This replaces the older demo milestones as the current plan; their implementation and limitations remain documented in `docs/IMPLEMENTATION_STATUS.md`.

## Product promise

A restaurant operator should be able to understand customer repeat behavior, measured promotion costs, and significant differences between locations in a single workspace, then ask evidence-backed questions. **We do not claim sales attribution equals incremental profit.**

## Completed in the source release

- [x] M0–M5: synthetic source adapters, normalized orders, PostgreSQL demonstration, browser import, campaign CSV/redemption matching, finance and customer analytics.
- [x] v0.5: optional Supabase identity foundation, owner-scoped synthetic account workspace, proposed pricing, Stripe **test-only** subscription workflow and read-only analyst.
- [x] v0.6: simpler four-task workspace, account/billing pages, early homepage motion tour.
- [x] **v0.7:** longer animated homepage with meaningful interactions, interactive analyst, four-step product story, customer/account journey, more polished sign-in / sign-up experience, account-aware navigation, direct pricing-to-billing route, biller configuration status and tests.
- [x] v0.7: 25 backend / 29 frontend source tests pass.

## Acceptance still outstanding

- [ ] Run full Next.js production build and static export on Mac with npm registry access.
- [ ] Manually verify responsive navigation, scroll reveal, reduced motion and account forms in an actual browser.
- [ ] Configure a Supabase test project and complete email confirmation / reset flows end-to-end.
- [ ] Configure Stripe test product/price and webhook; perform successful checkout and cancellation, ensure entitlement follows verified event only.
- [ ] Publish the synthetic-only frontend and verify all public routes. Do **not** publish legacy API.
- [ ] Test product value proposition with at least one independent restaurant operator.
- [ ] Verify working name availability before committing to a domain or trademark.

## Next milestone: v0.8 — Secure merchant pilot architecture

**Do this before charging live or receiving real merchant data.**

1. Isolate all unauthenticated demo routes from production API deployment, and secure each authenticated endpoint by tenant/role.
2. Add per-merchant authorized data import, protected storage, deletion and backup policies; strengthen transactional schema, migrations and reconciliation.
3. Test real Square Sandbox authorization; investigate Toast partner requirements; do not claim a live connection based on fixtures.
4. Implement robust subscription lifecycle: invoice failure/dunning, subscription reconciliation, location-based quantity, cancellation, tax and plan limits.
5. Add organization membership/invites, service roles, audit logs, rate limits, monitoring and recovery procedures.
6. Publish and review legal/privacy/support policies before a limited approved pilot.
7. Validate at least one problem a restaurant operator will actually pay to solve and update pricing hypothesis.

## After a pilot: evidence-based AI and retention

- Customer cohorts and repeat/at-risk segments with stable identifiers and known coverage limitations.
- Restaurant-specific business context (hours, locations, menu, promotion eligibility, verified costs).
- Read-only AI research using approved analytics APIs and citations, never fabricated metrics.
- Controlled campaign experimentation and margin-aware incremental outcomes.
- More POS/loyalty integrations only when demonstrated customer value justifies them.

**Working rule:** One customer journey first; technical tools available in secondary flows. No live billing or sensitive uploads into the prototype. Update this file after independently completing the unfinished checks.
