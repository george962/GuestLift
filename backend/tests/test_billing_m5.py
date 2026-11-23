"""M5: entitlements, trial, dunning and paid-route enforcement."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import billing, connections, saas, square_sync, worker
from app.main import app
from journey_support import harness  # noqa: F401

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def ws(**kw):
    base = dict(subscription_status='none', stripe_subscription_id=None, current_period_end=None,
                cancel_at_period_end=False, payment_failed_at=None, trial_ends_at=None)
    return SimpleNamespace(**{**base, **kw})


STATES = {
    # name: (workspace fields, expected state, expected access)
    'setup': ({}, 'setup', 'setup'),
    'trial': ({'trial_ends_at': (NOW + timedelta(days=3)).isoformat()}, 'trial', 'full'),
    'trial_expired': ({'trial_ends_at': (NOW - timedelta(seconds=1)).isoformat()}, 'trial_expired', 'read_only'),
    'active': ({'subscription_status': 'active', 'stripe_subscription_id': 'sub_1'}, 'active', 'full'),
    'canceling': ({'subscription_status': 'active', 'stripe_subscription_id': 'sub_1', 'cancel_at_period_end': True,
                   'current_period_end': int((NOW + timedelta(days=9)).timestamp())}, 'canceling', 'full'),
    'past_due_grace': ({'subscription_status': 'past_due', 'stripe_subscription_id': 'sub_1',
                        'payment_failed_at': (NOW - timedelta(days=2)).isoformat()}, 'past_due', 'full'),
    'past_due_over': ({'subscription_status': 'past_due', 'stripe_subscription_id': 'sub_1',
                       'payment_failed_at': (NOW - timedelta(days=8)).isoformat()}, 'read_only', 'read_only'),
    'unpaid': ({'subscription_status': 'unpaid', 'stripe_subscription_id': 'sub_1'}, 'read_only', 'read_only'),
    'canceled': ({'subscription_status': 'canceled', 'stripe_subscription_id': 'sub_1'}, 'read_only', 'read_only'),
    'incomplete_checkout': ({'subscription_status': 'incomplete', 'stripe_subscription_id': 'sub_1',
                             'trial_ends_at': (NOW + timedelta(days=3)).isoformat()}, 'trial', 'full'),
}


@pytest.mark.parametrize('name', STATES)
def test_entitlement_rules(name):
    fields, state, access = STATES[name]
    e = billing.entitlement(ws(**fields), now=NOW)
    assert (e['state'], e['access']) == (state, access), e
    assert e['message']


def test_trial_days_left_and_message():
    e = billing.entitlement(ws(trial_ends_at=(NOW + timedelta(days=3, hours=1)).isoformat()), now=NOW)
    assert e['days_left'] == 4 and 'No card' in e['message']


# Every paid route, by the dependency that guards it. A new paid route must be added here.
PAID = {'POST /api/saas/analyst', 'POST /api/intelligence/ask', 'POST /api/decisions/plans',
        'POST /api/decisions/plans/{plan_id}/status'}
SYNC = {'POST /api/integrations/square/sync'}


def _routes(routes):
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, 'original_router'):
            yield from _routes(r.original_router.routes)


def _uses(dependant, fn) -> bool:
    return any(d.call is fn or _uses(d, fn) for d in dependant.dependencies)


def test_paid_route_inventory():
    routes = list(_routes(app.routes))
    paid = {f'{sorted(r.methods)[0]} {r.path}' for r in routes if _uses(r.dependant, billing.paid_subject)}
    sync = {f'{sorted(r.methods)[0]} {r.path}' for r in routes if _uses(r.dependant, billing.sync_subject)}
    assert paid == PAID and sync == SYNC


def _set(h, **fields):
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        for k, v in {'subscription_status': 'none', 'stripe_subscription_id': None, 'cancel_at_period_end': False,
                     'payment_failed_at': None, 'trial_ends_at': None, 'current_period_end': None, **fields}.items():
            setattr(w, k, v)
        db.commit()


PLAN = {'title': 'Matrix plan', 'objective': 'returning_guests', 'offer_type': 'percent', 'offer_value': 10,
        'target_redemptions': 40, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35}


def test_every_state_against_every_paid_endpoint(harness):
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    assert h.post('/api/integrations/square/sync').status_code == 200
    plan_id = h.post('/api/decisions/plans', PLAN).json()['plan']['id']  # trial started by the sync
    now = datetime.now(timezone.utc)
    calls = {
        'POST /api/saas/analyst': lambda: h.post('/api/saas/analyst', {'question': 'Summarize my sales'}),
        'POST /api/intelligence/ask': lambda: h.post('/api/intelligence/ask', {'question': 'What changed?'}),
        'POST /api/decisions/plans': lambda: h.post('/api/decisions/plans', PLAN),
        'POST /api/decisions/plans/{plan_id}/status': lambda: h.post(f'/api/decisions/plans/{plan_id}/status', {'status': 'planned'}),
        'POST /api/integrations/square/sync': lambda: h.post('/api/integrations/square/sync'),
    }
    assert set(calls) == PAID | SYNC
    for name, (fields, _, access) in STATES.items():
        shifted = {k: (v if not isinstance(v, str) or 'T' not in v else
                       (now + (datetime.fromisoformat(v) - NOW)).isoformat()) for k, v in fields.items()}
        if 'current_period_end' in shifted:
            shifted['current_period_end'] = int(now.timestamp()) + 9 * 86400
        _set(h, **shifted)
        for route, call in calls.items():
            allowed = access == 'full' or (route in SYNC and access == 'setup')
            r = call()
            if allowed:
                assert r.status_code != 402, f'{name}: {route} was refused: {r.text}'
            else:
                assert r.status_code == 402, f'{name}: {route} should need a trial or subscription, got {r.status_code}'
                assert r.headers.get('x-entitlement-state')


def test_trial_starts_after_first_complete_sync_only_once(harness, monkeypatch):
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    monkeypatch.setenv('GUESTLIFT_SYNC_INLINE_SECONDS', '0')
    assert h.post('/api/integrations/square/sync').status_code == 202  # partial: no trial yet
    assert h.get('/api/saas/me').json()['workspace']['entitlement']['state'] == 'setup'
    monkeypatch.setattr(worker, 'engine', connections.engine)
    while worker.run_once(slice_seconds=30):
        pass
    e = h.get('/api/saas/me').json()['workspace']['entitlement']
    assert e['state'] == 'trial' and e['days_left'] == 14
    with Session(saas.engine) as db:
        first = db.scalar(select(saas.Workspace)).trial_ends_at
    monkeypatch.setenv('GUESTLIFT_SYNC_INLINE_SECONDS', '20')
    h.post('/api/integrations/square/sync')
    with Session(saas.engine) as db:
        assert db.scalar(select(saas.Workspace)).trial_ends_at == first  # never restarts


def test_worker_pauses_updates_for_read_only_workspaces(harness):
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    h.post('/api/integrations/square/sync')
    later = int(time.time()) + square_sync.sync_interval_seconds() + 60
    _set(h, trial_ends_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    with Session(connections.engine) as db:
        assert worker.schedule(db, now=later) == 0
    _set(h, trial_ends_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    with Session(connections.engine) as db:
        assert worker.schedule(db, now=later) == 1


def _stripe_event(kind, obj, secret='whsec_m5'):
    body = json.dumps({'id': f'evt_{kind}_{time.time_ns()}', 'object': 'event', 'type': kind, 'livemode': False,
                       'data': {'object': obj}})
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f'{ts}.{body}'.encode(), hashlib.sha256).hexdigest()
    return body, {'stripe-signature': f't={ts},v1={sig}', 'content-type': 'application/json'}


def test_failed_payment_grace_then_recovery_via_webhooks(harness, monkeypatch):
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    h.post('/api/integrations/square/sync')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_m5')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID', 'price_test_growth')
    from app.location_entitlements import snapshot
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        conn = db.scalar(select(connections.SquareConnection))
        snap = snapshot(db, w.id, conn.merchant_id)
        wid = w.id
        w.stripe_customer_id, w.stripe_subscription_id, w.subscription_status = 'cus_m5', 'sub_m5', 'active'
        db.commit()
    state = {'status': 'past_due'}

    def fake_retrieve(sub_id):
        return {'id': sub_id, 'object': 'subscription', 'livemode': False, 'status': state['status'], 'customer': 'cus_m5',
                'cancel_at_period_end': False,
                'metadata': {'workspace_id': wid, 'sandbox_location_digest': snap['digest'],
                             'sandbox_location_quantity': str(snap['quantity'])},
                'items': {'data': [{'id': 'si_1', 'price': {'id': 'price_test_growth'}, 'quantity': snap['quantity'],
                                    'current_period_end': int(time.time()) + 20 * 86400}]}}
    import stripe
    monkeypatch.setattr(stripe.Subscription, 'retrieve', staticmethod(fake_retrieve))
    body, headers = _stripe_event('invoice.payment_failed', {'id': 'in_1', 'object': 'invoice', 'customer': 'cus_m5'})
    assert h.api.post('/api/saas/billing/webhook', content=body, headers=headers).status_code == 200
    e = h.get('/api/saas/me').json()['workspace']['entitlement']
    assert e['state'] == 'past_due' and e['access'] == 'full' and e['days_left'] == 7
    with Session(saas.engine) as db:  # grace runs out
        w = db.get(saas.Workspace, wid); w.payment_failed_at = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(); db.commit()
    assert h.get('/api/saas/me').json()['workspace']['entitlement']['access'] == 'read_only'
    assert h.post('/api/decisions/plans', PLAN).status_code == 402
    state['status'] = 'active'
    body, headers = _stripe_event('invoice.paid', {'id': 'in_2', 'object': 'invoice', 'customer': 'cus_m5'})
    assert h.api.post('/api/saas/billing/webhook', content=body, headers=headers).status_code == 200
    e = h.get('/api/saas/me').json()['workspace']['entitlement']
    assert e['state'] == 'active'
    with Session(saas.engine) as db:
        assert db.get(saas.Workspace, wid).payment_failed_at is None
    assert h.post('/api/decisions/plans', PLAN).status_code == 201


def test_adding_a_location_queues_its_history_import(harness):
    h = harness
    h.sign_up(); h.connect_oauth(); ids = h.select_eligible()
    h.post('/api/integrations/square/sync')
    assert h.post('/api/saas/billing/locations/confirm', {'location_ids': ids[:1]}).status_code == 200
    with Session(connections.engine) as db:
        assert db.scalar(select(square_sync.SquareSyncJob).where(square_sync.SquareSyncJob.status == 'queued')) is None
    assert h.post('/api/saas/billing/locations/confirm', {'location_ids': ids}).status_code == 200
    with Session(connections.engine) as db:
        assert db.scalar(select(square_sync.SquareSyncJob).where(square_sync.SquareSyncJob.status == 'queued')) is not None


def test_stripe_return_urls_are_real_pages(harness, monkeypatch):
    """Regression: Checkout sent paying customers to /billing/success, which didn't exist."""
    from pathlib import Path
    from urllib.parse import urlparse
    import stripe
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID', 'price_test_growth')
    captured = {}
    monkeypatch.setattr(stripe.checkout.Session, 'create', staticmethod(lambda **kw: captured.update(kw) or SimpleNamespace(url='https://checkout.stripe.com/x')))
    monkeypatch.setattr(stripe.checkout.Session, 'list', staticmethod(lambda **kw: {'data': []}))
    assert h.post('/api/saas/billing/checkout').status_code == 200
    app_dir = Path(__file__).resolve().parents[2] / 'frontend' / 'app'
    for key in ('success_url', 'cancel_url'):
        path = urlparse(captured[key]).path.strip('/')
        assert (app_dir / path / 'page.tsx').exists(), f'{key} points at /{path}, which has no page'
    assert 'session_id={CHECKOUT_SESSION_ID}' in captured['success_url']
