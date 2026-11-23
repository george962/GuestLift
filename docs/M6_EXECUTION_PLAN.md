# M6 customer-readiness execution plan

Status: step 1 in progress. M4 implementation and P0–P3 engineering hardening were merged through PRs #29–#32. Hosted pilot/production verification is separate.

The sequence below follows `docs/PRODUCT_PLAN.md`. Each stage gets its own PR, preserves the golden-path Playwright journey and updates the product status table.

## Step 1 — Guided first run (current PR)
- Always show one compact, accessible checklist on signed-in app pages until a decision is saved.
- Derive Connect, eligible monitored locations, first completed sync, verified weekly brief and first saved decision from authenticated workspace endpoints; no manually ticked boxes.
- Do not treat a missing/stale/partial sync as a verified weekly insight. Data-health banners remain the source for current freshness; a first sync already completed does not un-complete when data later grows stale. If location selection is disabled by the development feature flag, legacy auto-monitoring is considered complete after connection.
- The fifth step is durable: once the workspace has a saved plan, hide the first-run checklist. The brief step currently means **brief ready**, not tracked as **viewed**; first-view instrumentation belongs to step 4.
- Verify on the existing end-to-end browser journey, including progress after saving locations and hiding after the first decision.

## Step 2 — Insight and error-state clarity
- Audit every signed-in page for loading, disconnected, no-data, partial import, stale sync, revoked token, permission denial and server error states.
- No false statements such as "Nothing changed" while the data-completeness guard says incomplete.
- Each state has a next action and clear explanation. Add deterministic browser tests for failure and recovery.

## Step 3 — Mobile, navigation and accessibility
- Responsive app shell, keyboard-only flows, visible focus, semantic labels, screen-reader announcements, reduced-motion support.
- Axe checks on every page in the golden path; zero serious/critical violations. Lighthouse mobile >= 90 on public pages.
- Test narrow viewport and touch interactions end to end, not screenshots alone.

## Step 4 — Customer-readiness and feedback
- Help center: connection, data completeness, refunds/taxes, prices, invoices, cancellation; reachable support contact.
- CSV export and workspace deletion with confirmation, tenant isolation and deletion tests.
- Draft Terms/Privacy pages with explicit legal-review flags; capture consent at signup only after legal requirements are settled.
- Privacy-respecting activation, first insight view, weekly retention and decision follow-through instrumentation; no PII in analytics, plus backend/frontend error tracking.
- Uncoached usability test with three new users; sample finding in <= 2 minutes and connection without assistance.

## Go/no-go
M6 is not complete simply because all changes merged. Keep M7 and real merchant OAuth / LIVE Stripe blocked until hosting, consent, privacy/security and release gates in `docs/PRODUCTION_READINESS.md`, `docs/V013_TO_V1_PRODUCTION_GATES.md`, and `docs/PILOT_TRUST_PLAN.md` have verified evidence.
