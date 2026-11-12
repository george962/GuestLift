# TableSignal — Build and launch roadmap

**As of November 12, 2026: v0.8 local-account development release.**

## Product promise

Help restaurant operators understand recorded sales, identifiable returning customers, promotion spending, and questions worth investigating. Don't claim a profit lift based on observational promotion redemptions.

## Completed synthetic demo foundation

- [x] v0.1–v0.3: Toast-shaped CSV and Square-shaped JSON adapters; canonical orders; source validation, local Postgres/FastAPI, browser demo.
- [x] v0.4: Campaign and redemption modeling, traceable recorded coupon reports, synthetic customer aliases, descriptive finance metrics.
- [x] v0.5: Operator workspace, customer patterns and evidence-backed analyst; Stripe **test-mode** subscription API foundation.
- [x] v0.6–v0.7: Clearer animated marketing website, public product/pricing, account pages, guided restaurant onboarding.
- [x] v0.8: Local PostgreSQL authentication without Supabase; Argon2id password hashing, DB-backed revocable sessions, HttpOnly cookie, CSRF and origin checks, independent seeded workspaces, settings and password change, integration and isolation tests.
- [ ] Verify full Docker/Next.js build and manual browser sign-in/checkout on the developer's Mac.

## Immediate acceptance milestone — v0.8 local SaaS workflow

1. Install updated files into the local project and run all tests.
2. Open `/sign-up`, create developer account A, finish `/onboarding`, and change restaurant profile.
3. Restart containers and confirm A remains signed in and data persists.
4. Sign out and sign back in; change password and confirm old password fails.
5. Register account B; verify B's workspace is independent from A.
6. Optionally configure Stripe **test mode** and validate signed webhook status before granting a Growth entitlement.

**Done only after** a human verifies the live local frontend experience, not simply passing source tests.

## Next steps, in priority order

### v0.9 — Pilot-value validation

- Talk to 3–5 restaurant owners or multi-location operators. Ask whether customer retention, promotion performance, or labor/menu questions are highest priority.
- Build a concise recurring operator dashboard, not more disconnected pages.
- Improve insight accuracy, explainable trend comparisons, customer coverage warnings, and transparent campaign economics.
- Document onboarding friction and willingness to pay before setting final pricing.

### Production readiness (separate, substantial milestone)

- Build a separately secured hosted API, remove or isolate unauthenticated demo routes, migrate from local Docker PostgreSQL to a managed server with backups and formal schema migrations.
- Add verified email ownership, production account recovery, credential/session rotation, device and team management, persistent rate limiting, event auditing, TLS-only cookies and deployment monitoring.
- Implement permissions and tenant-isolation tests under real hostile traffic, data retention/deletion, incident procedures, and vendor approvals before accepting real merchant transactions.
- Validate live Toast/Square export semantics and correct-order/refund updates; add legitimate merchant OAuth/integration process.
- Configure Stripe live billing only after tax, legal, pricing, refund, customer-support and security reviews; webhooks should reconcile missed/out-of-order events.
- Evaluate AI privacy/usage quotas and enforce read-only metric grounding.

## Working rules

- Build and test **one clear operator workflow at a time**.
- Keep synthetic demo and real merchant records strictly separate.
- Never call a test-mode checkout a live subscription or an observed promotion association incremental ROI.
- Keep features usable on local Docker before paying for hosting.
- Update acceptance tests and documentation with every release.
