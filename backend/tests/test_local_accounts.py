"""End-to-end local account tests: real cookies, hashed passwords, DB isolation, CSRF."""
from __future__ import annotations

import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app import saas, local_auth
from app.database import Base
from app.main import app

ORIGIN = {'Origin':'http://localhost:3000'}


def setup_db(tmp_path,monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path/'local_accounts.sqlite'),connect_args={'check_same_thread':False})
    monkeypatch.setattr(local_auth, 'engine', engine)
    monkeypatch.setattr(saas, 'engine', engine)
    Base.metadata.create_all(engine)
    return engine


def register(client, address, pwd='fourteen-characters-safe'):
    return client.post('/api/local-auth/register',json={'email':address,'password':pwd},headers=ORIGIN)


def csrf(client):
    r=client.get('/api/local-auth/session')
    assert r.status_code==200
    assert r.json()['authenticated']
    return r.json()['csrf_token']


def test_full_local_user_workflow_and_workspace_isolation(tmp_path,monkeypatch):
    engine=setup_db(tmp_path,monkeypatch)
    with TestClient(app) as one, TestClient(app) as two:
        r=register(one, 'OWNER@EXAMPLE.COM')
        assert r.status_code==201, r.text
        cookie=one.cookies.get(local_auth.SESSION_COOKIE)
        assert cookie and 'httponly' in r.headers['set-cookie'].lower()
        assert 'samesite=strict' in r.headers['set-cookie'].lower()
        with Session(engine) as db:
            person=db.scalar(select(local_auth.LocalUser).where(local_auth.LocalUser.email=='owner@example.com'))
            assert person is not None
            assert 'fourteen-characters-safe' not in person.password_hash
            assert db.get(local_auth.LocalSession,hashlib.sha256(cookie.encode()).hexdigest()) is not None
        assert one.get('/api/saas/me').json()['summary']['orders']==56
        assert two.get('/api/saas/me').status_code==401
        assert register(two,'second@example.com').status_code==201
        a=one.get('/api/saas/me').json()['workspace']
        b=two.get('/api/saas/me').json()['workspace']
        assert a['workspace_id']!=b['workspace_id']
        assert a['plan']=='sandbox' and b['plan']=='sandbox'
        change={'name':'Owner Restaurant','restaurant_type':'cafe','goal':'customer_retention'}
        post=one.post('/api/saas/profile',json=change,headers={**ORIGIN,'X-CSRF-Token':csrf(one)})
        assert post.status_code==200,post.text
        assert one.get('/api/saas/me').json()['workspace']['name']=='Owner Restaurant'
        assert two.get('/api/saas/me').json()['workspace']['name']=='My Restaurant'
        assert one.post('/api/saas/demo-reset',headers={**ORIGIN,'X-CSRF-Token':csrf(one)}).status_code==200
        assert two.get('/api/saas/me').json()['summary']['orders']==56
    engine.dispose()


def test_authentication_csrf_logout_password_rotation_and_relogin(tmp_path,monkeypatch):
    engine=setup_db(tmp_path,monkeypatch)
    with TestClient(app) as a, TestClient(app) as b:
        assert register(a,'local@example.com').status_code==201
        assert register(b,'local@example.com').status_code==409
        assert a.post('/api/saas/profile',json={},headers=ORIGIN).status_code==403
        assert a.post('/api/saas/profile',json={},headers={'X-CSRF-Token':csrf(a)}).status_code==403
        assert a.post('/api/local-auth/logout',headers=ORIGIN).status_code==403
        assert a.get('/api/local-auth/session').json()['authenticated']
        assert b.post('/api/local-auth/login',json={'email':'local@example.com','password':'wrong'},headers=ORIGIN).status_code==401
        assert b.post('/api/local-auth/login',json={'email':'local@example.com','password':'fourteen-characters-safe'},headers=ORIGIN).status_code==200
        c=a.post('/api/local-auth/change-password',json={'current_password':'fourteen-characters-safe','new_password':'this-is-the-new-password'},headers={**ORIGIN,'X-CSRF-Token':csrf(a)})
        assert c.status_code==200,c.text
        assert b.get('/api/local-auth/session').json()['authenticated'] is False
        assert a.post('/api/local-auth/logout',headers={**ORIGIN,'X-CSRF-Token':csrf(a)}).status_code==200
        assert a.get('/api/saas/me').status_code==401
        assert a.post('/api/local-auth/login',json={'email':'local@example.com','password':'fourteen-characters-safe'},headers=ORIGIN).status_code==401
        assert a.post('/api/local-auth/login',json={'email':'local@example.com','password':'this-is-the-new-password'},headers=ORIGIN).status_code==200
        assert a.get('/api/saas/me').json()['workspace']['name']=='My Restaurant'
    engine.dispose()


def test_no_cross_site_registration_and_no_short_password(tmp_path,monkeypatch):
    engine=setup_db(tmp_path,monkeypatch)
    with TestClient(app) as client:
        assert client.post('/api/local-auth/register',json={'email':'x@example.com','password':'some-long-password'}).status_code==403
        assert client.post('/api/local-auth/register',json={'email':'x@example.com','password':'some-long-password'},headers={'Origin':'https://evil.example'}).status_code==403
        assert register(client,'x@example.com','short').status_code in (422,400)
        assert client.get('/api/local-auth/session').json()['authenticated'] is False
    engine.dispose()


def test_development_cors_allows_credentialed_browser_calls():
    with TestClient(app) as client:
        r=client.options('/api/local-auth/session',headers={
            'Origin':'http://localhost:3000',
            'Access-Control-Request-Method':'GET'
        })
        assert r.status_code==200
        assert r.headers.get('access-control-allow-credentials')=='true'
        assert r.headers.get('access-control-allow-origin')=='http://localhost:3000'
