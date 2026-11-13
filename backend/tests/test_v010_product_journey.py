"""v0.10: persistent onboarding, useful decisions and strict workspace isolation.
No production Stripe or Square traffic is used in these tests.
"""
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.main import app
from app import saas, decisions
from app.local_auth import SESSION_TTL
from app.connections import SquareOrder, SquareConnection


def prepare(tmp_path, monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'v010.sqlite'), connect_args={'check_same_thread':False})
    monkeypatch.setattr(saas,'engine',engine)
    monkeypatch.setattr(decisions,'engine',engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[saas.authenticated_subject]=lambda:'owner-a'
    return engine


def test_30_day_cookie_expiry_for_local_developer_accounts():
    assert SESSION_TTL == 30 * 24 * 60 * 60


def test_onboarding_survives_requests_without_migration(tmp_path,monkeypatch):
    engine=prepare(tmp_path,monkeypatch)
    try:
        with TestClient(app) as c:
            assert c.get('/api/saas/onboarding').json()['stage']==1
            before=c.post('/api/saas/onboarding',json={'stage':3,'plan_choice':'growth'})
            assert before.status_code==409
            result=c.post('/api/saas/profile',json={'name':'Harbor Cafe','restaurant_type':'cafe','goal':'customer_retention'})
            assert result.status_code==200,result.text
            assert c.get('/api/saas/onboarding').json()['stage']==2
            result=c.post('/api/saas/onboarding',json={'stage':3,'plan_choice':'sandbox'})
            assert result.status_code==200,result.text
            assert c.get('/api/saas/onboarding').json()=={'stage':3,'plan_choice':'sandbox'}
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_empty_workspace_never_invents_opportunities_or_allows_plan(tmp_path,monkeypatch):
    engine=prepare(tmp_path,monkeypatch)
    try:
        with TestClient(app) as c:
            result=c.get('/api/decisions/opportunities')
            assert result.status_code==200,result.text
            assert result.json()['observed_orders']==0
            assert result.json()['has_connected_source'] is False
            payload=dict(title='Test return visit offer', objective='returning_guests',offer_type='percent',
                         offer_value=10,target_redemptions=10,reference_basket_minor=2500,assumed_margin_percent=35)
            assert c.post('/api/decisions/plans',json=payload).status_code==409
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_decision_plans_persist_and_are_private(tmp_path,monkeypatch):
    engine=prepare(tmp_path,monkeypatch)
    now=datetime.now(timezone.utc)
    try:
        with Session(engine) as db:
            w=saas._get_workspace(db,'owner-a')
            wid=w.id
            db.add(SquareConnection(id=str(uuid.uuid4()),workspace_id=wid,merchant_id='sandbox-merchant-1',
                   credential_mode='developer',connected_at=now.isoformat()))
            # Records with recognizable returning guests; no identifying names/emails.
            for i in range(30):
                date=now-timedelta(days=i*2)
                db.add(SquareOrder(id=str(uuid.uuid4()), workspace_id=wid,source_order_id=f'sandbox-{i}',
                     location_id='location-1',created_at=date.isoformat(),updated_at=date.isoformat(),
                     status='COMPLETED',customer_id=f'fake-customer-{i%6}', net_sales_minor=2500,
                     discount_minor=100,tax_minor=0,tip_minor=0,currency='USD'))
            db.commit()
        with TestClient(app) as c:
            results=c.get('/api/decisions/opportunities')
            assert results.status_code==200,results.text
            assert results.json()['observed_orders']==30
            assert results.json()['identified_customers']==6
            assert results.json()['reference_basket_minor']==2500
            payload={'title':'Compare a 10% return visit offer','objective':'returning_guests','offer_type':'percent',
                     'offer_value':10,'target_redemptions':10,'reference_basket_minor':2500,
                     'assumed_margin_percent':35,'notes':'Synthetic planning scenario only'}
            saved=c.post('/api/decisions/plans',json=payload)
            assert saved.status_code==201,saved.text
            body=saved.json()
            assert body['plan']['discount_budget_minor']==2500
            assert body['plan']['modeled_contribution_minor']==6250
            pid=body['plan']['id']
            assert len(c.get('/api/decisions/plans').json()['plans'])==1
            assert c.post('/api/decisions/plans/'+pid+'/status',json={'status':'planned'}).json()['plan']['status']=='planned'
            # Switch identity: the other account must see zero records and cannot edit the first.
            app.dependency_overrides[saas.authenticated_subject]=lambda:'owner-b'
            assert c.get('/api/decisions/plans').json()['plans']==[]
            assert c.post('/api/decisions/plans/'+pid+'/status',json={'status':'reviewed'}).status_code==404
            assert c.get('/api/decisions/opportunities').json()['observed_orders']==0
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_offer_scenarios_validate_cost_inputs():
    x=decisions.scenario('fixed',1000,10,2500,35)
    assert x['discount_budget_minor']==10000
    assert x['modeled_contribution_minor']==-1250
    assert decisions.scenario('no_offer',0,10,2500,35)['discount_budget_minor']==0
    from fastapi import HTTPException
    try:decisions.scenario('fixed',3000,10,2500,35)
    except HTTPException as e:assert e.status_code==422
    else:raise AssertionError('Should reject a fixed discount larger than basket')


def test_stripe_sdk_objects_are_supported_without_get():
    class StripeObject:
        def to_dict(self): return {'id':'sub_test_object'}
    class StripeList:
        def to_dict(self): return {'data':[{'id':'cs_test_123'}]}
    assert saas._object_id(StripeObject())=='sub_test_object'
    assert saas._stripe_payload(StripeList())['data'][0]['id']=='cs_test_123'
