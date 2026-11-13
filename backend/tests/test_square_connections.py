"""Square Sandbox contract tests: mocked external APIs, real workspace DB isolation."""
from __future__ import annotations
import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app import saas,local_auth,connections
from app.database import Base

ORIGIN={'Origin':'http://localhost:3000'}


def db_fixture(tmp_path, monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'sandbox.sqlite'),connect_args={'check_same_thread':False})
    for module in (saas,local_auth,connections):monkeypatch.setattr(module,'engine',engine)
    Base.metadata.create_all(engine)
    return engine


def register(c,email):
    r=c.post('/api/local-auth/register',json={'email':email,'password':'a-long-sandbox-password'},headers=ORIGIN)
    assert r.status_code==201,r.text


def csrf(c):
    return c.get('/api/local-auth/session').json()['csrf_token']


def post(c,path,payload=None):
    return c.post(path,json=payload,headers={**ORIGIN,'X-CSRF-Token':csrf(c)})


def fake_square(token,method,path,payload=None):
    assert token=='SANDBOX_TEST_TOKEN'
    if path=='/v2/payments':
        return {'payments':[{'order_id':'order-b','customer_id':'guest-a','status':'COMPLETED'}]}
    if path=='/v2/locations':
        return {'locations':[{'id':'loc-01','merchant_id':'sandbox-merchant-1','status':'ACTIVE'}]}
    assert path=='/v2/orders/search' and method=='POST'
    assert payload['location_ids']==['loc-01']
    assert payload['query']['filter']['date_time_filter']['created_at']['start_at']
    return {'orders':[
        {'id':'order-a','location_id':'loc-01','state':'COMPLETED','created_at':'2026-11-10T10:00:00Z',
         'updated_at':'2026-11-10T10:00:00Z','customer_id':'guest-a','total_money':{'amount':2700,'currency':'USD'},
         'total_discount_money':{'amount':300},'total_tax_money':{'amount':200},'total_tip_money':{'amount':100}},
        {'id':'order-b','location_id':'loc-01','state':'COMPLETED','created_at':'2026-11-11T10:00:00Z',
         'updated_at':'2026-11-11T10:00:00Z','total_money':{'amount':1600,'currency':'USD'},
         'total_discount_money':{'amount':0},'total_tax_money':{'amount':100},'total_tip_money':{'amount':0}},
        {'id':'order-c','location_id':'loc-01','state':'OPEN','total_money':{'amount':600,'currency':'USD'}},
        {'id':'order-d','location_id':'loc-01','state':'CANCELED','created_at':'2026-11-11T10:00:00Z',
         'total_money':{'amount':400,'currency':'USD'}},
    ]}


def test_sandbox_connect_sync_is_idempotent_and_isolated(tmp_path, monkeypatch):
    engine=db_fixture(tmp_path,monkeypatch)
    monkeypatch.setenv('SQUARE_SANDBOX_ACCESS_TOKEN','SANDBOX_TEST_TOKEN')
    monkeypatch.setattr(connections,'_api',fake_square)
    with TestClient(app) as a,TestClient(app) as b:
        register(a,'owner-a@example.com')
        register(b,'owner-b@example.com')
        assert a.get('/api/saas/me').json()['summary']['orders']==0
        assert a.get('/api/integrations/square/status').json()['connected'] is False
        assert a.post('/api/integrations/square/connect-developer-sandbox',headers=ORIGIN).status_code==403
        assert post(a,'/api/integrations/square/connect-developer-sandbox').status_code==200
        assert post(b,'/api/integrations/square/connect-developer-sandbox').status_code==409
        first=post(a,'/api/integrations/square/sync')
        assert first.status_code==200,first.text
        assert first.json()['scanned']==4
        assert first.json()['inserted']==3
        assert first.json()['skipped']==1
        second=post(a,'/api/integrations/square/sync')
        assert second.status_code==200 and second.json()['updated']==3 and second.json()['inserted']==0
        mine=a.get('/api/saas/me').json()['summary']
        theirs=b.get('/api/saas/me').json()['summary']
        assert mine['orders']==2 and theirs['orders']==0
        assert mine['net_sales_minor']==3900  # (2700-200-100)+(1600-100)
        assert mine['repeat_customers']==1
        assert mine['data_origin']=='square_sandbox_api'
        assert a.get('/api/integrations/square/status').json()['runs'][0]['scanned']==4
        assert b.get('/api/integrations/square/status').json()['runs']==[]
        assert 'SANDBOX_TEST_TOKEN' not in a.get('/api/integrations/square/status').text
        assert post(a,'/api/integrations/square/disconnect').status_code==200
        assert a.get('/api/saas/me').json()['summary']['orders']==0
        assert b.get('/api/saas/me').json()['summary']['orders']==0
    engine.dispose()


def test_square_parser_missing_ids_non_usd_and_cancelled():
    assert connections._parse_order({'id':'x','location_id':'l','state':'OPEN','total_money':{'amount':100,'currency':'USD'}}) is None
    assert connections._parse_order({'id':'x','location_id':'l','state':'COMPLETED','total_money':{'amount':100,'currency':'EUR'}}) is None
    assert connections._parse_order({'id':'x','state':'COMPLETED','total_money':{'amount':100,'currency':'USD'}}) is None
    parsed=connections._parse_order({'id':'x','location_id':'l','state':'CANCELED','total_money':{'amount':100,'currency':'USD'}})
    assert parsed and parsed['status']=='CANCELED'


def test_local_assisted_setup_requests_not_sent_and_tenant_scoped(tmp_path,monkeypatch):
    engine=db_fixture(tmp_path,monkeypatch)
    with TestClient(app) as one, TestClient(app) as two:
        register(one,'assist-a@example.com');register(two,'assist-b@example.com')
        p=post(one,'/api/integrations/square/assisted-setup',{'provider':'toast','note':'one location'})
        assert p.status_code==201 and p.json()['status']=='requested'
        assert post(one,'/api/integrations/square/assisted-setup',{'provider':'toast','note':'repeat'}).json()['duplicate']
        assert one.get('/api/integrations/square/status').json()['assisted_requests'][0]['provider']=='toast'
        assert two.get('/api/integrations/square/status').json()['assisted_requests']==[]
        assert post(one,'/api/integrations/square/assisted-setup',{'provider':'square','note':'x'*500}).status_code==422
    engine.dispose()


def test_oauth_single_use_state_and_encrypted_token(tmp_path,monkeypatch):
    from cryptography.fernet import Fernet
    engine=db_fixture(tmp_path,monkeypatch)
    monkeypatch.setenv('TABLESIGNAL_CREDENTIAL_KEY',Fernet.generate_key().decode())
    monkeypatch.setenv('SQUARE_SANDBOX_APP_ID','sandbox-app-123')
    monkeypatch.setenv('SQUARE_SANDBOX_APP_SECRET','dummy_test_secret')
    monkeypatch.setenv('SQUARE_SANDBOX_REDIRECT_URI','http://localhost:8000/api/integrations/square/oauth/callback')
    monkeypatch.setattr(connections,'_api',lambda token,method,path,payload=None:{'locations':[{'id':'l','merchant_id':'m','status':'ACTIVE'}]})
    class FakeResponse:
        status_code=200
        def json(self):return {'access_token':'private-sandbox-token','refresh_token':'private-refresh','merchant_id':'m'}
    class FakeClient:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,*args,**kwargs):return FakeResponse()
    monkeypatch.setattr(connections.httpx,'Client',FakeClient)
    with TestClient(app) as c:
        register(c,'oauth-a@example.com')
        r=post(c,'/api/integrations/square/oauth/start')
        assert r.status_code==200,r.text
        from urllib.parse import parse_qs,urlparse
        state=parse_qs(urlparse(r.json()['url']).query)['state'][0]
        res=c.get('/api/integrations/square/oauth/callback?code=abc&state='+state,follow_redirects=False)
        assert res.status_code==303
        assert c.get('/api/integrations/square/oauth/callback?code=abc&state='+state,follow_redirects=False).status_code==400
        with Session(engine) as db:
            row=db.scalar(select(connections.SquareConnection))
            assert row and 'private-sandbox-token' not in row.token_ciphertext
            assert connections._decrypted(row.token_ciphertext)=='private-sandbox-token'
    engine.dispose()


def test_sync_failure_rolls_back_order_writes(tmp_path,monkeypatch):
    engine=db_fixture(tmp_path,monkeypatch)
    monkeypatch.setenv('SQUARE_SANDBOX_ACCESS_TOKEN','SANDBOX_TEST_TOKEN')
    def failing(token,method,path,payload=None):
        if path in ('/v2/locations','/v2/payments'):return fake_square(token,method,path,payload)
        raise connections.HTTPException(503,'Sandbox unavailable')
    monkeypatch.setattr(connections,'_api',fake_square)
    with TestClient(app) as c:
        register(c,'failure@example.com')
        assert post(c,'/api/integrations/square/connect-developer-sandbox').status_code==200
        monkeypatch.setattr(connections,'_api',failing)
        assert post(c,'/api/integrations/square/sync').status_code==503
        assert c.get('/api/saas/me').json()['summary']['orders']==0
        assert c.get('/api/integrations/square/status').json()['runs'][0]['status']=='failed'
    engine.dispose()
