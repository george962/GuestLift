# Square data pipeline (M3)

How TableSignal imports a restaurant's Square data, and how to check it's right.

## Processes
- **API** (`uvicorn app.main:app`): "Sync now" runs a sync for up to `GUESTLIFT_SYNC_INLINE_SECONDS` (20s). Whatever is left continues in the worker.
- **Worker** (`python -m app.worker`): queues a sync for every active connection every `GUESTLIFT_SYNC_INTERVAL_HOURS` (4h) and runs jobs in `GUESTLIFT_WORKER_SLICE_SECONDS` slices (60s). You can run several worker processes; jobs are claimed atomically. Docker Compose runs one as `worker`.

## Sync
- Weekly windows of order creation time per monitored location, oldest first. Each window's payments (guest IDs), orders and refunds are saved together, then the location checkpoint (`square_location_state.synced_through`) advances.
- First sync imports `GUESTLIFT_BACKFILL_DAYS` (395, about 13 months). Later syncs re-read the last 3 days.
- No order limit. Crashes and rate limits lose at most the window in progress, and the next run resumes from the checkpoint without duplicates.
- Failures:
  - 429, Square 5xx and network errors: retried with exponential backoff, up to 6 attempts.
  - 401/403 (token rejected): the connection is marked `needs_reconnect` and the owner sees "Reconnect Square".
- Tokens are refreshed when fewer than 7 days remain; Square tokens last 30 days.
- Revocation: Square's `oauth.authorization.revoked` webhook (`POST /api/integrations/square/webhook`, HMAC-verified with `SQUARE_WEBHOOK_SIGNATURE_KEY` and `SQUARE_WEBHOOK_URL`) deletes the tokens and stops syncing.

## Numbers
- **Net sales** = order total − tax − tips − service charges − completed refunds. Refunds count on the day they happened.
- **Days** follow each location's own time zone (from Square), as Square's reports do.
- Not separated yet: gift card sales, comps. These are listed in the data-health "What these numbers don't include" box.

## Checking against Square
`GET /api/integrations/square/reconciliation?start=YYYY-MM-DD&end=YYYY-MM-DD` (up to 93 days), shown on the Connections page as **Check against Square** with a CSV download. Compare one location at a time with Square Dashboard → Reports → Sales summary for the same dates. The pilot accuracy bar (`docs/PILOT_TRUST_PLAN.md` §3) is an exact order count and money within ±0.5%.

## Environments
`SQUARE_ENVIRONMENT=sandbox` (default) or `production`. Production refuses to start unless `GUESTLIFT_ALLOW_SQUARE_PRODUCTION=1`, which is only to be set once Gate P0 passes. Credentials: `SQUARE_APP_ID`, `SQUARE_APP_SECRET`, `SQUARE_REDIRECT_URI`. Sandbox also accepts the older `SQUARE_SANDBOX_*` names.

## Data health
`GET /api/integrations/square/health` returns one of: `importing` (with % done), `healthy`, `stale` (no update in 12h), `error`, `needs_reconnect`, `revoked` or `not_connected`. It also lists the known gaps. A banner shows on the dashboard, analyst, opportunities and connections pages whenever the status isn't healthy.
