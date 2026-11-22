"""Environment-driven settings shared across the backend.

Values are read at call time (not import time) so tests and deployments can
change them without re-importing modules. Defaults match the local
developer preview, so nothing changes unless you set the variables.
"""
from __future__ import annotations

import os

_DEFAULT_APP_URL = 'http://localhost:3000'
_DEFAULT_ORIGINS = ('http://localhost:3000', 'http://127.0.0.1:3000')


def app_url() -> str:
    """Public base URL of the frontend (no trailing slash)."""
    return os.getenv('GUESTLIFT_APP_URL', _DEFAULT_APP_URL).rstrip('/')


def allowed_origins() -> list[str]:
    """Browser origins allowed for CORS and the CSRF origin check.

    Set GUESTLIFT_ALLOWED_ORIGINS to a comma-separated list, e.g.
    "https://app.example.com,https://www.example.com".
    """
    raw = os.getenv('GUESTLIFT_ALLOWED_ORIGINS', '')
    origins = [o.strip().rstrip('/') for o in raw.split(',') if o.strip()]
    return origins or list(_DEFAULT_ORIGINS)


def demo_endpoints_enabled() -> bool:
    """Shared-dataset demo endpoints (import, upload, metrics, campaigns).

    These have no login and no per-workspace scoping, so they are OFF unless
    GUESTLIFT_ENABLE_DEMO_ENDPOINTS=1. compose.yaml enables them for local use.
    """
    return os.getenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS') == '1'


# --- Authentication -------------------------------------------------------------
# GUESTLIFT_AUTH_MODE=local  (default) cookie sessions from the built-in dev accounts
# GUESTLIFT_AUTH_MODE=oidc   bearer tokens from a managed identity provider
#   GUESTLIFT_OIDC_ISSUER    exact `iss` the provider puts in tokens, e.g. https://example.clerk.accounts.dev
#   GUESTLIFT_OIDC_JWKS_URL  where the provider publishes signing keys
#   GUESTLIFT_OIDC_AUDIENCE  optional; when set, tokens must carry this `aud`
#   GUESTLIFT_OIDC_AUTHORIZED_PARTIES  optional, comma-separated frontend origins; when set, a token's
#                            `azp` claim (if present) must be one of them (Clerk recommends this)
# GUESTLIFT_ENV=production refuses to start with local accounts.

def auth_mode() -> str:
    mode = os.getenv('GUESTLIFT_AUTH_MODE', 'local').strip().lower()
    return mode if mode in ('local', 'oidc') else 'invalid:' + mode


def oidc_settings() -> dict:
    return {
        'issuer': os.getenv('GUESTLIFT_OIDC_ISSUER', '').strip(),
        'jwks_url': os.getenv('GUESTLIFT_OIDC_JWKS_URL', '').strip(),
        'audience': os.getenv('GUESTLIFT_OIDC_AUDIENCE', '').strip(),
        'authorized_parties': [p.strip().rstrip('/') for p in os.getenv('GUESTLIFT_OIDC_AUTHORIZED_PARTIES', '').split(',') if p.strip()],
    }


def is_production() -> bool:
    return os.getenv('GUESTLIFT_ENV', '').strip().lower() == 'production'


def validate_auth_config() -> None:
    """Fail at startup, with a clear message, instead of failing open or at first login."""
    mode = auth_mode()
    if mode.startswith('invalid:'):
        raise RuntimeError(f"GUESTLIFT_AUTH_MODE must be 'local' or 'oidc', got {mode[8:]!r}.")
    if mode == 'local' and is_production():
        raise RuntimeError('GUESTLIFT_ENV=production requires GUESTLIFT_AUTH_MODE=oidc. '
                           'The built-in local accounts are for development only.')
    if mode == 'oidc':
        s = oidc_settings()
        missing = [name for name, key in (('GUESTLIFT_OIDC_ISSUER', 'issuer'), ('GUESTLIFT_OIDC_JWKS_URL', 'jwks_url')) if not s[key]]
        if missing:
            raise RuntimeError('GUESTLIFT_AUTH_MODE=oidc requires ' + ' and '.join(missing) + '.')
        if is_production() and not s['jwks_url'].startswith('https://'):
            raise RuntimeError('GUESTLIFT_OIDC_JWKS_URL must be https:// in production.')


def production_config_problems() -> list[str]:
    """Settings that would make a GUESTLIFT_ENV=production deployment unsafe. Empty outside production."""
    if not is_production():
        return []
    env = os.getenv
    problems = []
    if env('DATABASE_URL', '').startswith('sqlite') or not env('DATABASE_URL'):
        problems.append('DATABASE_URL must point at a managed PostgreSQL database, not SQLite.')
    if not app_url().startswith('https://'):
        problems.append('GUESTLIFT_APP_URL must be https://.')
    if not env('GUESTLIFT_ALLOWED_ORIGINS', '').strip() or any(not o.startswith('https://') for o in allowed_origins()):
        problems.append('GUESTLIFT_ALLOWED_ORIGINS must be set explicitly and every origin must be https://.')
    if demo_endpoints_enabled():
        problems.append('GUESTLIFT_ENABLE_DEMO_ENDPOINTS must be unset (unauthenticated shared demo API).')
    if env('TABLESIGNAL_ENABLE_DEMO_RESET') == '1':
        problems.append('TABLESIGNAL_ENABLE_DEMO_RESET must be unset (unauthenticated data reset).')
    if env('GUESTLIFT_AUTO_CREATE_SCHEMA', '1') != '0':
        problems.append('GUESTLIFT_AUTO_CREATE_SCHEMA=0 is required; run `alembic upgrade head` instead.')
    if not env('TABLESIGNAL_CREDENTIAL_KEY'):
        problems.append('TABLESIGNAL_CREDENTIAL_KEY is required to encrypt stored POS tokens.')
    return problems


def validate_production_config() -> None:
    problems = production_config_problems()
    if problems:
        raise RuntimeError('Refusing to start in production:\n- ' + '\n- '.join(problems))
