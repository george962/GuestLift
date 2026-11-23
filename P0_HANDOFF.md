# P0 handoff: database architecture and startup reliability

Status: **backend fix done and tested; orchestration, CI, docs and Docker verification not started.**
Delete this file before merging into `feat/m4-insight-loop`.

## Where things are

| | |
|---|---|
| Worktree | `/Users/georgejiang/GuestLift/.claude/worktrees/fix-p0-database` |
| Branch | `fix/p0-database`, based on `feat/m4-insight-loop` @ `b3ec17a` (PR #29's head) |
| Commits | One local commit with everything below. **Not pushed** (see "Why not pushed") |
| PR #29 | Untouched, not merged. `feat/m4-insight-loop` is untouched |
| Python | Reuse `/Users/georgejiang/GuestLift/backend/.venv/bin/python` with cwd `backend/` (the lockfile is unchanged) |
| Test Postgres | Throwaway container `p0-pg` on `127.0.0.1:55433` (user `ci`, password `ci`, db `ci`). Recreate with: `docker run -d --rm --name p0-pg -e POSTGRES_USER=ci -e POSTGRES_PASSWORD=ci -e POSTGRES_DB=ci -p 127.0.0.1:55433:5432 postgres:16`. It is NOT the user's database |
| User's real stack | Compose project `guestlift` (main checkout): `database` healthy, `backend` exited (3), `worker` restart loop. **Unchanged by this work.** Volume `guestlift_guestlift_pg` |
| Backup of user DB | `pg_dump` (read-only) at `/private/tmp/claude-501/-Users-georgejiang-GuestLift/81b0ef71-9146-4b98-bfc9-d4d1a0ccb9ad/scratchpad/p0/user-db-backup.sql` (70 KB, sha256 prefix `a6ffde0e7ad39d87`). It contains password hashes: never commit it |
| User DB contents | 1 local user, 6 sessions, 1 workspace, 28 `canonical_orders`, no `alembic_version` |

## Root causes (one problem: two owners of the schema)

1. **API and worker both ran DDL at startup** (`init_db()` = `create_all()` plus ad-hoc ALTERs plus an in-process Alembic run for pre-scoping databases).
   - Concurrent `create_all()` → PostgreSQL `DeadlockDetected` / `UniqueViolation pg_type_typname_nsp_index`.
   - On SQLite → `table campaigns already exists`, the journey CI flake.
2. **Duplicate index.** `create_all()` (via an `after_create` hook) and `ensure_indexes()` created `uq_square_sync_jobs_one_open`; then the legacy-adoption path ran Alembic from base, and 0008's unguarded `op.create_index` failed: "already exists".
   - This is the user's exact worker restart loop: their database has pre-scoping demo tables, so adoption ran on every start.
3. **M3→M4 gap.** `create_all()` never adds columns to existing tables, and adoption only fired for pre-scoping databases. M3-era databases got the new M4 tables but none of the 0005/0006/0007 columns.
   - Result: `column saas_workspaces.trial_started_at does not exist`. The user's database lacks these columns right now.
4. **New finding: legacy duplicate open sync jobs.** `ensure_indexes()` built the unique index before 0008 could close the duplicate open jobs the old race left behind → `could not create unique index`.
5. **Latent bug in 0001.** Its module-level `_existing` set was never cleared, so migrating several databases in one process skipped tables.

## Fix implemented (backend)

- **`backend/app/migrate.py` (new)** is the only code that changes the schema.
  - Entry point: `python -m app.migrate`; `--check` reports only.
  - Runs `alembic upgrade head` under a cross-process lock: PostgreSQL `pg_advisory_lock(73072026)` on a dedicated connection; SQLite `fcntl.flock` on `<db>.migrate.lock`.
  - Legacy databases with no `alembic_version` are adopted in place by running every migration from base. They're all idempotent.
  - Afterwards it checks for tables or columns still missing versus the models. If any remain, it **stops and lists them. It never stamps a version it didn't apply** (the stamp-based "replay" path was removed at the user's request).
  - Also provides `status()` and `wait_until_ready(engine, timeout, should_continue)` (raises `SchemaNotReady`).
- **`database.init_db()`** now just calls `migrate.upgrade(engine)`, the same locked upgrade. `_adopt_pre_scoping_schema`, `create_all`, `ensure_indexes` and the manual `customer_id` ALTER were removed.
- **`main.py` (API) startup** never runs DDL. The lifespan calls `migrate.wait_until_ready(engine, GUESTLIFT_SCHEMA_WAIT_SECONDS=120)`, then fails with "Run `python -m app.migrate`". `/api/ready` now returns 503 with the reason when the schema isn't at head (SELECT 1 plus schema version).
- **`worker.py`** never runs DDL either.
  - It installs SIGTERM/SIGINT handlers first, then waits for the schema. Stopping while waiting exits 0. A timeout exits with code 3 and a clear message.
  - It touches `GUESTLIFT_WORKER_HEARTBEAT_FILE` (default `/tmp/tablesignal-worker-heartbeat`) every loop, for a Docker health check.
  - `main()` returns an exit code.
- **`dev_admin.py`** waits for the schema (5s) instead of calling `init_db()`.
- **`square_sync.py`:** the one-open-job partial unique index moved into `SquareSyncJob.__table_args__` (`Index(..., unique=True, sqlite_where/postgresql_where="status IN ('queued','running')")`). The DDL hook and `ensure_indexes()` were removed.
- **Migration `0008`:** closes duplicate open jobs first (newest kept, `ORDER BY created_at DESC, id DESC`), then creates the index only if it's missing. The downgrade is guarded.
- **Migration `0001`:** clears `_existing` on each run.
- **`alembic/env.py`:** the `UNMANAGED_INDEXES` / `include_object` exception was removed. `alembic check` is clean with the index in metadata.
- **`config.py`:** the `GUESTLIFT_AUTO_CREATE_SCHEMA` production check was removed. The flag no longer exists, because the services can't create tables.

## Tests

- **New fixtures:** `backend/tests/fixtures/legacy_schemas/`.
  - `v013_pre_m2.{sqlite,postgres}.sql` (commit `4a62f4f`) and `m3.{sqlite,postgres}.sql` (commit `7537614`) were generated by **running the old code's startup** (`scripts/make-legacy-schema-fixtures.sh`, committed).
  - `mixed_local_compose.postgres.sql` is a **schema-only** dump of the user's real database. It was asserted to contain no rows, emails or hashes.
- **New helpers:** `backend/tests/db_lifecycle.py`. They seed realistic legacy data (local account with a known password, session, subscribed workspace, Square connection, monitored location, orders, decision plan, demo orders, billing event, 2 duplicate open sync jobs). They also provide `assert_upgraded_with_data_intact()`:
  - the old password signs in; `/api/saas/me`, plans and Square status all work
  - counts are preserved; demo rows land in `public-demo`; `local_date` is backfilled
  - an owner membership row exists; at most one open job remains
  - no missing tables or columns, and **no missing indexes or constraints per Alembic `compare_metadata`**
  - the one-open index **definition** (unique and partial, with `queued`/`running`) and **behavior** (a second open job is refused, a finished job is allowed; probes rolled back)
  - the revision is at head
- **New test files:**
  - `test_schema_lifecycle.py` (SQLite): fresh database; 4 concurrent startups; `create_all` then upgrade; v0.13 and M3 legacy with data; Alembic-managed M3 (0005) to M4; every migration's `upgrade()` replayed on a current database (enforces idempotency without touching `alembic_version`); repeated upgrade is a no-op.
  - `test_postgres_lifecycle.py`: needs `TEST_POSTGRES_URL` (each test creates and drops its own database). Covers 6 concurrent startups; mixed/v0.13/M3 legacy with data; Alembic-managed M3 to M4; API and worker started **before** 3 racing `migrate` runs both become ready, plus register and login over HTTP; one-open constraint enforcement.
  - `test_service_startup.py`: no DDL in `app/` (static scan); the API refuses an unmigrated database and creates nothing; the API starts after migrate and `/api/ready` returns 503 when the schema is behind; the worker waits then starts and stops cleanly while waiting; the worker gives up with code 3; the migrate CLI is idempotent; 5 concurrent migrate runs (exactly one does the work).
- **Updated tests:**
  - `test_pipeline.py` and `test_campaigns.py` migrate their temporary databases, since the API no longer creates tables.
  - `test_square_sync_m3` worker boot test migrates first and checks the heartbeat.
  - `test_production_hardening` drops the old flag.
  - `test_schema_flag.py` was deleted (its flag is gone).
  - `conftest.py` gives the suite its own migrated session database (never `./guestlift_demo.db`).

### Results

| Run | Result |
|---|---|
| New regression tests **before** the fix | All failed with the original errors: `table campaigns already exists`, `UniqueViolation pg_type_typname_nsp_index`, `relation uq_square_sync_jobs_one_open already exists`, `column … trial_started_at does not exist`, `could not create unique index`, plus the 2 PR #29 legacy tests (`index … already exists`). Log: `scratchpad/p0/before.log` |
| Same tests **after** the fix | 25/25 pass (SQLite and PostgreSQL) |
| Mutation checks | Disabling the migration lock brings back all three concurrency failures; an unguarded 0008 brings back both duplicate-index failures. Both restored |
| Full backend suite, PostgreSQL enabled | **217 passed, 1 skipped (Stripe test clock, needs `RUN_STRIPE_TESTS=1`), 0 failed** (run twice; also 210 passed / 8 skipped without PostgreSQL) |
| Unresolved | `test_square_connections.py::test_sandbox_connect_sync_is_idempotent_and_isolated` failed **once** in an earlier full run (summary only, no traceback captured). It didn't reproduce in 2 full runs or in isolation. Treat as a possible intermittent failure: rerun the full suite a few times with `--tb=long` and investigate if it reappears |
| Not run yet | Frontend tests, browser journeys, Docker, CI (blocked on the remaining work) |
| Warnings | 182, mostly pre-existing deprecations (e.g. `Column.copy()` in 0006/0007). Not addressed |

## Why not pushed

`scripts/journey.sh` doesn't run `python -m app.migrate` yet. With this branch, its API would wait 120s for the schema and the `journey` CI job would fail. The same goes for the CI `docker` job, which boots the backend image alone. Push only after the orchestration below is done.

## What remains of P0 (do in this order)

1. **`scripts/journey.sh`:** run `"$PY" -m app.migrate` with the same `DATABASE_URL` **before** starting the API and worker.
2. **`compose.yaml`:**
   - Add a one-shot `migrate` service: same `./backend` build, `command: ["python","-m","app.migrate"]`, `environment: *backend-env`, depends on `database: service_healthy`, `restart: "no"`.
   - `backend` and `worker` should depend on `migrate: service_completed_successfully` (and `database: service_healthy`); drop the worker's `backend: service_started`.
   - Health checks:
     - backend: `python -c` urllib GET `http://127.0.0.1:8000/api/ready` (the slim image has no curl)
     - worker: heartbeat file mtime under ~300s
     - frontend: `wget -q -O /dev/null http://localhost:3000/`
   - `frontend` depends on `backend: service_healthy`.
   - Make the host ports configurable for an isolated project: `${TABLESIGNAL_API_PORT:-8000}`, `${TABLESIGNAL_WEB_PORT:-3000}`, and the frontend build arg `NEXT_PUBLIC_GUESTLIFT_API_URL: http://localhost:${TABLESIGNAL_API_PORT:-8000}`.
   - Keep the volume name `guestlift_pg`. Never `down -v`.
3. **`scripts/compose-smoke.sh` (new):**
   - `docker compose -p <project> up -d --build`.
   - Wait for backend, worker and frontend to be healthy, and for the `migrate` exit code to be 0.
   - Check `/api/ready` returns 200; register then log in over HTTP.
   - Check the worker stays healthy for ~30s.
   - Restart `backend` and `worker` and check they come back healthy; run `up` again (repeated startup, where migrate reports "already current").
   - No `down -v`.
4. **CI (`.github/workflows/ci.yml`):**
   - `migrations-postgres`: replace `alembic upgrade head` with `python -m app.migrate`; keep `alembic check` and the downgrade/upgrade round trip; add `TEST_POSTGRES_URL=postgresql+psycopg://ci:ci@localhost:5432/ci python -m pytest -q tests/test_postgres_lifecycle.py`.
   - `docker`: replace the single-container boot with `scripts/compose-smoke.sh` (real compose, PostgreSQL, all four services, `/api/ready`, auth, worker stability).
   - Required checks on `main` are unchanged (`frontend`, `backend`, `migrations-postgres`, `docker`, `journey`, `secrets`).
5. **Docs:**
   - Rewrite `docs/MIGRATIONS.md`: single authority, `python -m app.migrate`, Docker order, legacy adoption, "every migration must be idempotent" (enforced by a test), and recovering the user's stack without a reset.
   - `.env.example`: remove `GUESTLIFT_AUTO_CREATE_SCHEMA` (two lines); add `GUESTLIFT_SCHEMA_WAIT_SECONDS` and `GUESTLIFT_WORKER_HEARTBEAT_FILE`.
   - `README.md`: mention `python -m app.migrate` for non-Docker runs.
   - `.gitignore`: add `*.migrate.lock`.
6. **Isolated database verification:**
   - Create a separate compose project (`-p tablesignal-p0`, ports such as 3300/8300, its own fresh volume).
   - Start only `database`, then restore `user-db-backup.sql` into it with psql.
   - Run the full stack from this branch and confirm all four services are healthy, migrate reported "adopted a database created by an older version", and the counts are preserved (1 user, 6 sessions, 1 workspace, 28 canonical orders, now `public-demo`).
   - Register and log in a new account; check the revision is `0008`; restart twice.
   - **Do not touch the `guestlift` project or its volume.**
7. **Final checks:**
   - Full backend suite with `TEST_POSTGRES_URL`; frontend `npm test` and `npx tsc --noEmit`.
   - `scripts/journey.sh` locally, using `PYTHON=/Users/georgejiang/GuestLift/backend/.venv/bin/python` and `npm ci` in the worktree's `frontend/` first. Also `JOURNEY_AUTH_MODE=clerk scripts/journey.sh`; Clerk keys are in the main checkout's `.env`, so copy only those three variables or point the script at them.
   - Rerun the journey several times to show the startup race is gone.
8. **Ship:** delete this file; commit; `git push -u origin fix/p0-database`; report the CI results. **Do not merge PR #29 and do not merge into M4.** Tell the user the non-destructive command to fix their real stack: run `docker compose up -d --build` from a checkout of the fixed branch; the migrate service adopts their database in place, and their backup exists.

## Constraints from the user (still in force)

Never reset or delete databases or volumes, never `docker compose down -v`, no production Square or Stripe LIVE, don't merge PR #29, work only in this worktree and branch, stay on P0 (not P1, P2 or M6). Don't use Alembic stamping to hide unapplied schema changes.
