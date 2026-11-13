# Safe TableSignal v0.10 upgrade

If you're already running v0.9.1 on Mac in `~/GuestLift`, install the **upgrade patch ZIP**, not the full project ZIP. The patch contains only changed/new paths and does not include `.env`, `.git`, credentials or a database.

1. Keep your existing `~/GuestLift` folder. Do NOT remove or recreate it.
2. Save `TableSignal_v0_10_Upgrade_Patch.zip` from ChatGPT to `~/Downloads`.
3. Back up your existing project files before extracting. Extract the patch **into** `~/GuestLift`; file paths in the patch start with `backend/` or `frontend/`, plus docs and release files. This is an additive upgrade: no tracked files need deleting.
4. Run `cd ~/GuestLift && docker compose up --build -d`.
5. Run tests and typecheck: `docker compose exec -T backend python -m pytest -q && docker compose exec -T frontend npm test && docker compose exec -T frontend npm run lint`.
6. Open `http://localhost:3000/account/welcome`, `http://localhost:3000/onboarding`, `http://localhost:3000/opportunities` and `http://localhost:3000/experiments` with an existing or test account.
7. Confirm billing and Square Sandbox still function. Do not repeat a paid test checkout if your Growth plan is already active.
8. Inspect `git diff --stat` and `git status` before committing. Do not run `git reset --hard` or `docker compose down -v`.

The full source ZIP is an archive/reference, not an instruction to overwrite an existing working project. This release was not automatically deployed or pushed to GitHub.
