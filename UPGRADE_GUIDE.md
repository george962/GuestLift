# Upgrade v0.4 → v0.5

1. Keep your existing GitHub repository and `.git` folder.
2. Copy/extract the **complete v0.5 replacement source tree** over the application files. Do not replace `.git` or tracked secrets.
3. Confirm with `grep '"version"' frontend/package.json` — expected `0.5.0`.
4. Run from `~/GuestLift`: `docker compose up --build -d`.
5. Run backend tests: `docker compose exec -T backend python -m pytest -q`.
6. Run frontend tests: `docker compose exec -T frontend npm test`.
7. Open `/workspace`, `/pricing`, `/account`; check mobile layout and demo actions.
8. Commit only after successful local build: check `git status`, then `git add -A`, `git commit -m 'feat: unified workspace and SaaS foundation'`, `git push origin main`.

The new database tables are created additively. No `docker compose down -v` or database reset is required. **Existing v0.4 records are not converted into private account data**; each optional account receives its own separate synthetic seed.

If Docker won't build, share the actual error output. Do not install Python dependencies into your Conda base environment to diagnose Docker-only failures.
