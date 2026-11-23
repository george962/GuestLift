"""Billing webhook guarantees: signed, test-mode only, and idempotent."""
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import saas
from app.database import Base
from app.main import app
from app import membership

SECRET = 'whsec_test_guarantees'


def _signed(event: dict, secret: str = SECRET):
    body = json.dumps(event)
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f'{ts}.{body}'.encode(), hashlib.sha256).hexdigest()
    return body, {'stripe-signature': f't={ts},v1={sig}', 'content-type': 'application/json'}


def _event(event_id='evt_test_1', livemode=False, kind='invoice.paid'):
    return {'id': event_id, 'object': 'event', 'type': kind, 'livemode': livemode,
            'data': {'object': {'id': 'in_test_1', 'object': 'invoice'}}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'wh.sqlite'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    monkeypatch.setattr(saas, 'engine', engine)
    monkeypatch.setattr(membership, 'engine', engine)
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', SECRET)
    yield TestClient(app), engine
    engine.dispose()


def test_bad_signature_rejected(client):
    c, _ = client
    body, headers = _signed(_event(), secret='whsec_wrong')
    assert c.post('/api/saas/billing/webhook', content=body, headers=headers).status_code == 400


def test_live_mode_events_rejected(client):
    c, engine = client
    body, headers = _signed(_event(livemode=True))
    r = c.post('/api/saas/billing/webhook', content=body, headers=headers)
    assert r.status_code == 400 and 'Live' in r.json()['detail']
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(saas.BillingEvent)) == 0


def test_replayed_event_processed_once(client):
    c, engine = client
    body, headers = _signed(_event('evt_replay'))
    first = c.post('/api/saas/billing/webhook', content=body, headers=headers)
    second = c.post('/api/saas/billing/webhook', content=body, headers=headers)
    assert first.json() == {'received': True}
    assert second.json() == {'received': True, 'duplicate': True}
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(saas.BillingEvent)) == 1


def test_missing_webhook_secret_fails_closed(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv('STRIPE_WEBHOOK_SECRET')
    body, headers = _signed(_event())
    assert c.post('/api/saas/billing/webhook', content=body, headers=headers).status_code == 503
