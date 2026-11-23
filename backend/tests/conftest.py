import httpx
import pytest

_RealClient = httpx.Client  # captured before any test monkeypatches httpx.Client


@pytest.fixture(autouse=True)
def _enable_demo_endpoints(monkeypatch):
    """Existing tests exercise the demo API; production default is OFF."""
    monkeypatch.setenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', '1')
    # Legacy contract tests use the original behavior.
    # Dedicated v0.13 tests explicitly enable selection.
    monkeypatch.setenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0')


@pytest.fixture(autouse=True)
def _no_real_email(monkeypatch):
    """Tests never reach Resend, even if the developer's shell has real keys. Tests that need a
    provider set fake keys and replace emailer._client with an httpx.MockTransport."""
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('EMAIL_FROM', raising=False)
    monkeypatch.setenv('GUESTLIFT_EMAIL_SEND_INTERVAL_SECONDS', '0')
    from app import emailer

    def refuse(request):
        raise AssertionError(f'a test tried to send real email to {request.url}')
    monkeypatch.setattr(emailer, '_client', lambda: _RealClient(transport=httpx.MockTransport(refuse)))


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Each test starts with empty in-memory limiters (sign-up throttle, AI question cap)."""
    from app import local_auth, rate_limit
    with local_auth._lock:
        local_auth._attempts.clear()
    rate_limit.reset()
    yield
