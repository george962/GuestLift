# Update GuestLift from v0.3 to v0.4 on your Mac

The release ZIP is a **complete replacement code tree**, not a patch. It does not contain your `.git` directory, dependencies, database volume or secrets.

## Install

1. Download `GuestLift_v0_4_Campaign_Analytics_MVP.zip` and save it to your Mac's Downloads folder.
2. Extract it. The ZIP has one top-level folder named `GuestLift_v0_4`.
3. From a Mac Terminal, **after confirming the extracted directory exists**, run the following block. It copies the source files into your existing `~/GuestLift` Git checkout and does **not** delete existing files or your SQL volume.

```bash
cd "$HOME/GuestLift" || exit 1
SRC="$HOME/Downloads/GuestLift_v0_4"
if [[ ! -f "$SRC/frontend/app/campaigns/page.tsx" ]]; then
  echo "Can't find $SRC/frontend/app/campaigns/page.tsx. Check where Finder extracted the ZIP."
else
  rsync -av --exclude='.git/' --exclude='node_modules/' --exclude='.next/' --exclude='__pycache__/' --exclude='.venv/' "$SRC/" "$HOME/GuestLift/" && \
  docker compose up --build -d && \
  docker compose exec -T backend python -m pytest -q && \
  docker compose exec -T frontend npm test && \
  docker compose ps && \
  git status
fi
```

If Finder unzips the release into a differently named directory, change only the `SRC=` value to that **exact path**. Do not copy from guessed locations. `set -e` is intentionally not required.

## Verify

- Open `http://localhost:3000/campaigns`.
- Click **Download sample campaigns** to get the two CSVs.
- Use both file controls to upload them in the same browser.
- See 2 campaigns and 21 matched synthetic redemption events.
- Use **Save to local SQL**, then visit `http://localhost:8000/api/campaigns/report`.
- Repeat Save to local SQL; replays should not create extra redemptions.
- Visit `http://localhost:3000/import` for Toast/Square source-file imports, then return to the Campaign Lab.

## Save to GitHub

Only after the tests and pages work locally:

```bash
cd "$HOME/GuestLift"
git status
git add .
git commit -m "feat: campaign analytics MVP with synthetic loyalty reports"
git push origin main
```

`.gitignore` excludes Python caches, local databases and dependencies. Never commit `.env`, real restaurant transaction files or customer data.

## Important deployment distinction

Your public deployment should be the static Next.js export. The FastAPI backend has no merchant authentication or tenant separation and is **not safe to expose on the internet**. Public visitors can safely explore synthetic files in their browsers without a server-side upload service. See `docs/DEPLOYMENT.md`.
