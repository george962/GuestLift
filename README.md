# TableSignal v0.12 — Public product experience & billing design (drop-in)

## What is included

- `frontend/components/v012-experience.tsx` — complete Next.js client component for the new public landing experience and simulated location selector.
- `frontend/app/page.tsx` — the `/` route with SEO metadata; imports the new experience.
- `frontend/app/v012.css` — prefixed responsive stylesheet; coexists with existing `globals.css` and hides duplicate global public nav/footer on the new homepage in modern browsers.
- `backend/app/location_billing_rules.py` and `backend/tests/test_location_billing_rules.py` — server-side, provider-verified location-quote domain rules and 6 passing pure unit tests (not connected to billing endpoints yet).
- `docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md` — account, OAuth, provider-verified location selection, trial, Stripe state and edge-case specification.
- `docs/V013_TO_V1_PRODUCTION_GATES.md` — explicit release blockers/acceptance criteria.
- A separate `tablesignal-v012-preview/index.html` provides a standalone local preview and does NOT access a real merchant account.

## Where to place files

From the root of the actual latest TableSignal Next.js workspace, copy complete source files to their matching relative paths. This is a **non-destructive package** with two new route/component files plus a homepage replacement; review against your local v0.11 before copying because GitHub `main` was inspected as v0.10.

Do not overwrite local `.env` or databases. Do not replace `frontend/app/layout.tsx` or the authenticated product screens. Keep production frontend/backend test gates.

## Test after integration

```bash
cd frontend
npm run lint
npm run build
npm test
```

Pure billing-rule tests included in this package (from the package root):

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

Also run local Playwright E2E/mobile checks against a real Next server, then verify both `/` and authenticated dashboards. The synthetic sample and the pricing calculator work client-side; no payments or OAuth are wired by this package.

## Distribution disclaimer

GitHub write/branch creation was rejected by integration permissions (403). **This package was not pushed, merged or deployed.** Keep the product demo labeled fictional. V1.0 is reserved for independently tested real signup, live OAuth, verified location billing and payment acceptance.
