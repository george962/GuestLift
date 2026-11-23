#!/usr/bin/env bash
# Regenerates backend/tests/fixtures/legacy_schemas/{v013_pre_m2,m3}.{sqlite,postgres}.sql: the exact
# schemas that OLDER app versions created with their startup create_all(), on SQLite and PostgreSQL.
# Schema only, no data. Needs git history, docker, and a Python env with backend/requirements.lock.
# Usage: PYTHON=backend/.venv/bin/python scripts/make-legacy-schema-fixtures.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"
OUT="$ROOT/backend/tests/fixtures/legacy_schemas"
WORK="$(mktemp -d)"
PG=legacy-fixture-pg
PORT=55499
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT
mkdir -p "$OUT"
docker run -d --rm --name "$PG" -e POSTGRES_USER=fx -e POSTGRES_PASSWORD=fx -e POSTGRES_DB=fx \
  -p "127.0.0.1:$PORT:5432" postgres:16 >/dev/null
for _ in $(seq 1 30); do docker exec "$PG" pg_isready -q -U fx && break; sleep 1; done
sleep 2

# name:commit  (v013_pre_m2 = main just before M2 merged; m3 = the M3 merge, PR #27)
for spec in v013_pre_m2:4a62f4f m3:7537614; do
  name="${spec%%:*}"
  commit="${spec##*:}"
  src="$WORK/$name"
  mkdir -p "$src"
  (cd "$ROOT" && git archive "$commit" backend) | tar -x -C "$src"

  (cd "$src/backend" && DATABASE_URL="sqlite:///$WORK/$name.db" "$PY" -c 'import app.main; from app.database import init_db; init_db()')
  "$PY" - "$WORK/$name.db" "$OUT/$name.sqlite.sql" "$commit" <<'PYEOF'
import sqlite3, sys
db, out, commit = sys.argv[1:]
lines = [l for l in sqlite3.connect(db).iterdump()
         if not l.startswith('INSERT') and l not in ('BEGIN TRANSACTION;', 'COMMIT;')]
header = f'-- Schema created by create_all() at commit {commit} (scripts/make-legacy-schema-fixtures.sh)\n'
open(out, 'w').write(header + '\n'.join(lines) + '\n')
PYEOF

  docker exec "$PG" psql -U fx -d fx -qc "CREATE DATABASE $name"
  (cd "$src/backend" && DATABASE_URL="postgresql+psycopg://fx:fx@127.0.0.1:$PORT/$name" "$PY" -c 'import app.main; from app.database import init_db; init_db()')
  {
    echo "-- Schema created by create_all() at commit $commit (scripts/make-legacy-schema-fixtures.sh)"
    docker exec "$PG" pg_dump -U fx -d "$name" --schema-only --no-owner --no-privileges | grep -v '^\\'
  } > "$OUT/$name.postgres.sql"
  echo "generated $name ($commit)"
done
