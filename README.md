# TableSignal — v0.13.0 (Sandbox integration)

**Restaurant decision intelligence: Connect → Discover → Investigate → Decide → Track.**

TableSignal is a **local development preview**, not a commercially deployed restaurant analytics service. The public workspace uses fictional data. Private accounts are developer-only; the Square connector targets **Square Sandbox**; Stripe supports **TEST** billing only. Never use this build for real merchant data, public customer signups, or live payments.

## Repository layout

- `frontend/` — Next.js public site, sample workspace, local-account UI, analyst, Square connection and billing screens.
- `backend/` — FastAPI, synthetic order adapters, local auth, SQLite/PostgreSQL-friendly models, Square Sandbox and Stripe TEST logic.
- `docs/` — current product/launch specifications and [production readiness](docs/PRODUCTION_READINESS.md).
- `compose.yaml` — **localhost-only** developer services and retained Postgres volume.

## Local development

1. Use Docker Desktop and keep `.env` local; never commit credentials.
2. From repository root: `docker compose up -d --build`. A one-shot `migrate` service brings the database schema up to date before the API and worker start ([docs/MIGRATIONS.md](docs/MIGRATIONS.md)). Without Docker, run `python -m app.migrate` in `backend/` before starting the API or worker.
3. Open `http://localhost:3000`; test API health at `http://localhost:8000/api/health`.
4. Run `docker compose ps -a` and `docker compose logs --tail=100 migrate backend worker frontend` if startup fails.
5. Never run `docker compose down -v` unless intentionally destroying local database contents.

## Tests

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
# with localhost:3000 serving: npx playwright test e2e/v012-public.spec.ts

# Signed-in customer journey (mock Square, own ports; runs alongside docker compose):
# ../scripts/journey.sh
# Full compose stack in its own project and ports (PostgreSQL, migrate, API, worker, frontend):
# ../scripts/compose-smoke.sh
cd ../backend
python -m pip install -r requirements.txt
python -m pytest -q
PYTHONPATH=. python -m unittest discover -s tests -p 'test_location_billing_rules.py' -v
```

CI on pull requests must run the same checks. A successful build or synthetic sample test **does not** certify security, real Square API behavior, or Stripe LIVE readiness.

## Current commercial assumption

Growth is **provisionally $99 per selected, eligible, provider-verified location per month**. This is a product proposal, **not active pricing**. Stripe TEST uses its independently configured `STRIPE_GROWTH_PRICE_ID`. Behind the OFF-by-default `TABLESIGNAL_SANDBOX_LOCATION_BILLING=1` local-dev flag, checkout quantity is derived from selected and server-refreshed Square Sandbox locations and verified against subscription metadata. The `$99/location` figure remains a proposal, not an actual Stripe TEST or LIVE price. Production entitlements, prorations and live billing remain blocked.

## v0.13 local Sandbox integration test

To opt into the new owner-selected monitored-location Sandbox flow, add `TABLESIGNAL_SANDBOX_LOCATION_BILLING=1` to your existing **local only** `.env` and rebuild Docker. Visit `/connections`, select active physical Sandbox locations, sync orders, and inspect `/billing`. Stripe TEST quantity is based on those selections; the configured TEST price is **not** necessarily $99. Never enable this local-only build for real merchants or real charges.

## Source of truth

- [Active roadmap](ROADMAP.md)
- [Production readiness gates and evidence log](docs/PRODUCTION_READINESS.md)
- [Detailed v0.13→v1.0 release gates](docs/V013_TO_V1_PRODUCTION_GATES.md)
- [Product and location billing specification](docs/V012_PRODUCT_AND_SELF_SERVICE_BILLING.md)

Earlier install guides, patch ZIPs and standalone preview files were removed from the tree (they remain in git history). Do not unzip patches over the live working tree. Use version-controlled edits, branches, pull requests and CI.
