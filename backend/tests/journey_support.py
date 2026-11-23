"""Shared harness: real app + local auth + the mock Square API in-process."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import connections, decisions, intelligence, local_auth, saas
from app.database import Base
from app.main import app
from mock_square import app as mock
from app import membership

ORIGIN = {'Origin': 'http://localhost:3000'}
MOCK = 'http://mock-square.test'


@pytest.fixture
def harness(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'journey.sqlite'), connect_args={'check_same_thread': False})
    for module in (saas, local_auth, connections, decisions, intelligence, membership):
        monkeypatch.setattr(module, 'engine', engine)
    Base.metadata.create_all(engine)
    env = {'SQUARE_API_BASE_URL': MOCK, 'TABLESIGNAL_CREDENTIAL_KEY': Fernet.generate_key().decode(),
           'SQUARE_SANDBOX_APP_ID': 'mock-app-id', 'SQUARE_SANDBOX_APP_SECRET': 'mock-app-secret',
           'SQUARE_SANDBOX_REDIRECT_URI': 'http://testserver/api/integrations/square/oauth/callback',
           'TABLESIGNAL_SANDBOX_LOCATION_BILLING': '1'}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    mock_client = TestClient(mock.app)
    # Backend -> Square calls go to the in-process mock instead of the network.
    monkeypatch.setattr(connections.httpx, 'Client', lambda **kw: TestClient(mock.app))
    mock._state['faults'] = []
    yield Harness(TestClient(app), mock_client)
    engine.dispose()


class Harness:
    def __init__(self, api: TestClient, square: TestClient):
        self.api, self.square = api, square

    def truth(self) -> dict:
        return self.square.get('/__mock/truth').json()

    def post(self, path, payload=None):
        token = self.api.get('/api/local-auth/session').json()['csrf_token']
        return self.api.post(path, json=payload, headers={**ORIGIN, 'X-CSRF-Token': token})

    def get(self, path):
        return self.api.get(path)

    def sign_up(self, email='owner@harbor.test'):
        r = self.api.post('/api/local-auth/register', json={'email': email, 'password': 'a-long-journey-password'},
                          headers=ORIGIN)
        assert r.status_code == 201, r.text

    def connect_oauth(self):
        start = self.post('/api/integrations/square/oauth/start')
        assert start.status_code == 200, start.text
        url = urlparse(start.json()['url'])
        authorize = self.square.get(url.path + '?' + url.query, follow_redirects=False)
        assert authorize.status_code == 302
        q = parse_qs(urlparse(authorize.headers['location']).query)
        cb = self.api.get('/api/integrations/square/oauth/callback',
                          params={'code': q['code'][0], 'state': q['state'][0]}, follow_redirects=False)
        assert cb.status_code == 303 and cb.headers['location'].endswith('/connections?square=connected'), cb.text

    def select_eligible(self):
        locs = self.get('/api/integrations/square/locations').json()
        ids = [l['id'] for l in locs['locations'] if l['eligible']]
        r = self.post('/api/integrations/square/locations/selection', {'location_ids': ids})
        assert r.status_code == 200, r.text
        return ids
