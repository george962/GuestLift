#!/usr/bin/env bash
# Compose smoke test (P0): the real stack — PostgreSQL, migrate, API, worker, frontend — starts in
# order, stays healthy, survives restarts, and a repeated `up` is a no-op for the schema.
# Usage: scripts/compose-smoke.sh                 project tablesignal-smoke on ports 3400/8400
#        SMOKE_PROJECT=name SMOKE_WEB_PORT=3300 SMOKE_API_PORT=8300 scripts/compose-smoke.sh
#        SMOKE_SKIP_BUILD=1 ...                   reuse images already built for this project
# It never removes containers or volumes (no `down -v`); stop the project yourself with
# `docker compose -p <project> stop`. It refuses the default `guestlift` project unless
# SMOKE_ALLOW_PROJECT=1, so it can't restart someone's working stack by accident.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${SMOKE_PROJECT:-tablesignal-smoke}"
export TABLESIGNAL_WEB_PORT="${SMOKE_WEB_PORT:-3400}" TABLESIGNAL_API_PORT="${SMOKE_API_PORT:-8400}"
API="http://127.0.0.1:$TABLESIGNAL_API_PORT" ORIGIN="http://localhost:$TABLESIGNAL_WEB_PORT"
if [ "$PROJECT" = guestlift ] && [ "${SMOKE_ALLOW_PROJECT:-0}" != 1 ]; then
  echo "Refusing to smoke-test the default 'guestlift' project (set SMOKE_ALLOW_PROJECT=1 to allow)."; exit 2
fi
dc() { docker compose -f "$ROOT/compose.yaml" -p "$PROJECT" "$@"; }
step() { echo; echo "== $*"; }
fail() { echo "FAIL: $*"; dc ps -a || true; dc logs --tail=60 migrate backend worker frontend || true; exit 1; }
cid() { dc ps -aq "$1"; }
health() { docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$(cid "$1")" 2>/dev/null || echo missing; }

wait_healthy() {  # wait_healthy <seconds> <service>...
  local limit="$1"; shift
  for _ in $(seq 1 "$limit"); do
    local all=1
    for s in "$@"; do [ "$(health "$s")" = healthy ] || all=0; done
    [ "$all" = 1 ] && { echo "healthy: $*"; return 0; }
    sleep 1
  done
  for s in "$@"; do echo "$s: $(health "$s")"; done
  fail "services not healthy within ${limit}s"
}

migrate_ok() {
  local state; state="$(docker inspect -f '{{.State.Status}} {{.State.ExitCode}}' "$(cid migrate)")"
  [ "$state" = "exited 0" ] || fail "migrate is '$state', expected 'exited 0'"
  echo "migrate: $(dc logs --no-log-prefix --tail=1 migrate)"
}

up() {
  if [ "${SMOKE_SKIP_BUILD:-0}" = 1 ]; then dc up -d; else dc up -d --build; fi
}

step "Start $PROJECT (web $TABLESIGNAL_WEB_PORT, api $TABLESIGNAL_API_PORT)"
up || fail "docker compose up failed"
wait_healthy 240 backend worker frontend
migrate_ok

step "API ready, schema at head"
curl -fsS "$API/api/ready" || fail "/api/ready is not 200"; echo

step "Register and sign in over HTTP"
email="smoke-$(date +%s)-$RANDOM@example.test" password="smoke-password-$RANDOM-ok"
body="{\"email\":\"$email\",\"password\":\"$password\"}"
jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT
curl -fsS -X POST "$API/api/local-auth/register" -H "Origin: $ORIGIN" -H 'Content-Type: application/json' -d "$body" >/dev/null \
  || fail "register failed"
curl -fsS -c "$jar" -X POST "$API/api/local-auth/login" -H "Origin: $ORIGIN" -H 'Content-Type: application/json' -d "$body" >/dev/null \
  || fail "login failed"
curl -fsS -b "$jar" "$API/api/local-auth/session" | grep -q '"authenticated":true' || fail "session not authenticated"
curl -fsS -b "$jar" "$API/api/saas/me" >/dev/null || fail "/api/saas/me failed"
echo "signed in as $email"

step "Worker stays healthy for 30s"
restarts="$(docker inspect -f '{{.RestartCount}}' "$(cid worker)")"
for _ in $(seq 1 30); do
  [ "$(docker inspect -f '{{.State.Running}}' "$(cid worker)")" = true ] || fail "worker stopped"
  sleep 1
done
[ "$(docker inspect -f '{{.RestartCount}}' "$(cid worker)")" = "$restarts" ] || fail "worker restarted"
[ "$(health worker)" = healthy ] || fail "worker is $(health worker)"
echo "worker: healthy, no restarts"

step "Restart backend and worker"
dc restart backend worker
wait_healthy 120 backend worker frontend
curl -fsS "$API/api/ready" >/dev/null || fail "/api/ready after restart"
curl -fsS -c "$jar" -X POST "$API/api/local-auth/login" -H "Origin: $ORIGIN" -H 'Content-Type: application/json' -d "$body" >/dev/null \
  || fail "login after restart failed"

step "Repeated up (migrate must find the schema already current)"
SMOKE_SKIP_BUILD=1 up || fail "second up failed"
wait_healthy 120 backend worker frontend
migrate_ok
dc logs --no-log-prefix --tail=1 migrate | grep -q 'already current' || fail "second migrate run changed the schema"

step "Compose smoke passed ($PROJECT)"
dc ps -a
