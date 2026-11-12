# v0.7 — Longer animated homepage and real test-account journey

## Added

- Scroll-responsive homepage reveal, looping capability ticker, hero ambient motion, hover product cards, animated figures, interactive source-to-insight stages, verified analyst question cards, responsive sections, reduced-motion support.
- Account creation/authorization flow with password visibility and safe redirects from proposed Growth plan to Billing, improved account overview and account-aware header.
- Stripe test checkout CTA from the account Billing page and test configuration status API (`GET /api/saas/config`) with no credentials or customer data exposed.
- New regression checks for account routes, payment mode gating, motion preferences and source-driven metric use.

## Not included

- Live Stripe charges, actual merchant subscriptions, secured production API, real Toast/Square merchant connections, PCI/DPA reviews, production-grade account lifecycle, actual measured campaign ROI, or autonomous AI actions.

## Verification

- 25 backend pytest passes; 29 Node tests pass; TS/TSX syntax parser clean.
- Full Next.js production compilation / live visual QA requires Mac/npm registry availability.
