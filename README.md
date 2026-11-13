# TableSignal v0.10 — Restaurant Retention & Promotion Intelligence

**Local developer release (not production merchant ready).** See [Customer Journey](docs/V010_CUSTOMER_JOURNEY.md), [Acceptance Tests](docs/V010_ACCEPTANCE_TESTS.md), and [Safe Upgrade](INSTALL_V010.md).

This version turns private Square Sandbox orders into evidence-backed opportunities, hypothetical offer-cost comparisons, and saved account-specific experiment drafts, alongside improved account confirmation, onboarding progress, navigation, and session resilience.

**Quick start (on Mac):** `docker compose up --build -d`; browse `http://localhost:3000`. Keep existing `.env` credentials and Docker PostgreSQL volume. Stripe is test-only and Square is Sandbox-only. No actual messages or campaigns are sent.

**Verification:** 45 backend tests and 39 frontend JavaScript tests passed in the builder. The full Next.js production build, real browser E2E and external Stripe/Square connectivity must be tested on the Mac.

---

# TableSignal v0.9 — Connected Restaurant Onboarding (local development release)

**TableSignal connects Square Sandbox test orders to a private, account-specific restaurant dashboard.** Each account begins empty. The public fictional demo remains separate, and paid analyst endpoints still require a verified **Stripe TEST** subscription. This package is a complete replacement of v0.8 based on [`george962/GuestLift`](https://github.com/george962/GuestLift).

> This is a local developer/pilot foundation, **not a production merchant service**. Do not upload real customer data, connect real seller accounts, share secrets or expose the backend publicly. The name TableSignal is provisional.

## What is new

- **Real account journey:** `/sign-up` → `/onboarding` (restaurant → plan → connection) → `/connections` → `/dashboard`.
- **Private dashboard:** new accounts no longer inherit the same 56 fictional orders. All private figures are calculated server-side from that account's own Square Sandbox synchronized orders. Sales trend, locations, observed repeat guests, data completeness, promotions and analyst statuses are represented faithfully.
- **Real Square *Sandbox* API access:** `ListLocations`, `SearchOrders`, `ListPayments` (to join customer IDs when present), with pagination, completed-order filter, USD currency validation and a bounded 180-day import window.
- **Connection methods:** your **own local developer Sandbox token** (easy first test) or **Square Sandbox OAuth** (scoped test authorization). OAuth state is time-bound and single-use, credentials are encrypted with a developer-supplied Fernet key. Secrets never appear in API status responses.
- **Tenant-scoped persistence:** `square_sandbox_connections`, `square_sandbox_oauth_states`, `square_sandbox_orders`, `square_sandbox_sync_runs`, and `assisted_setup_requests` added to existing Postgres using additive SQLAlchemy table creation.
- **Sync operations:** authenticated, CSRF-protected sync; order IDs upsert on re-run, existing orders are refreshed; one failed sync rolls back imported rows while recording a failed job. Disconnect deletes local credentials and associated Sandbox orders. Supported volume: max 800 orders per location batch in the last 180 days.
- **Assisted onboarding:** records *local-only* implementation requests for future review—no imaginary outgoing support email or integration-fee charge.
- **Local test data:** a developer-only utility can create paid fictional orders **through Square's real Sandbox APIs**. It never uses production.
- **Test billing:** optional Stripe Checkout and signed subscription webhooks from v0.8 remain. Registration itself is free; private AI usage is gated by a verified Growth test subscription. No live charges.

## Start locally

From your Mac's project folder `~/GuestLift`, after replacing its source files with this package:

```bash
cd "$HOME/GuestLift"
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

**No separate Supabase installation.** Existing PostgreSQL Docker volume persists; do **not** run `docker compose down -v`. Keep `.git` and `.env` unchanged when copying a release.

- Homepage: http://localhost:3000
- Free fictional demo: http://localhost:3000/workspace
- Account registration: http://localhost:3000/sign-up
- Onboarding: http://localhost:3000/onboarding
- Private account dashboard: http://localhost:3000/dashboard
- Square Sandbox connection: http://localhost:3000/connections
- Test subscription management: http://localhost:3000/billing

## First real API experiment

1. Create a developer Sandbox app at [Square Developer Console](https://developer.squareup.com/apps).
2. Open Sandbox → Credentials and locate **your own Sandbox access token** (never send it in chat or put it in GitHub).
3. Set `SQUARE_SANDBOX_ACCESS_TOKEN` in root `.env` using `.env.example` as a reference, then restart `docker compose up -d --force-recreate backend`.
4. Register an account on TableSignal and provide a restaurant name.
5. At `/connections`, choose **Connect my Sandbox** and **Sync last 180 days**.
6. If you have no completed Sandbox orders, generate fictional transactions using Square API Explorer or, intentionally, run `docker compose exec backend env TABLESIGNAL_SEED_CONFIRM=YES python -m app.dev_seed_square` and sync again.
7. Verify that `/dashboard` contains your Sandbox data, then register a second account using a different browser profile. The second account must not see the first's orders or reuse the same connected seller.

The token is stored **only** in the backend environment for developer-token mode, not sent from the browser and not persisted in the SQL connection table. The optional OAuth flow stores encrypted access/refresh tokens. See [detailed setup](docs/SQUARE_SANDBOX_SETUP.md).

## Source of truth and financial caution

- Only orders in Square state `COMPLETED` are included in reported order counts. `OPEN` orders are omitted; canceled records do not contribute.
- Dashboard **observed order value** is `Square total_money − reported total_tax_money − reported total_tip_money`. It is *not fully reconciled net sales*: return/refund processing, service charges, payment reconciliation and currency conversions are **not implemented**. The UI names this limitation.
- Stable customer IDs are used only when present in exact order or linked completed payment records. Missing customer IDs remain anonymous, not inferred.
- A direct, connected order total does **not** prove revenue lift, promotion attribution, acquisition or retention causality.
- **No automatic background synchronization** yet. A human clicks Sync; a monitored queue, pagination checkpoints, retries, corrections and webhook reconcilers remain production blockers.

## Verified scope

- Backend: end-to-end tests with mocked Square responses and real local SQL ORM verify registration, CSRF, workspace separation, new-account zero state, upsert/replay, updated customer IDs, seller ownership, encrypted OAuth, one-use state, assisted request scoping and rollback after sync failure.
- Frontend: existing offer/import/analytics test suite plus v0.9 route checks and TypeScript syntax checks.
- **Not verified in this build environment:** full Next.js compile (npm registry inaccessible), live Square Sandbox API calls (your own Sandbox token needed), Stripe external test checkout, mobile browser acceptance. These need verification on your Mac before calling this milestone fully accepted.

## Next

See [ROADMAP.md](ROADMAP.md), [architecture and security](docs/V09_ARCHITECTURE.md), and [release deployment checklist](docs/PRODUCTION_READINESS.md).

TableSignal is independent and not affiliated with Square or Toast. No production seller onboarding or public merchant-data handling is enabled.
