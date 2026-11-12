# GuestLift v0.3 — Start here

This package contains the **complete Next.js + FastAPI + PostgreSQL application**, including the new hands-on Data Import Lab. It replaces the v0.2 files in your existing `george962/GuestLift` repository, but it is **not deployed automatically**.

## The shortest path

1. Open [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md). Its Terminal commands unzip and copy this package into your `~/GuestLift` checkout, build Docker, and run tests without manually installing FastAPI.
2. Visit `http://localhost:3000/import`.
3. Click **Download Toast CSV sample pack**, extract it, upload all three CSVs and run the import. You should see **28 accepted orders, $594.70 in pretax net sales**, and an optional local SQL import ID.
4. Repeat with the Square JSON sample ZIP: **28 accepted orders, $650.80 in pretax net sales**.
5. Try the deliberately invalid Toast ZIP and inspect the validation error; click through a split-payment or refunded order to compare the actual source fields with the normalized GRDC record.
6. Click **Model an offer on these orders** to evaluate a hypothetical coupon using the canonical synthetic orders from your browser session.
7. When ready, publish the **static browser-only frontend** via Cloudflare Pages using [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Never upload real restaurant or customer data to this prototype.** Local FastAPI is unauthenticated and intended for 127.0.0.1 only. The public static version does not send uploaded synthetic files to a server.

For technical details and limitations, see [docs/IMPORT_LAB.md](docs/IMPORT_LAB.md) and [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).
