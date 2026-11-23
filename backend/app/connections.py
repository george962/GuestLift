"""LOCAL DEVELOPER ONLY: per-account Square Sandbox OAuth + verified data sync.

This module deliberately never accepts seller-supplied production tokens, never calls
Square production, never exposes encrypted credentials, and has no public deployment
contract. Square Sandbox's real APIs are used for non-real transactions only.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, select, delete
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import config
from .database import Base, engine
from .local_auth import authenticated_subject
from .membership import owner_subject
from .location_entitlements import (SandboxMonitoredLocation, eligible_location,
    selection_enabled, selected_rows, snapshot, utc_now)

router = APIRouter(prefix='/api/integrations/square', tags=['Square Sandbox local integration'])
SQUARE_URL = 'https://connect.squareupsandbox.com'


SQUARE_PRODUCTION_URL = 'https://connect.squareup.com'


def square_environment() -> str:
    """sandbox (default) or production. Production also needs GUESTLIFT_ALLOW_SQUARE_PRODUCTION=1."""
    env = os.getenv('SQUARE_ENVIRONMENT', 'sandbox').strip().lower()
    return env if env in ('sandbox', 'production') else 'invalid'


def validate_square_config() -> None:
    env = square_environment()
    if env == 'invalid':
        raise RuntimeError("SQUARE_ENVIRONMENT must be 'sandbox' or 'production'.")
    if env == 'production' and os.getenv('GUESTLIFT_ALLOW_SQUARE_PRODUCTION') != '1':
        raise RuntimeError('Square production is locked until the go-live checklist passes '
                           '(docs/PILOT_TRUST_PLAN.md Gate P0). Set GUESTLIFT_ALLOW_SQUARE_PRODUCTION=1 to unlock.')


def _square_url() -> str:
    # Tests and local dev point this at the mock Square service; production refuses an override.
    default = SQUARE_PRODUCTION_URL if square_environment() == 'production' else SQUARE_URL
    return os.getenv('SQUARE_API_BASE_URL', default).rstrip('/')


def _square_setting(name: str) -> str:
    """SQUARE_APP_ID etc.; Sandbox may still use the older SQUARE_SANDBOX_* names."""
    value = os.getenv('SQUARE_' + name, '')
    if not value and square_environment() == 'sandbox':
        value = os.getenv('SQUARE_SANDBOX_' + name, '')
    return value
API_VERSION = '2026-09-16'


class SquareConnection(Base):
    __tablename__ = 'square_sandbox_connections'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), unique=True, index=True)
    merchant_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    credential_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[str | None] = mapped_column(String(48), nullable=True)
    connected_at: Mapped[str] = mapped_column(String(48), nullable=False)
    last_sync_at: Mapped[str | None] = mapped_column(String(48), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(220), nullable=True)
    # active | needs_reconnect (Square rejected the token) | revoked (owner turned access off in Square)
    status: Mapped[str] = mapped_column(String(20), default='active', server_default='active')
    environment: Mapped[str] = mapped_column(String(12), default='sandbox', server_default='sandbox')


class SquareOAuthState(Base):
    __tablename__ = 'square_sandbox_oauth_states'
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)


class SquareOrder(Base):
    __tablename__ = 'square_sandbox_orders'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    source_order_id: Mapped[str] = mapped_column(String(160), nullable=False)
    location_id: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[str] = mapped_column(String(55), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(55), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(140), nullable=True)
    # Order total less tax, tip and service charges (Square's net sales before refunds).
    net_sales_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tip_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    service_charge_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    # Calendar day in the location's own time zone, as Square reports it.
    local_date: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(4), nullable=False, default='USD')
    __table_args__ = (UniqueConstraint('workspace_id', 'source_order_id', name='uq_sandbox_order_owner'),)


class SquareSyncRun(Base):
    __tablename__ = 'square_sandbox_sync_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    started_at: Mapped[str] = mapped_column(String(48), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(48), nullable=True)
    status: Mapped[str] = mapped_column(String(18), nullable=False)
    scanned: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(200), default='')


class AssistedSetupRequest(Base):
    __tablename__ = 'assisted_setup_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str] = mapped_column(String(300), default='')
    status: Mapped[str] = mapped_column(String(30), default='requested')
    created_at: Mapped[str] = mapped_column(String(48), nullable=False)


class MonitoredSelection(BaseModel):
    location_ids: list[str] = Field(min_length=1, max_length=25)


class SetupRequest(BaseModel):
    provider: str = Field(pattern='^(square|toast|other)$')
    note: str = Field(default='', max_length=300)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key() -> Fernet:
    secret = os.getenv('TABLESIGNAL_CREDENTIAL_KEY', '')
    if not secret:
        raise HTTPException(503, 'Set TABLESIGNAL_CREDENTIAL_KEY in the local .env before using OAuth.')
    try:
        return Fernet(secret.encode())
    except (ValueError, TypeError):
        raise HTTPException(503, 'The local credential encryption key is not valid.')


def _encrypted(value: str) -> str:
    return _key().encrypt(value.encode()).decode()


def _decrypted(value: str) -> str:
    try:
        return _key().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        raise HTTPException(503, 'Unable to decrypt the stored Sandbox connection. Check your local encryption key.')


def _workspace(db: Session, user_sub: str) -> str:
    # Import here to avoid a circular import with SaaS and SQL model registration.
    from .saas import _get_workspace
    return _get_workspace(db, user_sub).id


def _connection(db: Session, wid: str) -> SquareConnection | None:
    return db.scalar(select(SquareConnection).where(SquareConnection.workspace_id == wid))


def _api(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    # Fixed base URL and path set by code, never from a browser or a Square response.
    if path not in ('/v2/locations', '/v2/orders/search', '/v2/payments', '/v2/refunds'):
        raise ValueError('Unknown Square API operation')
    try:
        with httpx.Client(timeout=18.0, follow_redirects=False) as client:
            response = client.request(method, _square_url() + path,
                                      params=payload if method == 'GET' else None,
                                      json=payload if method == 'POST' else None, headers={
                'Authorization': f'Bearer {token}', 'Square-Version': API_VERSION,
                'Content-Type': 'application/json', 'Accept': 'application/json',
            })
    except httpx.RequestError:
        raise HTTPException(502, 'Square Sandbox could not be reached. Retry after checking your network.')
    if response.status_code in (401, 403):
        raise HTTPException(422, 'Square Sandbox authorization was rejected or lacks required read permissions.')
    if response.status_code == 429 or response.status_code >= 500:
        raise HTTPException(503, f'Square Sandbox temporarily unavailable (HTTP {response.status_code}).')
    if response.status_code >= 400:
        raise HTTPException(502, f'Square Sandbox rejected the {path.split("/")[-1]} request (HTTP {response.status_code}).')
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError('JSON root must be an object')
        return data
    except ValueError:
        raise HTTPException(502, 'Square Sandbox returned an unexpected response.')


def _merchant_from_locations(token: str) -> tuple[str, list[dict]]:
    locations = _api(token, 'GET', '/v2/locations').get('locations') or []
    locations = [loc for loc in locations if isinstance(loc, dict) and loc.get('id')]
    if not locations:
        raise HTTPException(422, 'No Square Sandbox locations are available for this token.')
    merchant_ids = {str(x.get('merchant_id')) for x in locations if x.get('merchant_id')}
    if len(merchant_ids) != 1:
        raise HTTPException(422, 'Could not identify one Sandbox merchant from its locations.')
    return merchant_ids.pop(), locations


def _bind(db: Session, wid: str, merchant: str, mode: str, access: str | None, refresh: str | None,
          expiry: str | None) -> SquareConnection:
    other = db.scalar(select(SquareConnection).where(SquareConnection.merchant_id == merchant,
                                                       SquareConnection.workspace_id != wid))
    if other:
        raise HTTPException(409, 'That Sandbox seller is connected to another local workspace.')
    current = _connection(db, wid)
    if current and current.merchant_id != merchant:
        raise HTTPException(409, 'Disconnect the existing Sandbox seller before connecting a different seller.')
    if current is None:
        current = SquareConnection(id=str(uuid.uuid4()), workspace_id=wid, merchant_id=merchant,
                                   credential_mode=mode, connected_at=_now())
        db.add(current)
    current.credential_mode = mode
    current.status = 'active'
    current.environment = square_environment()
    current.token_ciphertext = _encrypted(access) if access is not None else None
    current.refresh_ciphertext = _encrypted(refresh) if refresh else None
    current.token_expires_at = expiry
    current.last_error = None
    db.commit()
    return current


def _refresh_oauth(connection: SquareConnection, db: Session) -> str:
    if connection.credential_mode == 'developer_env':
        token = os.getenv('SQUARE_SANDBOX_ACCESS_TOKEN', '')
        if not token:
            raise HTTPException(503, 'Sandbox developer token is missing from the backend environment.')
        return token
    if not connection.token_ciphertext:
        raise HTTPException(503, 'Connection is missing its encrypted access token.')
    token = _decrypted(connection.token_ciphertext)
    expires = connection.token_expires_at
    if not expires:
        return token
    try:
        exp = datetime.fromisoformat(expires.replace('Z', '+00:00'))
    except ValueError:
        exp = datetime.now(timezone.utc)
    # Square access tokens last 30 days; refresh a week ahead so scheduled syncs never hit expiry.
    if exp > datetime.now(timezone.utc) + timedelta(days=7):
        return token
    refresh = _decrypted(connection.refresh_ciphertext) if connection.refresh_ciphertext else ''
    app_id = _square_setting('APP_ID')
    app_secret = _square_setting('APP_SECRET')
    if not refresh or not app_id or not app_secret:
        raise HTTPException(503, 'Sandbox OAuth token expired. Reconnect Square.')
    try:
        with httpx.Client(timeout=15.0, follow_redirects=False) as client:
            response = client.post(_square_url() + '/oauth2/token', json={
                'client_id': app_id, 'client_secret': app_secret,
                'grant_type': 'refresh_token', 'refresh_token': refresh,
            })
    except httpx.RequestError:
        raise HTTPException(503, 'Square Sandbox OAuth refresh could not reach Square.')
    if response.status_code != 200:
        raise HTTPException(422, 'Square authorization expired or was revoked. Reconnect Square.')
    data = response.json()
    if not data.get('access_token'):
        raise HTTPException(502, 'Square returned no refreshed access token.')
    connection.token_ciphertext = _encrypted(data['access_token'])
    connection.refresh_ciphertext = _encrypted(data.get('refresh_token', refresh))
    connection.token_expires_at = data.get('expires_at')
    db.commit()
    return data['access_token']


def _parse_order(raw: dict) -> dict | None:
    if not isinstance(raw, dict) or not raw.get('id') or not raw.get('location_id'):
        return None
    state = str(raw.get('state') or '')
    if state not in ('COMPLETED', 'CANCELED'):
        return None  # Open/draft orders must not be counted as completed sales.
    total = raw.get('total_money') or {}
    if not isinstance(total, dict) or not isinstance(total.get('amount'), int):
        return None
    currency = str(total.get('currency') or '')
    if currency != 'USD':
        return None  # USD-only demonstration; don't convert currency without FX evidence.
    amount = int(total['amount'])
    taxes = int((raw.get('total_tax_money') or {}).get('amount') or 0)
    tip = int((raw.get('total_tip_money') or {}).get('amount') or 0)
    discounts = int((raw.get('total_discount_money') or {}).get('amount') or 0)
    service = int((raw.get('total_service_charge_money') or {}).get('amount') or 0)
    return dict(source_order_id=str(raw['id']), location_id=str(raw['location_id']),
                created_at=str(raw.get('created_at') or _now()),
                updated_at=str(raw.get('updated_at') or raw.get('created_at') or _now()),
                status=state, customer_id=str(raw['customer_id']) if raw.get('customer_id') else None,
                net_sales_minor=max(0, amount - taxes - tip - service), discount_minor=max(0, discounts),
                tax_minor=max(0, taxes), tip_minor=max(0, tip), service_charge_minor=max(0, service), currency=currency)


@router.get('/locations')
def available_sandbox_locations(sub: str = Depends(authenticated_subject)):
    if not selection_enabled():
        return {'enabled': False, 'locations': [], 'selected_location_ids': [],
                'selected_count': 0, 'notice': 'The v0.13 Sandbox selection gate is disabled.'}
    with Session(engine) as db:
        wid = _workspace(db, sub)
        conn = _connection(db, wid)
        if not conn:
            raise HTTPException(409, 'Connect a Square Sandbox account first.')
        token = _refresh_oauth(conn, db)
        merchant, locations = _merchant_from_locations(token)
        if merchant != conn.merchant_id:
            raise HTTPException(409, 'Sandbox merchant identity changed. Reconnect.')
        selected = {x.location_id for x in selected_rows(db, wid, merchant)}
        return {
            'enabled': True, 'environment': 'sandbox', 'merchant_id': merchant,
            'locations': [{'id': str(loc['id']), 'name': str(loc.get('name') or loc['id'])[:160],
                           'type': str(loc.get('type') or 'UNKNOWN'),
                           'status': str(loc.get('status') or 'UNKNOWN'),
                           'eligible': eligible_location(loc),
                           'selected': str(loc['id']) in selected} for loc in locations],
            'selected_location_ids': sorted(selected), 'selected_count': len(selected),
            'notice': 'Sandbox eligibility is provisional. Real order-access checks and production location mapping remain launch gates.'
        }


@router.post('/locations/selection')
def save_sandbox_locations(payload: MonitoredSelection, sub: str = Depends(owner_subject)):
    if not selection_enabled():
        raise HTTPException(409, 'Enable the v0.13 local Sandbox location gate first.')
    ids = payload.location_ids
    if any(not isinstance(x, str) or not x.strip() or len(x) > 160 for x in ids) or len(ids) != len(set(ids)):
        raise HTTPException(422, 'Select 1–25 distinct valid location IDs.')
    with Session(engine) as db:
        wid = _workspace(db, sub)
        conn = _connection(db, wid)
        if not conn:
            raise HTTPException(409, 'Connect Square Sandbox before selecting locations.')
        from .saas import Workspace
        w = db.get(Workspace, wid)
        if w and w.subscription_status in ('active', 'trialing'):
            raise HTTPException(409, 'Existing subscription must be canceled and reconciled before changing monitored locations. Prorations are not implemented.')
        token = _refresh_oauth(conn, db)
        merchant, locations = _merchant_from_locations(token)
        if merchant != conn.merchant_id:
            raise HTTPException(409, 'Connected Sandbox merchant does not match.')
        authorized = {str(x['id']): x for x in locations if eligible_location(x)}
        if any(location_id not in authorized for location_id in ids):
            raise HTTPException(422, 'Selection includes an unauthorized, inactive, nonphysical or unrecognized location.')
        db.execute(delete(SandboxMonitoredLocation).where(SandboxMonitoredLocation.workspace_id == wid))
        for loc_id in sorted(ids):
            loc = authorized[loc_id]
            db.add(SandboxMonitoredLocation(workspace_id=wid, location_id=loc_id,
                merchant_id=merchant, name=str(loc.get('name') or loc_id)[:160], selected_at=utc_now()))
        # Eliminate old Sandbox orders from previously monitored but now excluded locations.
        db.execute(delete(SquareOrder).where(
            SquareOrder.workspace_id == wid, SquareOrder.location_id.not_in(ids)))
        db.commit()
        result = snapshot(db, wid, merchant)
        return {'saved': True, 'environment': 'sandbox', 'selected_count': result['quantity'],
                'selected_location_ids': result['ids'],
                'notice': 'Selection saved in the local test database. Stripe TEST will derive its quantity from these server records.'}


@router.get('/status')
def status(sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        wid = _workspace(db, sub)
        conn = _connection(db, wid)
        runs = db.scalars(select(SquareSyncRun).where(SquareSyncRun.workspace_id == wid)
                          .order_by(SquareSyncRun.started_at.desc()).limit(8)).all()
        requests = db.scalars(select(AssistedSetupRequest).where(AssistedSetupRequest.workspace_id == wid)
                             .order_by(AssistedSetupRequest.created_at.desc()).limit(2)).all()
        return {
            'connected': conn is not None, 'environment': square_environment(),
            'connection_status': conn.status if conn else None,
            'merchant_id': conn.merchant_id if conn else None,
            'credential_mode': conn.credential_mode if conn else None,
            'last_sync_at': conn.last_sync_at if conn else None,
            'last_error': conn.last_error if conn else None,
            'developer_token_configured': bool(os.getenv('SQUARE_SANDBOX_ACCESS_TOKEN')),
            'oauth_configured': all((_square_setting('APP_ID'), _square_setting('APP_SECRET'),
                                     _square_setting('REDIRECT_URI'), os.getenv('TABLESIGNAL_CREDENTIAL_KEY'))),
            'runs': [{'status': x.status, 'started_at': x.started_at, 'completed_at': x.completed_at,
                      'scanned': x.scanned, 'inserted': x.inserted, 'updated': x.updated, 'skipped': x.skipped}
                     for x in runs],
            'assisted_requests': [{'provider': x.provider, 'status': x.status, 'created_at': x.created_at}
                                  for x in requests],
            'production_enabled': square_environment() == 'production',
        }


@router.post('/connect-developer-sandbox')
def connect_developer(sub: str = Depends(owner_subject)):
    token = os.getenv('SQUARE_SANDBOX_ACCESS_TOKEN', '')
    if not token:
        raise HTTPException(503, 'Add a Square Sandbox developer access token to the local .env first.')
    merchant, locations = _merchant_from_locations(token)
    with Session(engine) as db:
        wid = _workspace(db, sub)
        _bind(db, wid, merchant, 'developer_env', None, None, None)
    return {'connected': True, 'environment': 'sandbox', 'locations': len(locations),
            'next_step': 'Use the Sync orders action.'}


@router.post('/oauth/start')
def oauth_start(sub: str = Depends(owner_subject)):
    app_id = _square_setting('APP_ID')
    secret = _square_setting('APP_SECRET')
    redirect = _square_setting('REDIRECT_URI')
    if not all((app_id, secret, redirect)):
        raise HTTPException(503, 'Configure the Square Sandbox OAuth application first.')
    _key()
    state = secrets.token_urlsafe(40)
    with Session(engine) as db:
        wid = _workspace(db, sub)
        db.add(SquareOAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(),
                                workspace_id=wid, expires_at=int(time.time()) + 600))
        db.commit()
    url = _square_url() + '/oauth2/authorize?' + urlencode({
        'client_id': app_id, 'scope': 'ORDERS_READ PAYMENTS_READ MERCHANT_PROFILE_READ',
        'state': state, 'response_type': 'code', 'redirect_uri': redirect,
    })
    return {'url': url, 'environment': 'sandbox', 'expires_in_seconds': 600}


@router.get('/oauth/callback')
def oauth_callback(code: str = '', state: str = '', error: str = ''):
    # Square redirects from its domain; no session cookie is used here.
    # A random single-use 10-minute state binds the callback to the initiating workspace.
    if error:
        return RedirectResponse(config.app_url() + '/connections?square=denied', status_code=303)
    if not code or not state or len(code) > 4096 or len(state) > 256:
        raise HTTPException(400, 'Missing or invalid Sandbox authorization response.')
    with Session(engine) as db:
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        record = db.get(SquareOAuthState, state_hash)
        if not record or record.expires_at < int(time.time()):
            raise HTTPException(400, 'Sandbox authorization expired or state was already used.')
        wid = record.workspace_id
        db.delete(record)
        db.commit()  # Consume state before exchanging code (prevent replay).
    try:
        with httpx.Client(timeout=15.0, follow_redirects=False) as client:
            response = client.post(_square_url() + '/oauth2/token', json={
                'client_id': _square_setting('APP_ID'),
                'client_secret': _square_setting('APP_SECRET'),
                'code': code, 'grant_type': 'authorization_code',
                'redirect_uri': _square_setting('REDIRECT_URI'),
            })
    except httpx.RequestError:
        raise HTTPException(502, 'Could not exchange Sandbox authorization code.')
    if response.status_code != 200:
        raise HTTPException(422, 'Square Sandbox authorization exchange was rejected.')
    data = response.json()
    if not data.get('access_token'):
        raise HTTPException(502, 'Square returned no Sandbox access token.')
    token = data['access_token']
    merchant, _ = _merchant_from_locations(token)
    if data.get('merchant_id') and merchant != data['merchant_id']:
        raise HTTPException(422, 'Square merchant identity was inconsistent.')
    with Session(engine) as db:
        _bind(db, wid, merchant, 'oauth', token, data.get('refresh_token'), data.get('expires_at'))
    return RedirectResponse(config.app_url() + '/connections?square=connected', status_code=303)


@router.post('/sync')
def sync(response: Response, sub: str = Depends(authenticated_subject)):
    """Sync now: run the job here for a short time; anything left continues in the background worker."""
    from . import square_sync
    with Session(engine) as db:
        wid = _workspace(db, sub)
        connection = _connection(db, wid)
        if connection is None:
            raise HTTPException(409, 'Connect a Square account before syncing.')
        if connection.status != 'active':
            raise HTTPException(409, 'Reconnect Square before syncing; access was turned off or expired.')
        job = square_sync.enqueue(db, wid, 'manual', claimed=True)
        if not getattr(job, 'claimed_here', False) and not square_sync.claim(db, job.id):
            response.status_code = 202
            return {'status': 'running', 'message': 'A sync is already running.', 'progress': square_sync.progress(db, wid)}
        result = square_sync.execute(db, db.get(square_sync.SquareSyncJob, job.id),
                                     budget_seconds=float(os.getenv('GUESTLIFT_SYNC_INLINE_SECONDS', '20')))
        body = {'status': 'completed' if result['complete'] else 'continuing',
                'scanned': result['scanned'], 'inserted': result['inserted'], 'updated': result['updated'],
                'skipped': result['skipped'], 'refunds': result['refunds'], 'currency': 'USD',
                'progress': square_sync.progress(db, wid),
                'limitations': 'Net sales exclude tax, tips and service charges and subtract refunds. '
                               'Gift cards and comps are not imported separately.'}
        if not result['complete']:
            response.status_code = 202
            body['message'] = 'Importing your history in the background. This page updates as it goes.'
        return body


@router.get('/health')
def data_health(sub: str = Depends(authenticated_subject)):
    from . import square_sync
    with Session(engine) as db:
        return square_sync.health(db, _workspace(db, sub))


@router.get('/reconciliation')
def reconciliation_report(start: str | None = None, end: str | None = None, sub: str = Depends(authenticated_subject)):
    """Daily totals per location, to compare with Square's Sales Summary. Dates are local (YYYY-MM-DD)."""
    from datetime import date as _date
    from . import square_sync
    try:
        stop = _date.fromisoformat(end) if end else (datetime.now(timezone.utc).date() - timedelta(days=1))
        begin = _date.fromisoformat(start) if start else stop - timedelta(days=6)
    except ValueError:
        raise HTTPException(422, 'Use dates like 2026-11-16.')
    if begin > stop or (stop - begin).days > 92:
        raise HTTPException(422, 'Choose a range of up to 93 days with the start before the end.')
    with Session(engine) as db:
        wid = _workspace(db, sub)
        ids = None
        if selection_enabled():
            conn = _connection(db, wid)
            ids = [x.location_id for x in selected_rows(db, wid, conn.merchant_id)] if conn else []
        return square_sync.reconciliation(db, wid, begin, stop, ids)


@router.post('/webhook')
async def square_webhook(request: Request):
    """Square notifications. Handles oauth.authorization.revoked: stop syncing and delete the token."""
    import base64
    import hmac as _hmac
    import json as _json
    key, url = os.getenv('SQUARE_WEBHOOK_SIGNATURE_KEY', ''), os.getenv('SQUARE_WEBHOOK_URL', '')
    if not key or not url:
        raise HTTPException(503, 'Square webhooks are not configured.')
    body = await request.body()
    expected = base64.b64encode(_hmac.new(key.encode(), url.encode() + body, hashlib.sha256).digest()).decode()
    if not _hmac.compare_digest(expected, request.headers.get('x-square-hmacsha256-signature', '')):
        raise HTTPException(401, 'Invalid Square signature.')
    try:
        event = _json.loads(body)
    except ValueError:
        raise HTTPException(400, 'Invalid JSON.')
    if event.get('type') == 'oauth.authorization.revoked':
        from . import square_sync
        with Session(engine) as db:
            conn = db.scalar(select(SquareConnection).where(SquareConnection.merchant_id == str(event.get('merchant_id'))))
            if conn:
                conn.status = 'revoked'
                conn.token_ciphertext = conn.refresh_ciphertext = None
                conn.last_error = 'Access was turned off in Square.'
                for job in db.scalars(select(square_sync.SquareSyncJob).where(
                        square_sync.SquareSyncJob.workspace_id == conn.workspace_id,
                        square_sync.SquareSyncJob.status.in_(('queued', 'running')))):
                    job.status, job.last_error = 'failed', 'Access revoked in Square.'
                db.commit()
    return {'received': True}


@router.post('/disconnect')
def disconnect(sub: str = Depends(owner_subject)):
    # Deletes only this workspace's Sandbox records and encrypted credentials.
    # For OAuth, the seller should also revoke app access in Square's Sandbox Dashboard.
    with Session(engine) as db:
        wid = _workspace(db, sub)
        from .square_sync import SquareLocationState, SquareRefund, SquareSyncJob
        for model in (SquareOrder, SquareRefund, SquareLocationState, SquareSyncJob, SandboxMonitoredLocation):
            db.execute(delete(model).where(model.workspace_id == wid))
        conn = _connection(db, wid)
        if conn:
            db.delete(conn)
        db.commit()
    return {'disconnected': True, 'orders_deleted': True,
            'notice': 'Local records and credentials deleted. Revoke OAuth permissions in Square Sandbox separately.'}


@router.post('/assisted-setup', status_code=201)
def assisted_setup(data: SetupRequest, sub: str = Depends(authenticated_subject)):
    # Store an internal *request*, not a promise of a live human support service.
    with Session(engine) as db:
        wid = _workspace(db, sub)
        latest = db.scalar(select(AssistedSetupRequest).where(
            AssistedSetupRequest.workspace_id == wid,
            AssistedSetupRequest.status == 'requested', AssistedSetupRequest.provider == data.provider))
        if latest:
            return {'request_id': latest.id, 'status': 'requested', 'duplicate': True}
        row = AssistedSetupRequest(id=str(uuid.uuid4()), workspace_id=wid, provider=data.provider,
                                   note=data.note.strip(), created_at=_now(), status='requested')
        db.add(row)
        db.commit()
        return {'request_id': row.id, 'status': 'requested',
                'notice': 'Stored locally for developer review; no support notification was sent.'}
