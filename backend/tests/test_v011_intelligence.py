"""Evidence graph and optional model: business isolation, safe prompts and access gates."""
from datetime import datetime, timezone
import sys
import uuid
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.main import app
from app import saas, decisions, intelligence
from app.connections import SquareConnection, SquareOrder


def fixture(tmp_path, monkeypatch, *, growth=False):
    engine = create_engine('sqlite:///'+str(tmp_path/'ai.sqlite'), connect_args={'check_same_thread':False})
    monkeypatch.setattr(saas, 'engine', engine)
    monkeypatch.setattr(decisions, 'engine', engine)
    monkeypatch.setattr(intelligence, 'engine', engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[saas.authenticated_subject] = lambda:'test-owner-a'
    with Session(engine) as db:
        w = saas._get_workspace(db, 'test-owner-a')
        if growth:
            w.subscription_plan = 'growth'
            w.subscription_status = 'active'
        db.add(SquareConnection(id=str(uuid.uuid4()), workspace_id=w.id,
                merchant_id='fake-merchant-a', credential_mode='developer_env',
                connected_at=datetime.now(timezone.utc).isoformat()))
        for i in range(12):
            db.add(SquareOrder(id=str(uuid.uuid4()),workspace_id=w.id,
                source_order_id=f'order-{i}', location_id='loc-a',
                created_at='2026-11-08T00:00:00Z',updated_at='2026-11-08T00:00:00Z',
                status='COMPLETED',customer_id='private@example.test' if i%2==0 else None,
                net_sales_minor=2000,discount_minor=100,tax_minor=0,tip_minor=0,currency='USD'))
        db.commit()
    return engine


def test_graph_is_deterministic_scoped_and_contains_no_customer_id(tmp_path, monkeypatch):
    engine=fixture(tmp_path,monkeypatch)
    try:
        with TestClient(app) as c:
            r=c.get('/api/intelligence/brief')
            assert r.status_code==200,r.text
            body=r.json()
            assert body['data_connected'] is True
            assert body['orders_available'] is True
            assert next(x for x in body['nodes'] if x['id']=='orders')['value']=='12'
            assert 'private@example.test' not in r.text
            assert {x['id'] for x in body['nodes']} >= {'identity','repeat','discounts','decisions'}
            app.dependency_overrides[saas.authenticated_subject]=lambda:'test-owner-b'
            other=c.get('/api/intelligence/brief')
            assert other.status_code==200
            assert other.json()['data_connected'] is False
            assert other.json()['orders_available'] is False
            assert next(x for x in other.json()['nodes'] if x['id']=='orders')['value']=='0'
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_chat_requires_paid_plan_and_configured_model(tmp_path,monkeypatch):
    engine=fixture(tmp_path,monkeypatch)
    try:
        with TestClient(app) as c:
            payload={'question':'What should I investigate?'}
            assert c.post('/api/intelligence/ask',json=payload).status_code==402
            with Session(engine) as db:
                w=saas._get_workspace(db,'test-owner-a')
                w.subscription_plan='growth';w.subscription_status='active';db.commit()
            monkeypatch.delenv('OPENAI_API_KEY', raising=False)
            assert c.post('/api/intelligence/ask',json=payload).status_code==503
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_model_receives_only_aggregates_and_store_false(tmp_path,monkeypatch):
    engine=fixture(tmp_path,monkeypatch,growth=True)
    captured=[]
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(output_text='The observed numbers show known returning buyers, but cannot prove lift. (repeat_customers)')
    class FakeOpenAI:
        def __init__(self, **kwargs):pass
        @property
        def responses(self):return SimpleNamespace(create=create)
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv('GUESTLIFT_ENABLE_LLM','1')
    monkeypatch.setenv('OPENAI_API_KEY','sk-test-not-a-real-secret')
    monkeypatch.setenv('OPENAI_MODEL','test-model')
    try:
        with TestClient(app) as c:
            response=c.post('/api/intelligence/ask',json={'question':'What is changing among returning guests?'})
            assert response.status_code==200,response.text
            assert response.json()['engine']=='openai_responses'
            assert 'private@example.test' not in str(captured)
            assert captured[0]['store'] is False
            assert captured[0]['model']=='test-model'
            assert 'ORDERS' not in response.json()['answer']
            assert c.post('/api/intelligence/ask',json={'question':'a'}).status_code==422
    finally:
        app.dependency_overrides.clear();engine.dispose()
