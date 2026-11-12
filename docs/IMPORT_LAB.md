# GuestLift v0.3 — Import Lab

The Import Lab is designed to answer a concrete question: **Can different vendor-shaped POS records become the same auditable order model, and can a restaurant operator inspect the transformation?**

**Current scope:** fabricated sample files, not certified Toast exports or an authorized Square seller integration. The public site runs parsing **entirely in the visitor's browser**; the development API runs on localhost only.

## Five-minute walkthrough

1. Open `http://localhost:3000/import` (or `/import` on a public static deployment).
2. Select **Toast POS** and click **Download Toast CSV sample pack**. Extract the ZIP.
3. Select the three CSV files: `OrderDetails.csv`, `ItemSelectionDetails.csv`, `PaymentDetails.csv`.
4. Click **Run import pipeline**. The page actually reads and normalizes your selected files, not a pre-rendered image.
5. Inspect **28 accepted orders**, **$594.70 pretax net sales**, and the raw-to-GRDC order breakdown. Your local Docker instance should also show the SQL import count and a run ID.
6. Select **Square POS**, download/extract the sample ZIP, select `orders.json`, `payments.json`, `refunds.json`, and run again. Expect **28 orders**, **$650.80 pretax net sales**.
7. Click **Model an offer on these orders**. The Offer Studio will use the canonical synthetic orders saved in this tab's browser session. Change the coupon, threshold and assumed margin.

### Prove validation does something real

Download `toast-broken-example.zip` from `/samples/toast-broken-example.zip`. The included `OrderDetails.csv` uses `Wrong Order Key` in place of `Order Id`. Run the three-file import and verify it **fails visibly** with a missing-header error. The SQL database should not change after a rejected import.

### Prove the reported totals aren't hardcoded

Edit a single fabricated Toast source row in two places so the figures are consistent:

- In `ItemSelectionDetails.csv`, change the first order's gross item amount from `12.90` to `13.90`.
- In `OrderDetails.csv`, change the corresponding total from `22.03` to `23.03`.
- In `PaymentDetails.csv`, change that order's payment amount from `22.03` to `23.03`.

If you had previously imported this sample to local SQL, **change the order ID and its corresponding item/payment foreign keys**, or click **Reset local demo SQL** in the Import Lab (after confirming), which uses the existing `/api/reset` endpoint, because replays are intentionally ignored. The standalone browser analytics should immediately increase its net sales by $1.00. This demonstrates that numbers are derived from your files.

## What happens technically

- `frontend/lib/browser-import.mjs`: Browser parser for the two *sample* formats, including quoted/multiline CSV handling, required headers, ID uniqueness, foreign-key references, USD minor-unit money, voided items and completed refunds.
- `frontend/app/import/page.tsx`: File selection, sample downloads, progress/validation states, canonical drilldown, computed metrics, local-API detection.
- `backend/app/main.py`: `/api/upload/toast` and `/api/upload/square` accept exactly the three expected local synthetic files per provider, each at most 2 MB. Parses with the Python adapters and writes accepted orders to SQL with duplicate-ID replay detection.
- `frontend/app/offers/page.tsx`: Uses locally parsed canonical records from `sessionStorage` after navigating from `/import`. The tab's session data is not sent to a public server.

## Important limitations

- No live Toast or Square accounts connected. No customer names, email, card numbers or real merchant information should be uploaded.
- The browser pipeline is implemented in JavaScript; the local Docker pipeline uses the Python adapters and PostgreSQL. They share the **GRDC shape**, but code paths are distinct and should be kept aligned with contract tests.
- The public static deployment has **no persistent backend, SQL audit or merchant authentication**. Source files never leave the visitor's browser in public mode.
- The prototype uses order/item/payment/refund figures to compute a simplified pretax net sales definition. Financial definitions require further validation against real-world POS exports.
- Local SQL import is idempotent by `(provider, source_order_id)`. Updated source records are treated as duplicates, not correction events, until the later upsert milestone.
- A single bad input causes the entire import to fail; per-row quarantine, partial acceptance and schema flexibility are future work.
- The Offer Studio models the cost of applying a hypothetical offer to existing sample baskets; it cannot claim real redemption or incremental profit.

## Local API examples

The FastAPI docs at `http://localhost:8000/docs` expose `POST /api/upload/{provider}` with a three-file multipart form. The API is **unauthenticated and strictly for localhost demonstrations**; never publicly expose its port.

## Test commands

From repository root:

```bash
cd frontend && node --test tests/*.test.mjs
cd ../backend && python -m pytest -q
```

Or run inside Docker after `docker compose up --build -d`:

```bash
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm run test:offers
```
