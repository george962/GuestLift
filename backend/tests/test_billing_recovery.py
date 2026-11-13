"""Regression tests for Stripe Sandbox checkout verification, recovery and tenant isolation."""
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import saas
from app.database import Base
from app.main import app


def _fake_stripe(monkeypatch, workspace_id, *, subscription_status='active', price='price_growth',
                 session_id='cs_test_working123456', session_owner=None, payment_status='paid'):
    session_owner = workspace_id if session_owner is None else session_owner
    session_data = {'id':session_id, 'livemode':False, 'mode':'subscription',
                    'client_reference_id':session_owner, 'status':'complete',
                    'payment_status':payment_status, 'customer':'cus_testing01', 'subscription':'sub_testing01'}
    subscription = {'id':'sub_testing01','livemode':False,'metadata':{'workspace_id':workspace_id},
                    'customer':'cus_testing01','status':subscription_status,
                    'items':{'data':[{'price':{'id':price}}]}}
    calls={'checkout':[], 'portal':[], 'session_data':session_data, 'subscription':subscription, 'recent_checkouts':[]}

    def checkout_create(**kwargs):
        calls['checkout'].append(kwargs)
        return SimpleNamespace(url='https://checkout.stripe.com/c/pay/test')

    def portal_create(**kwargs):
        calls['portal'].append(kwargs)
        return SimpleNamespace(url='https://billing.stripe.com/p/session/test')

    stripe = SimpleNamespace(
        api_key=None,
        checkout=SimpleNamespace(Session=SimpleNamespace(create=checkout_create,
            retrieve=lambda sid:session_data if sid==session_data['id'] else (_ for _ in ()).throw(ValueError('Invalid ID')),
            list=lambda **kwargs:{'data':calls['recent_checkouts']})),
        Subscription=SimpleNamespace(retrieve=lambda sid:subscription),
        billing_portal=SimpleNamespace(Session=SimpleNamespace(create=portal_create)),
        error=SimpleNamespace(SignatureVerificationError=type('SignatureVerificationError',(Exception,),{})),
        Webhook=SimpleNamespace(construct_event=lambda *_:calls['event'])
    )
    monkeypatch.setitem(sys.modules, 'stripe', stripe)
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_synthetic')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID', 'price_growth')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_synthetic')
    return calls


def _db(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///'+str(tmp_path/'billing.sqlite'),connect_args={'check_same_thread':False})
    monkeypatch.setattr(saas, 'engine', engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        w = saas._get_workspace(db,'billing-owner-a')
        wid = w.id
    app.dependency_overrides[saas.authenticated_subject] = lambda:'billing-owner-a'
    return engine, wid


def test_checkout_creates_real_confirmation_url_not_instant_access(tmp_path, monkeypatch):
    engine, wid = _db(tmp_path,monkeypatch)
    calls = _fake_stripe(monkeypatch,wid)
    try:
        with TestClient(app) as client:
            response = client.post('/api/saas/billing/checkout')
            assert response.status_code==200, response.text
            assert 'billing/success?session_id={CHECKOUT_SESSION_ID}' in calls['checkout'][0]['success_url']
            assert calls['checkout'][0]['client_reference_id']==wid
            w=client.get('/api/saas/me').json()['workspace']
            assert w['plan']=='sandbox' and w['subscription_status']=='none'
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_recovery_can_find_legacy_checkout_and_enable_portal(tmp_path,monkeypatch):
    engine, wid = _db(tmp_path,monkeypatch)
    calls = _fake_stripe(monkeypatch,wid)
    calls['recent_checkouts'].append(calls['session_data'])
    try:
        with TestClient(app) as client:
            response=client.post('/api/saas/billing/reconcile',json={})
            assert response.status_code==200,response.text
            assert response.json()['access_granted'] is True
            w=client.get('/api/saas/me').json()['workspace']
            assert w['plan']=='growth' and w['subscription_status']=='active'
            assert w['has_billing_customer'] is True
            portal=client.post('/api/saas/billing/portal')
            assert portal.status_code==200,portal.text
            assert calls['portal'][0]['customer']=='cus_testing01'
            repeated=client.post('/api/saas/billing/reconcile',json={'session_id':'cs_test_working123456'})
            assert repeated.json()['access_granted'] is True
            assert client.post('/api/saas/billing/checkout').status_code==409
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_no_cross_workspace_checkout_access(tmp_path,monkeypatch):
    engine,wid=_db(tmp_path,monkeypatch)
    calls=_fake_stripe(monkeypatch,wid)
    calls['recent_checkouts'].append(calls['session_data'])
    try:
        app.dependency_overrides[saas.authenticated_subject]=lambda:'billing-owner-b'
        with TestClient(app) as client:
            result=client.post('/api/saas/billing/reconcile',json={'session_id':'cs_test_working123456'})
            assert result.status_code==403,result.text
            result=client.post('/api/saas/billing/reconcile',json={})
            assert result.status_code==404,result.text
            other=client.get('/api/saas/me').json()['workspace']
            assert other['plan']=='sandbox'
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_invalid_price_and_unpaid_do_not_unlock(tmp_path,monkeypatch):
    engine,wid=_db(tmp_path,monkeypatch)
    calls=_fake_stripe(monkeypatch,wid,price='price_other')
    try:
        with TestClient(app) as client:
            r=client.post('/api/saas/billing/reconcile',json={'session_id':'cs_test_working123456'})
            assert r.status_code==409,r.text
            calls['subscription']['items']['data'][0]['price']['id']='price_growth'
            calls['session_data']['payment_status']='unpaid'
            r=client.post('/api/saas/billing/reconcile',json={'session_id':'cs_test_working123456'})
            assert r.status_code==200 and r.json()['pending'] is True
            assert client.get('/api/saas/me').json()['workspace']['plan']=='sandbox'
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_signed_webhook_verifies_active_then_revokes_on_cancel(tmp_path,monkeypatch):
    engine,wid=_db(tmp_path,monkeypatch)
    calls=_fake_stripe(monkeypatch,wid)
    try:
        with TestClient(app) as client:
            calls['event']={'id':'evt_subscription1','type':'customer.subscription.created','livemode':False,
                'data':{'object':calls['subscription']}}
            res=client.post('/api/saas/billing/webhook',data=b'{}',headers={'stripe-signature':'fake'})
            assert res.status_code==200,res.text
            assert client.get('/api/saas/me').json()['workspace']['plan']=='growth'
            calls['subscription']['status']='canceled'
            calls['event']={'id':'evt_subscription2','type':'customer.subscription.deleted','livemode':False,
                'data':{'object':calls['subscription']}}
            res=client.post('/api/saas/billing/webhook',data=b'{}',headers={'stripe-signature':'fake'})
            assert res.status_code==200,res.text
            status=client.get('/api/saas/me').json()['workspace']
            assert status['plan']=='sandbox' and status['subscription_status']=='canceled'
    finally:
        app.dependency_overrides.clear();engine.dispose()



def test_stripe_sdk_v15_object_compatibility(tmp_path, monkeypatch):
    """Exercise SDK-style resources without dictionary .get() methods."""
    engine, wid = _db(tmp_path, monkeypatch)
    calls = _fake_stripe(monkeypatch, wid)
    calls['recent_checkouts'].append(calls['session_data'])

    class SDKObject:
        def __init__(self, data):
            self._data = data

        def to_dict(self):
            return self._data

    fake = sys.modules['stripe']

    fake.checkout.Session.list = lambda **kwargs: SDKObject({
        'data': calls['recent_checkouts']
    })

    fake.checkout.Session.retrieve = lambda sid: SDKObject(
        calls['session_data']
    )

    fake.Subscription.retrieve = lambda sid: SDKObject(
        calls['subscription']
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                '/api/saas/billing/reconcile',
                json={}
            )

            assert response.status_code == 200, response.text
            assert response.json()['access_granted'] is True

            workspace = client.get('/api/saas/me').json()['workspace']
            assert workspace['plan'] == 'growth'
            assert workspace['subscription_status'] == 'active'

            calls['subscription']['status'] = 'canceled'
            calls['event'] = SDKObject({
                'id': 'evt_sdk_v15_cancel',
                'type': 'customer.subscription.deleted',
                'livemode': False,
                'data': {'object': calls['subscription']}
            })

            webhook = client.post(
                '/api/saas/billing/webhook',
                content=b'{}',
                headers={'stripe-signature': 'synthetic'}
            )

            assert webhook.status_code == 200, webhook.text

            workspace = client.get('/api/saas/me').json()['workspace']
            assert workspace['plan'] == 'sandbox'
            assert workspace['subscription_status'] == 'canceled'
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
