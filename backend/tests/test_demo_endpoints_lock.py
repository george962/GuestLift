import pytest
from fastapi.testclient import TestClient

from app.main import app

LOCKED = [
    ('post', '/api/import/toast'),
    ('get', '/api/metrics'),
    ('get', '/api/imports'),
    ('get', '/api/campaigns/report'),
    ('get', '/api/customers/summary'),
    ('post', '/api/campaigns/demo/load'),
]


@pytest.mark.parametrize('method,path', LOCKED)
def test_demo_endpoints_are_404_by_default(monkeypatch, method, path):
    monkeypatch.delenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', raising=False)
    client = TestClient(app)
    assert getattr(client, method)(path).status_code == 404


def test_health_stays_open_when_locked(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', raising=False)
    assert TestClient(app).get('/api/health').status_code == 200
