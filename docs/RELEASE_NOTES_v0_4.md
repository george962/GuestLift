# GuestLift v0.4 — Campaign Analytics MVP

## Added

- `/campaigns` operator-facing page with a working two-CSV campaign import, genuine sample calculations, location breakdowns, customer coverage and record drill-down.
- Two synthetic campaign files (`Campaigns.csv`, `Redemptions.csv`) plus a deliberately broken example.
- Typed browser-only campaign parser and report model, usable on a static website with no backend.
- SQL `campaigns`, `campaign_redemptions`, and `campaign_import_runs` tables, and optional synthetic customer IDs on canonical orders.
- Local FastAPI endpoints for campaign import, reports, customer coverage, and loading idempotent sample data.
- Additional regression tests for invalid coupon references, double-counting, duplicate imports, repeat-customer coverage and legacy schema migration.
- Updated homepage and navigation to highlight campaign decisions, with meaningful campaign/margin color semantics.

## Source limitations

- Toast/Square files are **fabricated**. They are not live vendor integrations.
- A Toast field named `GuestLift Test Customer Id` and the Square test JSON customer IDs are custom fixture-only data, not an assertion about production vendor schemas.
- The test dataset reports *sales on redeemed orders*, not incremental revenue or real restaurant profitability.
- Contribution margin is an assumed scenario; marketing allocation and fulfillment cost are not extracted from POS files.
- Customer ID continuity is limited to one provider. No identity resolution across vendors or devices.
- A maximum of one redemption is allowed per order, and corrected redemptions are rejected pending an explicit update workflow.
- Static public hosting processes sample CSVs in the browser. The SQL backend must remain localhost-only.

## Validation performed

- 19 passing Python backend tests.
- 19 passing JavaScript tests.
- Cross-checked browser and backend outputs for both sample campaigns and customer repeat summary.
- Parsed the new TSX page with TypeScript's syntax parser.

A full Next.js/npm production build could not be run in the development environment without the npm registry. **Run `docker compose up --build -d` locally and confirm the frontend build before deploying.**
