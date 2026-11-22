from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_health_reports_demo_flag(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_ENABLE_DEMO_ENDPOINTS', raising=False)
    body = TestClient(app).get('/api/health').json()
    assert body['status'] == 'ok' and body['demo_endpoints'] is False


def test_ready_checks_database():
    r = TestClient(app).get('/api/ready')
    assert r.status_code == 200 and r.json() == {'status': 'ready'}


def test_ready_returns_503_when_database_down(monkeypatch):
    class Broken:
        def connect(self):
            raise RuntimeError('db down')
    monkeypatch.setattr(main, 'engine', Broken())
    assert TestClient(app).get('/api/ready').status_code == 503
