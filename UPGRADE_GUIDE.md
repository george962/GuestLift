# Upgrading from GuestLift / TableSignal v0.6 to v0.7

- Full replacement repository provided: frontend, backend, tests, fixtures, website and documentation. **No separate patches.**
- Copy the entire release's *contents* into the same existing `~/GuestLift` folder. Preserve your `.git` and your ignored `.env`. Keep existing PostgreSQL Docker volume if it contains your local synthetic test data.
- You do **not** need another unzip command after extracting the files yourself.
- Run the full one-block instructions in `RUN_ME_FIRST.md`.
- Rebuild the frontend after changing `NEXT_PUBLIC_SUPABASE_*` values: the env vars are embedded at build time.
- Old technical demo routes remain accessible but are no longer the primary public navigation.
- The name `TableSignal` is still temporary. Python internal identifiers and database volumes remain named GuestLift for backwards compatibility.
