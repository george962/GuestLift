# TableSignal — v0.12.2

**Restaurant decision intelligence: Connect → Discover → Investigate → Decide → Track.**

TableSignal is a **local development preview**, not a commercially deployed restaurant analytics service. The public workspace uses fictional data. Private accounts are developer-only; the Square connector targets **Square Sandbox**; Stripe supports **TEST** billing only. Never use this build for real merchant data, public customer signups, or live payments.

## Repository layout

- `frontend/` — Next.js public site, sample workspace, local-account UI, analyst, Square connection and billing screens.
- `backend/` — FastAPI, synthetic order adapters, local auth, SQLite/PostgreSQL-friendly models, Square Sandbox and Stripe TEST logic.
- `docs/` — current product/launch specifications and [production readiness](docs/PRODUCTION_READINESS.md).
- `compose.yaml` — **localhost-only** developer services and retained Postgres volume.

## Local development

1. Use Docker Desktop and keep `.env` local; never commit credentials.
2. From repository root: `docker compose up -d --build`.
3. Open `http://localhost:3000`; test API health at `http://localhost:8000/api/health`.
4. Run `docker compose ps -a` and `docker compose logs --tail=100 frontend backend` if startup fails.
5. Never run `docker compose down -v` unless intentionally destroying local database contents.

## Tests

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
# with localhost:3000 serving: npx playwright test e2e/v012-public.spec.ts
cd ../backend
python -m pip install -r requirements.txt
python -m pytest -q
PYTHONPATH=. python -m unittest discover -s tests -p 'test_location_billing_rules.py' -v
```

CI on pull requests must run the same checks. A successful build or synthetic sample test **does not** certify security, real Square API behavior, or Stripe LIVE readiness.

## Current commercial assumption

Growth is **provisionally $99 per selected, eligible, provider-verified location per month**. This is a product proposal, **not active pricing**. Stripe TEST uses its independently configured `STRIPE_GROWTH_PRICE_ID` and its quantity is **currently fixed to one**. The standalone `backend/app/location_billing_rules.py` quote is **not wired** to checkout or entitlements; production billing is blocked until it is.

## Source of truth

- [Active roadmap](ROADMAP.md)
- [Production readiness gates and evidence log](docs/PRODUCTION_READINESS.md)
- [Detailed v0.13→v1.0 release gates](docs/V013_TO_V1_PRODUCTION_GATES.md)
- [Product and location billing specification](docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md)

Earlier `INSTALL_V0*`, `README_V011.md`, preview HTML files and tracked ZIP releases are **historical artifacts**. Do not unzip patches over the live working tree. Use version-controlled edits, branches, pull requests and CI.
