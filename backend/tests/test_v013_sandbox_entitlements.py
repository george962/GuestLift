"""v0.13 server-owned Sandbox selection, isolation, sync scoping and Stripe checks."""
from __future__ import annotations

from fastapi.testclient import TestClient
from types import SimpleNamespace
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import connections, local_auth, saas
from app.database import Base
from app.location_entitlements import SandboxMonitoredLocation, snapshot
from app.main import app
from app import membership

ORIGIN = {'Origin': 'http://localhost:3000'}


def register(client, email):
    r = client.post('/api/local-auth/register', json={
        'email': email, 'password': 'a-secure-test-password-123'
    }, headers=ORIGIN)
    assert r.status_code == 201, r.text


def post(client, path, payload=None):
    csrf = client.get('/api/local-auth/session').json()['csrf_token']
    return client.post(path, json=payload, headers={**ORIGIN, 'X-CSRF-Token': csrf})


def fake_square(token, method, path, payload=None):
    assert token == 'V013_SANDBOX_TOKEN'
    locations = [
        {'id':'loc-a', 'merchant_id':'sandbox-merchant-v13', 'status':'ACTIVE', 'type':'PHYSICAL', 'name':'Downtown'},
        {'id':'loc-b', 'merchant_id':'sandbox-merchant-v13', 'status':'ACTIVE', 'type':'PHYSICAL', 'name':'Midtown'},
        {'id':'loc-virtual', 'merchant_id':'sandbox-merchant-v13', 'status':'ACTIVE', 'type':'MOBILE', 'name':'Virtual'},
    ]
    if path == '/v2/locations':
        return {'locations': locations}
    if path == '/v2/payments':
        assert payload['location_id'] in ('loc-a', 'loc-b')
        return {'payments': []}
    assert path == '/v2/orders/search'
    assert payload['location_ids'] == ['loc-a']
    return {'orders': [{
        'id':'order-a', 'location_id':'loc-a', 'state':'COMPLETED',
        'created_at':'2026-11-20T10:00:00Z', 'updated_at':'2026-11-20T10:00:00Z',
        'total_money':{'amount':1200,'currency':'USD'},
    }]}


def test_server_selected_locations_and_scoped_sync(tmp_path, monkeypatch):
    db_engine = create_engine('sqlite:///'+str(tmp_path/'v13.db'), connect_args={'check_same_thread':False})
    for module in (saas, connections, local_auth, membership):
        monkeypatch.setattr(module, 'engine', db_engine)
    monkeypatch.setenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '1')
    monkeypatch.setenv('SQUARE_SANDBOX_ACCESS_TOKEN', 'V013_SANDBOX_TOKEN')
    monkeypatch.setattr(connections, '_api', fake_square)
    Base.metadata.create_all(db_engine)
    try:
        with TestClient(app) as owner, TestClient(app) as outsider:
            register(owner, 'v13-owner@example.com')
            register(outsider, 'v13-other@example.com')
            assert post(owner, '/api/integrations/square/connect-developer-sandbox').status_code == 200
            discovered = owner.get('/api/integrations/square/locations')
            assert discovered.status_code == 200, discovered.text
            assert len(discovered.json()['locations']) == 3
            assert discovered.json()['selected_count'] == 0
            assert post(owner, '/api/integrations/square/sync').status_code == 409
            assert post(owner, '/api/integrations/square/locations/selection', {'location_ids':['loc-virtual']}).status_code == 422
            assert post(owner, '/api/integrations/square/locations/selection', {'location_ids':['loc-unknown']}).status_code == 422
            assert post(owner, '/api/integrations/square/locations/selection', {'location_ids':['loc-a','loc-a']}).status_code == 422
            selected = post(owner, '/api/integrations/square/locations/selection', {'location_ids':['loc-a']})
            assert selected.status_code == 200, selected.text
            assert selected.json()['selected_count'] == 1
            assert owner.get('/api/saas/billing/quote').json()['selected_quantity'] == 1
            assert outsider.get('/api/saas/billing/quote').json()['selected_quantity'] == 0
            assert post(owner, '/api/integrations/square/sync').status_code == 200
            assert owner.get('/api/saas/me').json()['summary']['orders'] == 1
            assert outsider.get('/api/saas/me').json()['summary']['orders'] == 0
            # Select a second location, verify server-sourced TEST checkout quantity.
            assert post(owner, '/api/integrations/square/locations/selection',
                        {'location_ids':['loc-a', 'loc-b']}).status_code == 200
            calls = []
            def create_checkout(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(url='https://checkout.stripe.com/c/test-checkout')
            fake_stripe = SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(
                list=lambda **kwargs: {'data': []}, create=create_checkout)))
            monkeypatch.setattr(saas, '_stripe_client', lambda: fake_stripe)
            monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID', 'price_growth_test')
            assert post(owner, '/api/saas/billing/checkout').status_code == 200
            assert calls[0]['line_items'][0]['quantity'] == 2
            with Session(db_engine) as db:
                loc = db.scalar(select(SandboxMonitoredLocation))
                assert loc is not None
                wid = loc.workspace_id
                snap = snapshot(db, wid, 'sandbox-merchant-v13')
                assert snap['ids'] == ['loc-a', 'loc-b']
                sub = {
                    'id': 'sub_valid_v13', 'livemode': False, 'customer': 'cus_v13',
                    'status': 'active', 'metadata': {
                        'workspace_id': wid, 'sandbox_location_digest': snap['digest'],
                        'sandbox_location_quantity': '2'},
                    'items': {'data': [{'price': {'id': 'price_growth_test'}, 'quantity': 1}]}
                }
                from fastapi import HTTPException
                w = db.get(saas.Workspace, wid)
                try:
                    saas._apply_verified_subscription(db, w, sub, 'cus_v13')
                    assert False, 'quantity mismatch should deny entitlement'
                except HTTPException as exc:
                    assert exc.status_code == 409
                sub['items']['data'][0]['quantity'] = 2
                assert saas._apply_verified_subscription(db, w, sub, 'cus_v13')['access_granted']
            assert post(owner, '/api/integrations/square/locations/selection',
                        {'location_ids':['loc-a']}).status_code == 409
            assert post(owner, '/api/integrations/square/disconnect').status_code == 200
            assert owner.get('/api/saas/billing/quote').json()['selected_quantity'] == 0
            assert owner.get('/api/saas/me').json()['summary']['orders'] == 0
    finally:
        db_engine.dispose()


def test_stripe_quantity_and_selection_digest_rejected_on_mismatch(tmp_path, monkeypatch):
    from fastapi import HTTPException
    engine = create_engine('sqlite:///'+str(tmp_path/'billing.db'), connect_args={'check_same_thread':False})
    monkeypatch.setenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '1')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID', 'price_test_growth')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            w = saas._get_workspace(db, 'billing-test-owner')
            db.add(SandboxMonitoredLocation(workspace_id=w.id, location_id='loc-a',
                merchant_id='merchant-a', name='A', selected_at='2026-11-22T00:00:00Z'))
            db.commit()
            snap = snapshot(db, w.id, 'merchant-a')
            # No active Square connection must never turn into paid access.
            subscription = {
                'id':'sub_123', 'livemode': False, 'customer': 'cus_123',
                'status': 'active', 'metadata': {
                    'workspace_id':w.id, 'sandbox_location_digest':snap['digest'],
                    'sandbox_location_quantity':'1'},
                'items':{'data':[{'price':{'id':'price_test_growth'},'quantity':1}]},
            }
            try:
                saas._apply_verified_subscription(db, w, subscription, 'cus_123')
                assert False, 'should reject missing connection'
            except HTTPException as e:
                assert e.status_code == 409
    finally:
        engine.dispose()
