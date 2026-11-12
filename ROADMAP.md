# TableSignal (working name) — product roadmap

Updated 2026-11-12. Built on the existing GitHub project `george962/GuestLift`.

## North star

Restaurant operators open a trusted workspace, understand sales and return visits, evaluate promotion economics, and ask a transparent analyst what to investigate next. A value-creating customer workflow precedes more connectors and AI bells and whistles.

### v0.6 — Unified website and account journey (delivered in source)

- [x] Plain-language landing page and non-technical value proposition
- [x] Automatically moving, pauseable, interactive sample product tour
- [x] Reduced-motion support and mobile CSS
- [x] Single clear `/start` entry point with public vs account paths
- [x] Separate sign-up, sign-in, forgot/reset password pages wired to Supabase
- [x] Restaurant profile onboarding and settings
- [x] Dedicated subscription and Stripe TEST controls
- [x] Public pricing and help/FAQ pages with honest availability
- [x] Four core operator workspace tabs, utility links moved into settings/data/billing
- [x] Preserve synthetic source adapters, campaign engine, and evidence-linked analyst
- [x] Run existing unit tests and TSX parsing
- [ ] Run full Next.js production/static builds and visual accessibility QA in Mac Docker
- [ ] Validate responsive marketing and account flows in actual browser
- [ ] Decide final business name after domain, trademark and usage diligence
- [ ] Recruit 1–3 restaurant operators for five-minute product walkthroughs

### v0.7 — True customer decision intelligence (next)

- [ ] Reliable 30/60/90 day cohorts with consistent observation periods and guest-ID coverage
- [ ] Segments such as observed repeat, recently active and potentially lapsed (only from stable IDs)
- [ ] Practical insights linked to campaign and location records
- [ ] Written operator interviews identifying a high-value repeat workflow
- [ ] AI model evaluated on evidence quality, uncertainty, refusal of unsupported requests

### v0.8 — Secure pilot foundation (before real merchant data)

- [ ] Production host/backend authentication, tenant authorization and policy review
- [ ] Per-merchant storage boundaries and least-privilege access
- [ ] Encryption, retention, deletion, audit events and backup/restore
- [ ] Protected ingestion; handle malformed data, retries and amendment/upsert/reconciliation
- [ ] Authorized Square Sandbox OAuth test integration and Toast partner feasibility
- [ ] Account recovery flows, billing lifecycle, plan limits, location metering, taxes, refunds, cancellations
- [ ] Published Privacy Policy, Terms, support contact and incident process reviewed by qualified parties
- [ ] Security review, staging tests and limited explicitly approved merchant pilot

### Later (only with evidence)

- Randomized controlled campaign tests and incremental contribution measurement
- Automated recommendations and campaign execution with user approval, budget and guardrails
- Multiple merchant teams, granular roles, multi-location rollups, integrations with loyalty platforms
- Operator admin dashboard and internal staff tooling

**Guardrails:** No real client uploads to the public sandbox. No claim of paid production service. No causal lift without valid test design. No automatic sensitive-data transmission to an LLM.
