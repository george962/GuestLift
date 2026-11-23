import pytest


@pytest.fixture(autouse=True)
def _enable_demo_endpoints(monkeypatch):
    """Existing tests exercise the demo API; production default is OFF."""
    monkeypatch.setenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', '1')
    # Legacy contract tests use the original behavior.
    # Dedicated v0.13 tests explicitly enable selection.
    monkeypatch.setenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0')


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Each test starts with empty in-memory limiters (sign-up throttle, AI question cap)."""
    from app import local_auth, rate_limit
    with local_auth._lock:
        local_auth._attempts.clear()
    rate_limit.reset()
    yield
