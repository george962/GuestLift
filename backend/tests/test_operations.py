import json
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import rate_limit
from app.logging_config import JsonFormatter
from app.main import app


def test_request_id_generated_and_echoed():
    c = TestClient(app)
    assert len(c.get('/api/health').headers['x-request-id']) == 32
    assert c.get('/api/health', headers={'X-Request-ID': 'abc-123'}).headers['x-request-id'] == 'abc-123'


def test_unsafe_request_id_replaced():
    r = TestClient(app).get('/api/health', headers={'X-Request-ID': 'bad id\nwith newline'})
    assert r.headers['x-request-id'] != 'bad id\nwith newline' and len(r.headers['x-request-id']) == 32


def test_json_log_format():
    rec = logging.LogRecord('guestlift', logging.INFO, __file__, 1, 'hello %s', ('x',), None)
    rec.request_id = 'r1'
    assert json.loads(JsonFormatter().format(rec))['msg'] == 'hello x'


def test_ai_rate_limit_per_user_and_window(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_AI_QUESTIONS_PER_HOUR', '2')
    rate_limit.reset()
    rate_limit.check('u1', now=0); rate_limit.check('u1', now=1)
    with pytest.raises(HTTPException) as e:
        rate_limit.check('u1', now=2)
    assert e.value.status_code == 429 and e.value.headers['Retry-After']
    rate_limit.check('u2', now=2)            # other users unaffected
    rate_limit.check('u1', now=3601)         # window slides
    rate_limit.reset()


@pytest.mark.parametrize('path', ['/api/saas/analyst', '/api/intelligence/ask'])
def test_ai_endpoints_return_429_when_over_limit(monkeypatch, path):
    from app.local_auth import authenticated_subject
    monkeypatch.setenv('GUESTLIFT_AI_QUESTIONS_PER_HOUR', '1')
    rate_limit.reset()
    rate_limit.check('limited-user')  # use up the allowance
    app.dependency_overrides[authenticated_subject] = lambda: 'limited-user'
    try:
        r = TestClient(app).post(path, json={'question': 'What changed this week?'})
        assert r.status_code == 429 and 'Retry-After' in r.headers
    finally:
        app.dependency_overrides.clear()
        rate_limit.reset()
