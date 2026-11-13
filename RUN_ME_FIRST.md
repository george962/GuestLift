# Start TableSignal v0.9 on your Mac

The ZIP contains a complete replacement project. Keep your existing Git repository and ignored `.env`. **If you have already copied/extracted the new files directly into `~/GuestLift`, do not unzip or copy anything again.**

From your existing `~/GuestLift` folder:

```bash
cd "$HOME/GuestLift" || exit 1
grep '"version"' frontend/package.json
docker compose up --build -d
docker compose exec -T backend python -m pytest -q
docker compose exec -T frontend npm test
docker compose ps
git status --short
```

Expected application version: `0.9.0`. Open `http://localhost:3000/sign-up`, create a new test account, complete `http://localhost:3000/onboarding`, open `/connections` and `/dashboard`.

The dashboard starts **empty** until Square Sandbox data is synchronized. For developer Sandbox credentials and paid test orders, follow `docs/SQUARE_SANDBOX_SETUP.md`.

> Never run `docker compose down -v` for an upgrade; it deletes your local PostgreSQL volume. Do not overwrite `.env` or commit tokens. Before accepting real merchant data the security checklist in `docs/PRODUCTION_READINESS.md` must be completed.
