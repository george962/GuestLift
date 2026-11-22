"""Verify access tokens issued by a managed identity provider (Clerk, Auth0, WorkOS,
Supabase Auth, or any OIDC provider that publishes a JWKS).

The provider owns sign-up, password reset, email verification, MFA and rate
limiting. This module only answers one question per request: "is this bearer
token genuine, current and meant for us?", and if so returns the user's stable
subject. That subject feeds the existing workspace lookup unchanged.

Security choices:
- Only asymmetric algorithms are accepted. ``none`` and HMAC (HS*) are rejected,
  which closes the classic "sign with the public key as an HMAC secret" attack.
- The signing key is picked by the token's ``kid`` from the provider's JWKS, never
  from anything inside the token body.
- ``exp``, ``sub`` and ``iss`` are required; ``aud`` is enforced when configured.
- A bearer header is not sent automatically by browsers, so these requests are not
  exposed to CSRF the way cookie sessions are.
"""
from __future__ import annotations

import threading

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from . import config

SUBJECT_PREFIX = 'oidc:'  # keeps provider subjects distinct from local-account ids
ALLOWED_ALGORITHMS = ('RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512', 'PS256')
LEEWAY_SECONDS = 30
# After a fetch, an unknown `kid` may trigger a refetch at most this often. This stops
# garbage tokens from making us hammer the provider, and bounds how long tokens signed
# by a freshly rotated key can be refused (providers publish new keys before using them).
JWKS_REFRESH_COOLDOWN_SECONDS = 10

_lock = threading.Lock()
_clients: dict[str, PyJWKClient] = {}


def _jwks_client(url: str) -> PyJWKClient:
    with _lock:
        client = _clients.get(url)
        if client is None:
            # lifespan: keep fetched keys for 5 minutes; an unknown kid triggers one refetch.
            client = PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5,
                                 cooldown_duration=JWKS_REFRESH_COOLDOWN_SECONDS)
            _clients[url] = client
        return client


def reset_cache() -> None:
    """Forget cached JWKS clients (used by tests and key-rotation drills)."""
    with _lock:
        _clients.clear()


def _bearer_token(request: Request) -> str:
    header = request.headers.get('authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(status_code=401, detail='Sign in to continue.', headers={'WWW-Authenticate': 'Bearer'})
    return token.strip()


def verify_bearer(request: Request) -> str:
    """Return the authenticated subject (``oidc:<sub>``) or raise 401/503."""
    settings = config.oidc_settings()
    token = _bearer_token(request)
    try:
        signing_key = _jwks_client(settings['jwks_url']).get_signing_key_from_jwt(token)
        options = {'require': ['exp', 'sub', 'iss'], 'verify_aud': bool(settings['audience'])}
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(ALLOWED_ALGORITHMS),
            issuer=settings['issuer'],
            audience=settings['audience'] or None,
            leeway=LEEWAY_SECONDS,
            options=options,
        )
    except PyJWKClientConnectionError:
        # Our dependency is down; this is not the caller's fault and must not look like a bad login.
        raise HTTPException(status_code=503, detail='Authentication service is temporarily unavailable.')
    except PyJWTError:
        raise HTTPException(status_code=401, detail='Your session is invalid or has expired. Sign in again.',
                            headers={'WWW-Authenticate': 'Bearer'})
    parties = settings['authorized_parties']
    azp = claims.get('azp')
    # A token minted for some other frontend app must not work here. When the provider
    # sends no azp claim there is nothing to compare, so the check is skipped.
    if parties and azp is not None and str(azp).rstrip('/') not in parties:
        raise HTTPException(status_code=401, detail='Your session is invalid or has expired. Sign in again.',
                            headers={'WWW-Authenticate': 'Bearer'})
    subject = str(claims['sub']).strip()
    if not subject or len(subject) > 150:
        raise HTTPException(status_code=401, detail='Your session is invalid or has expired. Sign in again.',
                            headers={'WWW-Authenticate': 'Bearer'})
    return SUBJECT_PREFIX + subject
