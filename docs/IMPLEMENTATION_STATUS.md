# GuestLift — Build v0.1 implementation status

**Updated:** November 12, 2026  
**Type:** Demo-only code release, *not* a production integration.

## Implemented in this package

| Roadmap | Shipped | Evidence / notes |
|---|---|---|
| M0 | README, proposal, Mermaid architecture | `README.md`, `docs/architecture.md`, `docs/proposal.md` |
| M1 | Responsive Next.js marketing home, How It Works, interactive Demo | `frontend/app/`; browser mode uses bundled pre-normalized synthetic sample |
| M2 | Python parser for Toast order, item and payment CSV fixtures | `backend/app/adapters.py`, `backend/fixtures/toast/`, unit tests |
| M3 | Python parser for Square Orders-shaped JSON, separate payment/refund fixtures | `backend/app/adapters.py`, `backend/fixtures/square/`; **not** a live Square Sandbox API integration |
| M4 | Canonical SQL persistence with unique `(provider, source_order_id)` key and shared reporting; PostgreSQL configured in Docker | `backend/app/database.py`, `compose.yaml`; SQLite default for quick local use; no formal Alembic migrations yet |
| M5 | Demo UI calls local FastAPI to import fixture data and read computed SQL metrics; browser-only preview when API absent | `frontend/app/demo/page.tsx`, `backend/app/main.py` |
| M6 | Python unit/API tests, duplicate replay, CI workflow, Compose, basic documentation | `backend/tests/test_pipeline.py`, `.github/workflows/ci.yml`; deeper failure recovery/security still needed |

## Open items, intentionally not marked complete

- Square Sandbox token-based API client and test account flow.
- Real Toast export compatibility testing with authorized merchant data, including configurable columns and modified/voided orders.
- Robust status updates/upserts when the source order changes after original import.
- File-upload endpoints for untrusted arbitrary CSVs; prototype imports shipped fixture files only.
- Tenant authentication/authorization, least-privilege, audit policy, retention, production secrets management, backups.
- Formal migrations, fuller refunds/taxes/tips/payment reconciliation, currency/locale variants, timezone normalization, business-day policy.
- Customer-level loyalty, campaign assignments, experimental incrementality, restaurant contribution costs and predictive modeling.
- Verified public deployment / hosted API.
- Independent operator feedback and real pilot.

## Important demo semantics

- **Toast** fixtures contain the documented core column names from official Toast data export field reference, using deliberately fabricated rows. Operators can customize exports, so this does not certify arbitrary real Toast files.
- **Square** fixture is API-shaped and synthetic. `orders.json`, `payments.json`, and `refunds.json` represent multiple source objects bundled together for demo purposes. No authenticated API request is performed.
- **GRDC** is a proposed canonical model, with source IDs, order items, payment events, amounts in integer cents and warnings. It is not an adopted industry standard.
- **Net sales** for this demo are item gross minus order discounts minus pretax sale refunds, excluding tax/tip. This is a project-specific example; real vendor financial definitions require careful verification.
- **Browser demo** loads saved pre-normalized examples, showing interactive pipeline stages as a *preview*, not actually running the Python adapter. The API-connected mode runs the adapters and persists results.
- No customer-owned data, credit card numbers, real ROI or claimed causal promotion lift are used.

## Verification performed in this build session

- Seven pytest tests passed for adapters, invalid money, duplicate/missing source headers, USD validation, SQL idempotency, API endpoints and dashboard totals.
- TS/TSX source files passed TypeScript parser/transpilation syntax checks.
- Frontend dependency installation and `next build` could **not** run in this environment because the npm registry was inaccessible. GitHub Actions workflow is included for independent frontend build verification after upload.

**Next engineering priority:** Install dependencies, run the Next.js website, then verify the local frontend-to-FastAPI interaction and fix any issues found before presenting the app to real operators.
