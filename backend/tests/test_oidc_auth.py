"""Managed-auth (OIDC) token verification, against a real local JWKS endpoint."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import config, oidc_auth, saas
from app.database import Base
from app.main import app

ISSUER = 'https://idp.example.test'
AUDIENCE = 'guestlift-api'


def _new_key(kid):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid=kid, use='sig', alg='RS256')
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub_pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return {'kid': kid, 'jwk': jwk, 'pem': pem, 'pub_pem': pub_pem}


class _IdP:
    """Tiny identity provider: serves a JWKS and signs tokens."""

    def __init__(self):
        self.keys = [_new_key('key-1')]
        self.fetches = 0
        idp = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                idp.fetches += 1
                body = json.dumps({'keys': [k['jwk'] for k in idp.keys]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}/jwks.json'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def token(self, sub='user_a', key=None, **overrides):
        key = key or self.keys[0]
        now = int(time.time())
        claims = {'sub': sub, 'iss': ISSUER, 'aud': AUDIENCE, 'iat': now, 'exp': now + 300}
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key['pem'], algorithm='RS256', headers={'kid': key['kid']})

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def idp(monkeypatch, tmp_path):
    provider = _IdP()
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'oidc')
    monkeypatch.setenv('GUESTLIFT_OIDC_ISSUER', ISSUER)
    monkeypatch.setenv('GUESTLIFT_OIDC_JWKS_URL', provider.url)
    monkeypatch.setenv('GUESTLIFT_OIDC_AUDIENCE', AUDIENCE)
    engine = create_engine(f"sqlite:///{tmp_path / 'oidc.sqlite'}", connect_args={'check_same_thread': False})
    monkeypatch.setattr(saas, 'engine', engine)
    Base.metadata.create_all(engine)
    oidc_auth.reset_cache()
    yield provider
    provider.close()
    engine.dispose()
    oidc_auth.reset_cache()


def _get(client, token=None, path='/api/saas/me'):
    return client.get(path, headers={'Authorization': f'Bearer {token}'} if token else {})


def test_valid_token_reaches_the_workspace_and_maps_to_oidc_subject(idp):
    with TestClient(app) as c:
        r = _get(c, idp.token('user_a'))
        assert r.status_code == 200, r.text
        assert r.json()['workspace']['workspace_id']


def test_two_users_get_separate_workspaces(idp):
    with TestClient(app) as c:
        a = _get(c, idp.token('user_a')).json()['workspace']['workspace_id']
        b = _get(c, idp.token('user_b')).json()['workspace']['workspace_id']
        again = _get(c, idp.token('user_a')).json()['workspace']['workspace_id']
        assert a != b and a == again


def test_subject_is_namespaced_away_from_local_account_ids(idp):
    with TestClient(app) as c:
        _get(c, idp.token('user_a'))
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    with Session(saas.engine) as db:
        assert db.scalar(select(saas.Workspace.owner_sub)) == 'oidc:user_a'


@pytest.mark.parametrize('token', [None, '', 'not-a-jwt', 'a.b.c'])
def test_missing_or_malformed_token_is_401(idp, token):
    with TestClient(app) as c:
        assert _get(c, token).status_code == 401


def test_expired_token_rejected(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token(exp=int(time.time()) - 3600)).status_code == 401


def test_wrong_issuer_rejected(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token(iss='https://evil.example')).status_code == 401


def test_wrong_audience_rejected_and_missing_audience_rejected(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token(aud='someone-else')).status_code == 401
        assert _get(c, idp.token(aud=None)).status_code == 401


def test_audience_not_enforced_when_not_configured(idp, monkeypatch):
    monkeypatch.delenv('GUESTLIFT_OIDC_AUDIENCE')
    with TestClient(app) as c:
        assert _get(c, idp.token(aud=None)).status_code == 200


def test_authorized_party_is_enforced_when_configured(idp, monkeypatch):
    monkeypatch.setenv('GUESTLIFT_OIDC_AUTHORIZED_PARTIES', 'https://app.example.com, https://www.example.com/')
    with TestClient(app) as c:
        assert _get(c, idp.token(azp='https://app.example.com')).status_code == 200
        assert _get(c, idp.token(azp='https://www.example.com')).status_code == 200  # trailing slash tolerated
        assert _get(c, idp.token(azp='https://evil.example')).status_code == 401
        assert _get(c, idp.token()).status_code == 200  # no azp claim: nothing to compare


def test_authorized_party_not_enforced_when_not_configured(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token(azp='https://anything.example')).status_code == 200


def test_token_without_subject_or_expiry_rejected(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token(sub=None)).status_code == 401
        assert _get(c, idp.token(exp=None)).status_code == 401


def test_token_signed_by_an_unknown_key_rejected(idp):
    attacker = _new_key('key-1')  # same kid, different key material
    with TestClient(app) as c:
        assert _get(c, idp.token(key=attacker)).status_code == 401


def test_unsigned_alg_none_token_rejected(idp):
    now = int(time.time())
    token = jwt.encode({'sub': 'x', 'iss': ISSUER, 'aud': AUDIENCE, 'exp': now + 300}, None, algorithm='none',
                       headers={'kid': 'key-1'})
    with TestClient(app) as c:
        assert _get(c, token).status_code == 401


def test_hmac_signed_with_public_key_rejected(idp):
    """Algorithm-confusion attack: HS256 using the published public key as the secret."""
    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=')
    now = int(time.time())
    header = b64(json.dumps({'alg': 'HS256', 'typ': 'JWT', 'kid': 'key-1'}).encode())
    body = b64(json.dumps({'sub': 'x', 'iss': ISSUER, 'aud': AUDIENCE, 'exp': now + 300}).encode())
    signature = b64(hmac.new(idp.keys[0]['pub_pem'], header + b'.' + body, hashlib.sha256).digest())
    forged = (header + b'.' + body + b'.' + signature).decode()
    with TestClient(app) as c:
        assert _get(c, forged).status_code == 401


def test_key_rotation_is_picked_up_without_restart(idp, monkeypatch):
    monkeypatch.setattr(oidc_auth, 'JWKS_REFRESH_COOLDOWN_SECONDS', 0)
    oidc_auth.reset_cache()
    with TestClient(app) as c:
        assert _get(c, idp.token()).status_code == 200
        idp.keys.append(_new_key('key-2'))
        assert _get(c, idp.token(key=idp.keys[1])).status_code == 200


def test_unknown_key_ids_cannot_make_us_hammer_the_provider(idp):
    with TestClient(app) as c:
        assert _get(c, idp.token()).status_code == 200
        before = idp.fetches
        for i in range(20):
            stranger = _new_key(f'made-up-{i}')
            assert _get(c, idp.token(key=stranger)).status_code == 401
        assert idp.fetches - before <= 1, 'refetches must be rate limited'


def test_identity_provider_outage_is_503_not_401(idp, monkeypatch):
    monkeypatch.setenv('GUESTLIFT_OIDC_JWKS_URL', 'http://127.0.0.1:9/jwks.json')
    oidc_auth.reset_cache()
    with TestClient(app) as c:
        assert _get(c, idp.token()).status_code == 503


def test_local_cookie_session_and_local_signup_do_not_work_in_oidc_mode(idp):
    with TestClient(app) as c:
        c.cookies.set('tablesignal_dev_session', 'anything')
        assert c.get('/api/saas/me').status_code == 401
        assert c.post('/api/local-auth/register', json={'email': 'a@b.co', 'password': 'x' * 14}).status_code == 404
        assert c.post('/api/local-auth/login', json={'email': 'a@b.co', 'password': 'x' * 14}).status_code == 404


def test_mutating_routes_need_no_csrf_header_but_do_need_a_valid_token(idp):
    with TestClient(app) as c:
        assert c.post('/api/saas/profile', json={}).status_code == 401
        ok = c.post('/api/saas/profile', json={'name': 'Cafe Test', 'restaurant_type': 'fast_casual',
                                               'goal': 'customer_retention'},
                    headers={'Authorization': f'Bearer {idp.token()}'})
        assert ok.status_code != 401, ok.text


# --- startup validation ----------------------------------------------------------

def test_default_mode_is_local(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_AUTH_MODE', raising=False)
    monkeypatch.delenv('GUESTLIFT_ENV', raising=False)
    config.validate_auth_config()
    assert config.auth_mode() == 'local'


def test_oidc_mode_without_settings_fails_fast(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'oidc')
    monkeypatch.delenv('GUESTLIFT_OIDC_ISSUER', raising=False)
    monkeypatch.delenv('GUESTLIFT_OIDC_JWKS_URL', raising=False)
    with pytest.raises(RuntimeError, match='GUESTLIFT_OIDC_ISSUER and GUESTLIFT_OIDC_JWKS_URL'):
        with TestClient(app):
            pass


def test_unknown_mode_fails_fast_instead_of_silently_falling_back(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'oidc ')  # whitespace is tolerated
    monkeypatch.setenv('GUESTLIFT_OIDC_ISSUER', ISSUER)
    monkeypatch.setenv('GUESTLIFT_OIDC_JWKS_URL', 'https://x/jwks')
    config.validate_auth_config()
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'oauth')
    with pytest.raises(RuntimeError, match="'local' or 'oidc'"):
        config.validate_auth_config()


def test_production_refuses_local_accounts_and_plain_http_jwks(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_ENV', 'production')
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'local')
    with pytest.raises(RuntimeError, match='requires GUESTLIFT_AUTH_MODE=oidc'):
        config.validate_auth_config()
    monkeypatch.setenv('GUESTLIFT_AUTH_MODE', 'oidc')
    monkeypatch.setenv('GUESTLIFT_OIDC_ISSUER', ISSUER)
    monkeypatch.setenv('GUESTLIFT_OIDC_JWKS_URL', 'http://idp.example/jwks')
    with pytest.raises(RuntimeError, match='https'):
        config.validate_auth_config()
    monkeypatch.setenv('GUESTLIFT_OIDC_JWKS_URL', 'https://idp.example/jwks')
    config.validate_auth_config()
