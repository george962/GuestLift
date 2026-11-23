#!/usr/bin/env bash
# M1 golden-path journey: mock Square + backend + frontend + Playwright, all on localhost.
# Usage: scripts/journey.sh                     local development accounts
#        JOURNEY_AUTH_MODE=clerk scripts/journey.sh   real Clerk development instance (M2)
# Needs backend/.venv with requirements and frontend/node_modules. Clerk mode reads
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY and GUESTLIFT_OIDC_ISSUER from the
# environment, or from the repo's .env when unset.
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

MODE="${JOURNEY_AUTH_MODE:-local}"
api_auth=() web_auth=()
if [ "$MODE" = clerk ]; then
  for k in NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY CLERK_SECRET_KEY GUESTLIFT_OIDC_ISSUER; do
    if [ -z "${!k:-}" ] && [ -f "$ROOT/.env" ]; then
      v="$(grep -E "^$k=" "$ROOT/.env" | head -1 | cut -d= -f2-)"; export "$k=$v"
    fi
    [ -n "${!k:-}" ] || { echo "Clerk mode needs $k (environment or .env)."; exit 1; }
  done
  export CLERK_PUBLISHABLE_KEY="$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
  api_auth=(GUESTLIFT_AUTH_MODE=oidc GUESTLIFT_OIDC_ISSUER="$GUESTLIFT_OIDC_ISSUER"
            GUESTLIFT_OIDC_JWKS_URL="${GUESTLIFT_OIDC_ISSUER%/}/.well-known/jwks.json"
            GUESTLIFT_OIDC_AUTHORIZED_PARTIES="http://localhost:$WEB_PORT")
  web_auth=(NEXT_PUBLIC_AUTH_MODE=clerk NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
fi

cd "$ROOT/backend"
CRED_KEY="$("$PY" -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
"$PY" -m uvicorn mock_square.app:app --port "$MOCK_PORT" > "$WORK/mock.log" 2>&1 & pids+=($!)
env ${api_auth[@]+"${api_auth[@]}"} DATABASE_URL="sqlite:///$WORK/journey.db" \
  GUESTLIFT_APP_URL="http://localhost:$WEB_PORT" GUESTLIFT_ALLOWED_ORIGINS="http://localhost:$WEB_PORT" \
  SQUARE_API_BASE_URL="http://localhost:$MOCK_PORT" \
  SQUARE_SANDBOX_APP_ID=mock-app-id SQUARE_SANDBOX_APP_SECRET=mock-app-secret \
  SQUARE_SANDBOX_REDIRECT_URI="http://localhost:$API_PORT/api/integrations/square/oauth/callback" \
  TABLESIGNAL_CREDENTIAL_KEY="$CRED_KEY" \
  TABLESIGNAL_SANDBOX_LOCATION_BILLING=1 \
  "$PY" -m uvicorn app.main:app --port "$API_PORT" > "$WORK/api.log" 2>&1 & pids+=($!)
# The background sync worker shares the API's settings (M3).
env ${api_auth[@]+"${api_auth[@]}"} DATABASE_URL="sqlite:///$WORK/journey.db" SQUARE_API_BASE_URL="http://localhost:$MOCK_PORT" \
  SQUARE_SANDBOX_APP_ID=mock-app-id SQUARE_SANDBOX_APP_SECRET=mock-app-secret TABLESIGNAL_SANDBOX_LOCATION_BILLING=1 \
  TABLESIGNAL_CREDENTIAL_KEY="$CRED_KEY" GUESTLIFT_WORKER_IDLE_SECONDS=1 \
  "$PY" -m app.worker > "$WORK/worker.log" 2>&1 & pids+=($!)

cd "$ROOT/frontend"
env ${web_auth[@]+"${web_auth[@]}"} NEXT_PUBLIC_GUESTLIFT_API_URL="http://localhost:$API_PORT" NEXT_PUBLIC_SQUARE_AUTHORIZE_ORIGIN="http://localhost:$MOCK_PORT" \
  npx next build > "$WORK/build.log" 2>&1 || { cat "$WORK/build.log"; exit 1; }
npx next start --port "$WEB_PORT" > "$WORK/web.log" 2>&1 & pids+=($!)

wait_for "http://localhost:$MOCK_PORT/__mock/truth"
wait_for "http://localhost:$API_PORT/api/ready"
wait_for "http://localhost:$WEB_PORT/"
JOURNEY_AUTH_MODE="$MODE" JOURNEY_BASE_URL="http://localhost:$WEB_PORT" MOCK_SQUARE_URL="http://localhost:$MOCK_PORT" \
  npx playwright test e2e/journey.spec.ts "$@" || { echo '--- api.log ---'; tail -40 "$WORK/api.log"; echo '--- worker.log ---'; tail -20 "$WORK/worker.log"; exit 1; }
kill -0 "${pids[2]}" 2>/dev/null || { echo 'The sync worker exited during the journey:'; cat "$WORK/worker.log"; exit 1; }
