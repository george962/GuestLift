import importlib

import pytest
from fastapi.testclient import TestClient

from app import config

SAFE = {
    'GUESTLIFT_ENV': 'production',
    'DATABASE_URL': 'postgresql+psycopg://u:p@db.internal/app',
    'GUESTLIFT_APP_URL': 'https://app.example.com',
    'GUESTLIFT_ALLOWED_ORIGINS': 'https://app.example.com',
    'TABLESIGNAL_CREDENTIAL_KEY': 'k',
}


@pytest.fixture
def prod(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', raising=False)
    monkeypatch.delenv('TABLESIGNAL_ENABLE_DEMO_RESET', raising=False)
    monkeypatch.delenv('SQUARE_API_BASE_URL', raising=False)
    for k, v in SAFE.items():
        monkeypatch.setenv(k, v)
    return monkeypatch


def test_not_production_has_no_problems(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_ENV', raising=False)
    assert config.production_config_problems() == []


def test_safe_production_config_passes(prod):
    config.validate_production_config()


@pytest.mark.parametrize('key,value,needle', [
    ('DATABASE_URL', 'sqlite:///./x.db', 'DATABASE_URL'),
    ('GUESTLIFT_APP_URL', 'http://app.example.com', 'GUESTLIFT_APP_URL'),
    ('GUESTLIFT_ALLOWED_ORIGINS', 'http://app.example.com', 'GUESTLIFT_ALLOWED_ORIGINS'),
    ('GUESTLIFT_ALLOWED_ORIGINS', '', 'GUESTLIFT_ALLOWED_ORIGINS'),
    ('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', '1', 'GUESTLIFT_ENABLE_DEMO_ENDPOINTS'),
    ('TABLESIGNAL_ENABLE_DEMO_RESET', '1', 'TABLESIGNAL_ENABLE_DEMO_RESET'),
    ('TABLESIGNAL_CREDENTIAL_KEY', '', 'TABLESIGNAL_CREDENTIAL_KEY'),
    ('SQUARE_API_BASE_URL', 'http://127.0.0.1:8100', 'SQUARE_API_BASE_URL'),
])
def test_each_unsafe_setting_blocks_startup(prod, key, value, needle):
    prod.setenv(key, value)
    with pytest.raises(RuntimeError, match=needle):
        config.validate_production_config()


def test_security_headers_on_api_responses():
    from app.main import app
    r = TestClient(app).get('/api/health')
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['x-frame-options'] == 'DENY'
    assert r.headers['cache-control'] == 'no-store'


def test_production_hides_api_docs_and_sets_hsts(prod):
    import app.main as main
    try:
        reloaded = importlib.reload(main)
        client = TestClient(reloaded.app)  # no `with`: skip lifespan/DB startup
        assert client.get('/docs').status_code == 404
        assert client.get('/openapi.json').status_code == 404
        assert 'max-age' in client.get('/api/health').headers['strict-transport-security']
    finally:
        prod.delenv('GUESTLIFT_ENV')
        importlib.reload(main)
