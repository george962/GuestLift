# GuestLift v0.3 — Install and demo

**This is a full replacement application release for your existing `~/GuestLift` project.** It includes all v0.2 code plus a new Import Lab. No changes to your git remote are necessary.

## 1. Install on your Mac

Download `GuestLift_v0_3_Import_Lab.zip` into `~/Downloads`. From Terminal, paste the full block below. **This block has no `#` comment lines**, to avoid the zsh prompt problem seen previously.

```bash
set -e
unzip -o "$HOME/Downloads/GuestLift_v0_3_Import_Lab.zip" -d "$HOME/Downloads"
rsync -av --exclude='.git' "$HOME/Downloads/GuestLift_v0_3/" "$HOME/GuestLift/"
cd "$HOME/GuestLift"
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm run test

docker compose ps
git status
```

The backend should show **10 passing tests**, and the frontend should show **10 passing tests**. If either test fails, **do not commit yet**—read the error output first.

## 2. Test real source-file parsing

Open `http://localhost:3000/import`.

**Toast:** Click Download Toast CSV sample pack; extract it; select the three CSVs and click Run import pipeline. Expect 28 accepted orders and $594.70 pretax net sales.

**Square:** Switch provider; download/extract its JSON pack; upload all three files. Expect 28 accepted orders and $650.80 pretax net sales.

**Broken fixture:** Visit `http://localhost:3000/samples/toast-broken-example.zip`, extract/upload its three CSVs, and confirm you see a missing-header error instead of fabricated metrics.

**Coupon scenario:** After a successful import, click **Model an offer on these orders**; adjust percent-off, minimum order and margin in Offer Studio. The results use the canonical orders you just parsed in this browser session.

You can also edit a copy of any fabricated CSV to test how the calculations change. Use only synthetic data; do not upload real customer or restaurant records.

## 3. Commit your verified version

Only after the above is working:

```bash
cd "$HOME/GuestLift"
git add .
git commit -m "feat: interactive import lab, synthetic file upload, new brand identity"
git push origin main
```

If Git reports no changes, review `git status`; don't create an empty commit.

## 4. Public deployment

The import page also works on a static public Next.js build: the uploaded synthetic files are processed in the **visitor's browser only**. The static build does not include the Python backend or a remotely accessible SQL database. Use the existing [Cloudflare Pages guide](docs/DEPLOYMENT.md), which sets `GUESTLIFT_STATIC_EXPORT=1`, framework Next.js (static), root `frontend`, output `out`.

Before accepting actual merchant uploads, GuestLift needs seller authorization, authentication, tenant separation, strict data retention, encrypted transport/storage, secure backend hosting and vendor-specific schema verification. None of those are part of v0.3.
