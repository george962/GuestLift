# GuestLift v0.4 — Start here

This download is a **complete GitHub-ready GuestLift application tree** with a new Campaign Lab, fictional coupon/redemption imports, repeat-customer reporting, local SQL data models, and automated tests. The original `frontend/`, `backend/`, `docs/` and Docker files are included; you do not need to reconstruct them from patches.

## 1. Update your existing repository

Read [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) for the exact Mac steps. Download and extract the release ZIP, then copy the extracted `GuestLift_v0_4/` folder contents into your existing `~/GuestLift/` checkout using `rsync` (preserving `.git`). You can also add the files to an empty repo if starting fresh.

## 2. Build and run with Docker

From the project root:

```bash
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
```

Open http://localhost:3000/campaigns. The site also has `/import`, `/offers`, `/demo`, and `/how-it-works`.

## 3. Try the sample campaign data

- Click **Download sample campaigns** in `/campaigns` or use `frontend/public/samples/campaigns-demo.zip`.
- Extract `Campaigns.csv` and `Redemptions.csv` and upload them via the two inputs on the page.
- Expected result: **21 valid redemptions across two fictional campaigns** from 56 sample Toast/Square orders. The figures in each report are computed, not pasted dashboard constants.
- Explore a wrong order ID or a coupon discount bigger than the POS discount to trigger a validation issue. A broken sample ZIP is included.
- If Docker is running, **Save to local SQL** should load example orders/campaigns. Use http://localhost:8000/api/campaigns/report to inspect server-side results.
- If your PostgreSQL volume contains v0.3 example records, optional customer IDs on those already imported records may still be missing; use the local-only `/api/reset` action and reload the new synthetic fixtures for a clean v0.4 demo.

**Never use real merchant exports, transaction data or personal information in this prototype.** Public hosting must use the static frontend, not the local unauthenticated API.

## 4. Publish source after reviewing

Check `git status`, then commit and push the files. CI will run frontend tests and a Next.js build plus Python tests. For public static hosting, follow `docs/DEPLOYMENT.md`.

## Current limits

No real Toast/Square connections, real coupon issuance, production customer identity resolution, multi-tenant security, real profit claims, or experiment/holdout analysis. See `docs/IMPLEMENTATION_STATUS.md`.
