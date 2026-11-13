# v0.8 to v0.9 — preserve your local accounts

1. Back up your existing Postgres database (especially if you care about prior development accounts):

   ```bash
   cd "$HOME/GuestLift"
   docker compose exec -T database pg_dump -U guestlift guestlift > tablesignal-backup-before-v09.sql
   ```

   This backup contains sensitive password hashes and emails. Keep it private, encrypted if possible, and outside GitHub.

2. Copy only the v0.9 source files over the matching contents of `~/GuestLift`; keep `.git/`, `.env`, and the Docker database volume unchanged. Do not nest `TableSignal_v0_9_Connected_Onboarding/` inside another copy of the project.
3. Bring up services using the complete block in `RUN_ME_FIRST.md`.
4. Sign in to your existing local account. New v0.9 SQL tables are created additively. Prior accounts and profile names are preserved.
5. **Intentional change:** private dashboards now show **only connected Square Sandbox orders**. Old `saas_workspace_demo_orders` from v0.8 remain in the database for backward compatibility but are not displayed. Public sample data remains available separately at `/workspace`.
6. Configure optional Square Sandbox credentials in the same ignored `.env`. See `docs/SQUARE_SANDBOX_SETUP.md`. Never paste secrets into the browser or GitHub.
7. Verify real Sandbox test calls and data ownership before committing v0.9. Do not switch Stripe to live keys or publish the unauthenticated demo API.

The full Next.js build and external Square Sandbox communication must be verified on the user's Mac; they were not runnable in the file creation environment.
