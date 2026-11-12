"""SaaS API and insight tests — all synthetic, no real Supabase or Stripe credentials."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app import saas
from app.database import Base
from app.insights import analyze_orders, answer_question
from app.main import app


def test_evidence_first_analyst_from_fictional_orders():
    rows=[{'provider':'toast','location_id':'1','customer_id':'A','status':'PAID','created_at':'2026-11-01T12:00:00Z','net_sales_minor':1300,'discount_minor':100,'campaign_code':'LUNCH','campaign_discount_minor':100},
          {'provider':'toast','location_id':'1','customer_id':'A','status':'PAID','created_at':'2026-11-02T12:00:00Z','net_sales_minor':2000,'discount_minor':0,'campaign_code':None},
          {'provider':'square','location_id':'2','customer_id':None,'status':'PAID','created_at':'2026-11-03T12:00:00Z','net_sales_minor':800,'discount_minor':0,'campaign_code':None}]
    s=analyze_orders(rows)
    assert s['net_sales_minor']==4100 and s['repeat_customers']==1
    assert s['anonymous_orders']==1 and s['identification_coverage_percent']==66.7
    for q in ('what is sales','why do customers return','which offer','best location'):
        r=answer_question(q,s)
        assert r['causal_claim'] is False
        assert r['source']=='fictional_workspace_seed / normalized orders'
        assert r['evidence_keys'] and r['engine']=='verified_rules'


def test_workspace_isolation_and_synthetic_seeding(tmp_path,monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'saas.sqlite'),connect_args={'check_same_thread':False})
    monkeypatch.setattr(saas,'engine',engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a=saas._get_workspace(db,'supabase-user-one')
        b=saas._get_workspace(db,'supabase-user-two')
        assert a.id!=b.id
        summary_a=saas._scoped_summary(db,a)
        summary_b=saas._scoped_summary(db,b)
        assert summary_a['orders']==56 and summary_b['orders']==56
        assert saas._seed_workspace(db,a.id)==0
        from sqlalchemy import delete
        db.execute(delete(saas.WorkspaceOrder).where(saas.WorkspaceOrder.workspace_id==a.id));db.commit()
        assert saas._scoped_summary(db,a)['orders']==0
        assert saas._scoped_summary(db,b)['orders']==56
        assert saas._seed_workspace(db,a.id)==56
    engine.dispose()


def test_private_endpoints_require_verification():
    with TestClient(app) as c:
        assert c.get('/api/saas/me').status_code == 401
        assert c.post('/api/saas/profile', json={}).status_code == 401


def test_plan_gates_analyst_and_checkout_is_test_only(tmp_path,monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'entitlement.sqlite'),connect_args={'check_same_thread':False})
    monkeypatch.setattr(saas,'engine',engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[saas.authenticated_subject]=lambda:'test-user-01'
    monkeypatch.delenv('STRIPE_SECRET_KEY',raising=False)
    try:
        with TestClient(app) as c:
            assert c.get('/api/saas/me').json()['workspace']['plan']=='sandbox'
            assert c.post('/api/saas/analyst',json={'question':'show sales'}).status_code==402
            assert c.post('/api/saas/billing/checkout').status_code==503
            w=saas._get_workspace(Session(engine),'test-user-01')
            with Session(engine) as db:
                row=db.get(saas.Workspace,w.id)
                row.subscription_plan='growth';row.subscription_status='active';db.commit()
            res=c.post('/api/saas/analyst',json={'question':'Which campaign gave discounts?'})
            assert res.status_code==200 and res.json()['engine']=='verified_rules'
            assert res.json()['causal_claim'] is False
    finally:
        app.dependency_overrides.clear();engine.dispose()
