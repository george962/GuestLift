#!/usr/bin/env bash
# M1 golden-path journey: mock Square + backend + frontend + Playwright, all on localhost.
# Usage: scripts/journey.sh   (needs backend/.venv with requirements and frontend/node_modules)
# Ports default away from docker compose (3000/8000) so both can run at once.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_PORT="${WEB_PORT:-3100}" API_PORT="${API_PORT:-8200}" MOCK_PORT="${MOCK_PORT:-8100}"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"
WORK="$(mktemp -d)"
pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT

wait_for() { for _ in $(seq 1 60); do curl -fsS "$1" >/dev/null 2>&1 && return 0; sleep 1; done; echo "Timed out waiting for $1"; cat "$WORK"/*.log; exit 1; }

cd "$ROOT/backend"
"$PY" -m uvicorn mock_square.app:app --port "$MOCK_PORT" > "$WORK/mock.log" 2>&1 & pids+=($!)
env DATABASE_URL="sqlite:///$WORK/journey.db" \
  GUESTLIFT_APP_URL="http://localhost:$WEB_PORT" GUESTLIFT_ALLOWED_ORIGINS="http://localhost:$WEB_PORT" \
  SQUARE_API_BASE_URL="http://localhost:$MOCK_PORT" \
  SQUARE_SANDBOX_APP_ID=mock-app-id SQUARE_SANDBOX_APP_SECRET=mock-app-secret \
  SQUARE_SANDBOX_REDIRECT_URI="http://localhost:$API_PORT/api/integrations/square/oauth/callback" \
  TABLESIGNAL_CREDENTIAL_KEY="$("$PY" -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')" \
  TABLESIGNAL_SANDBOX_LOCATION_BILLING=1 \
  "$PY" -m uvicorn app.main:app --port "$API_PORT" > "$WORK/api.log" 2>&1 & pids+=($!)

cd "$ROOT/frontend"
NEXT_PUBLIC_GUESTLIFT_API_URL="http://localhost:$API_PORT" NEXT_PUBLIC_SQUARE_AUTHORIZE_ORIGIN="http://localhost:$MOCK_PORT" \
  npx next build > "$WORK/build.log" 2>&1 || { cat "$WORK/build.log"; exit 1; }
npx next start --port "$WEB_PORT" > "$WORK/web.log" 2>&1 & pids+=($!)

wait_for "http://localhost:$MOCK_PORT/__mock/truth"
wait_for "http://localhost:$API_PORT/api/ready"
wait_for "http://localhost:$WEB_PORT/"
JOURNEY_BASE_URL="http://localhost:$WEB_PORT" MOCK_SQUARE_URL="http://localhost:$MOCK_PORT" \
  npx playwright test e2e/journey.spec.ts "$@" || { echo '--- api.log ---'; tail -40 "$WORK/api.log"; exit 1; }
