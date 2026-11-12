# Upgrading from v0.7 to v0.8

The v0.8 ZIP is a **complete replacement source tree** based on your existing v0.7 project. Copy its files into `~/GuestLift`; preserve the `.git` directory and local secrets (`.env`). Do **not** copy a second nested folder into `~/GuestLift` if the contents are already at the project root.

**What changes:** The login backend now uses local `local_users` and `local_sessions` SQL tables instead of Supabase. `frontend/lib/supabase-client.ts` is now a tiny **local-auth compatibility shim** to overwrite stale v0.7 copies (it does not use Supabase). `frontend/lib/local-auth.ts` handles cookie-based sessions; `backend/app/local_auth.py` provides local register/login/logout/change-password endpoints. Your existing tables are not removed or wiped.

**Previous Supabase test identities are not automatically migrated.** Create new local test accounts. Orphaned old synthetic workspaces stay in PostgreSQL until explicitly migrated/cleaned later.

**No volume deletion:** use `docker compose up --build -d`; **not** `docker compose down -v`. This adds the local-user tables to your database without deleting the existing demo data.

**Git warning:** The included `supabase-client.ts` shim safely overwrites the old Supabase-dependent source when upgrading by copying files over an existing project; it contains no third-party authentication dependency. Avoid committing your `.env` or backups.

Run the test block in `RUN_ME_FIRST.md`. A browser-based signup/signout/profile test is required before calling the frontend verified.
