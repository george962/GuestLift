import pytest


@pytest.fixture(autouse=True)
def _enable_demo_endpoints(monkeypatch):
    """Existing tests exercise the demo API; production default is OFF."""
    monkeypatch.setenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', '1')
    # Legacy contract tests use the original behavior.
    # Dedicated v0.13 tests explicitly enable selection.
    monkeypatch.setenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0')
