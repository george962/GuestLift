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
