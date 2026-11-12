# GuestLift v0.5 — Operator SaaS Foundation

Built on the existing v0.4 campaign and POS engineering prototype. No source adapters or historic tests were deleted.

## Added
- Three-link public navigation and interactive sales/customer/promotion hero.
- One operator workspace with overview, customers, campaigns, analyst, data sources, account and billing.
- Transparent rule-based patterns, evidence-backed natural language question handling, and optional server-only Responses API explanation.
- Supabase sign-up/sign-in UI and verified bearer auth dependency for account APIs (disabled by default).
- Per-owner synthetic workspace tables and isolated queries; editable business profile.
- Stripe TEST recurring subscription Checkout, portal, signed webhook event persistence, subscription entitlement gating.
- Public price proposal page, account page, business launch roadmap, service safety limits.
- Tests covering tenancy isolation, authorization, plan checks and metric parity.

## Does NOT add
- Merchant-data uploads, production auth certification, live billing, registered company subscriptions, multi-owner restaurant roles, actual restaurant profit lift, broad audience segmentation or autonomous agents.
- Real-time POS integrations; existing synthetic Toast/Square sample inputs remain.

## Test and build status
- Python: 23 tests passed during release preparation.
- JavaScript: 23 tests passed during release preparation.
- TSX/TS: syntax transpilation checked across 17 source files.
- Full Next.js production build is **not verified** in this environment because npm packages cannot be downloaded here. Verify with `docker compose up --build -d` on Mac before publishing.
