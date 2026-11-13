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
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, select, delete
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, engine
from .local_auth import authenticated_subject

router = APIRouter(prefix='/api/integrations/square', tags=['Square Sandbox local integration'])
SQUARE_URL = 'https://connect.squareupsandbox.com'
API_VERSION = '2026-09-16'
MAX_PAGES = 8
PAGE_SIZE = 100


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
    # total less separately reported tax and tip: not reconciled against payments or refunds.
    net_sales_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tip_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    if path not in ('/v2/locations', '/v2/orders/search', '/v2/payments'):
        raise ValueError('Unknown Square API operation')
    try:
        with httpx.Client(timeout=18.0, follow_redirects=False) as client:
            response = client.request(method, SQUARE_URL + path,
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
    if exp > datetime.now(timezone.utc) + timedelta(minutes=5):
        return token
    refresh = _decrypted(connection.refresh_ciphertext) if connection.refresh_ciphertext else ''
    app_id = os.getenv('SQUARE_SANDBOX_APP_ID', '')
    app_secret = os.getenv('SQUARE_SANDBOX_APP_SECRET', '')
    if not refresh or not app_id or not app_secret:
        raise HTTPException(503, 'Sandbox OAuth token expired. Reconnect Square.')
    try:
        with httpx.Client(timeout=15.0, follow_redirects=False) as client:
            response = client.post(SQUARE_URL + '/oauth2/token', json={
                'client_id': app_id, 'client_secret': app_secret,
                'grant_type': 'refresh_token', 'refresh_token': refresh,
            })
    except httpx.RequestError:
        raise HTTPException(503, 'Square Sandbox OAuth refresh could not reach Square.')
    if response.status_code != 200:
        raise HTTPException(422, 'Sandbox authorization expired or was revoked. Reconnect Square.')
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
    return dict(source_order_id=str(raw['id']), location_id=str(raw['location_id']),
                created_at=str(raw.get('created_at') or _now()),
                updated_at=str(raw.get('updated_at') or raw.get('created_at') or _now()),
                status=state, customer_id=str(raw['customer_id']) if raw.get('customer_id') else None,
                net_sales_minor=max(0, amount - taxes - tip), discount_minor=max(0, discounts),
                tax_minor=max(0, taxes), tip_minor=max(0, tip), currency=currency)


def _payment_customers(token: str, location_ids: list[str], since: str) -> dict[str, str]:
    """Optional customer IDs from payments; fail closed when required read scope is absent.

    Square doesn't attach a stable customer ID to every order. Payments can
    include a customer_id and order_id; join only exact order IDs from this
    one authorized Sandbox merchant, never inferred names or cards.
    """
    result: dict[str, str] = {}
    for location in location_ids:
        cursor = None
        cursors: set[str] = set()
        for page in range(MAX_PAGES):
            query: dict[str, Any] = {'location_id': location, 'begin_time': since,
                                     'limit': PAGE_SIZE, 'sort_order': 'DESC'}
            if cursor:
                query['cursor'] = cursor
            response = _api(token, 'GET', '/v2/payments', query)
            payments = response.get('payments') or []
            if not isinstance(payments, list):
                raise HTTPException(502, 'Unexpected Square payments response.')
            for payment in payments:
                if not isinstance(payment, dict):
                    continue
                if payment.get('order_id') and payment.get('customer_id') and payment.get('status') == 'COMPLETED':
                    result[str(payment['order_id'])] = str(payment['customer_id'])
            cursor = response.get('cursor')
            if not cursor:
                break
            if cursor in cursors or page == MAX_PAGES - 1:
                raise HTTPException(422, 'Square payment pagination exceeded the supported limit.')
            cursors.add(cursor)
    return result


def _synchronise(wid: str, db: Session, token: str) -> dict:
    connection = _connection(db, wid)
    if connection is None:
        raise HTTPException(409, 'Connect Square Sandbox before syncing.')
    run = SquareSyncRun(id=str(uuid.uuid4()), workspace_id=wid, started_at=_now(), status='running')
    db.add(run)
    db.commit()
    try:
        merchant, locations = _merchant_from_locations(token)
        if merchant != connection.merchant_id:
            raise HTTPException(409, 'This Sandbox token belongs to a different merchant.')
        location_ids = [loc['id'] for loc in locations if loc.get('status') != 'INACTIVE']
        if not location_ids:
            location_ids = [x['id'] for x in locations]
        scanned = inserted = updated = skipped = 0
        since = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        payment_customers = _payment_customers(token, location_ids, since)
        for batch in (location_ids[i:i+10] for i in range(0, len(location_ids), 10)):
            cursor = None
            seen: set[str] = set()
            for page in range(MAX_PAGES):
                payload: dict[str, Any] = {
                    'location_ids': batch, 'limit': PAGE_SIZE, 'return_entries': False,
                    'query': {'filter': {'date_time_filter': {'created_at': {'start_at': since}}},
                              'sort': {'sort_field': 'CREATED_AT', 'sort_order': 'DESC'}},
                }
                if cursor:
                    payload['cursor'] = cursor
                result = _api(token, 'POST', '/v2/orders/search', payload)
                values = result.get('orders') or []
                if not isinstance(values, list):
                    raise HTTPException(502, 'Unexpected Square orders response.')
                for raw in values:
                    scanned += 1
                    parsed = _parse_order(raw)
                    if parsed is None:
                        skipped += 1
                        continue
                    if not parsed['customer_id']:
                        parsed['customer_id'] = payment_customers.get(parsed['source_order_id'])
                    existing = db.scalar(select(SquareOrder).where(
                        SquareOrder.workspace_id == wid, SquareOrder.source_order_id == parsed['source_order_id']))
                    if existing:
                        if parsed['updated_at'] >= existing.updated_at:
                            for key, value in parsed.items():
                                setattr(existing, key, value)
                            updated += 1
                    else:
                        db.add(SquareOrder(id=str(uuid.uuid4()), workspace_id=wid, **parsed))
                        inserted += 1
                db.flush()
                cursor = result.get('cursor')
                if not cursor:
                    break
                if cursor in seen:
                    raise HTTPException(502, 'Square returned a repeated pagination cursor.')
                seen.add(cursor)
                if page == MAX_PAGES - 1:
                    raise HTTPException(422, 'More than 800 orders per location batch. Narrow the window before continuing.')
        run.scanned, run.inserted, run.updated, run.skipped = scanned, inserted, updated, skipped
        run.status = 'completed'
        run.completed_at = _now()
        connection.last_sync_at, connection.last_error = run.completed_at, None
        db.commit()
        return {'run_id': run.id, 'status': run.status, 'scanned': scanned,
                'inserted': inserted, 'updated': updated, 'skipped': skipped,
                'period': 'last_180_days', 'currency': 'USD',
                'limitations': 'Sandbox only. Order totals exclude recorded tax/tip; payment customer IDs may be joined by order ID. Refunds, payment totals, and service charges are not fully reconciled.'}
    except Exception as exc:
        db.rollback()
        # No partial import on failure. Never store API response or token in run log.
        run = db.get(SquareSyncRun, run.id)
        if run:
            run.status, run.completed_at, run.message = 'failed', _now(), 'Square synchronization did not complete.'
        connection = _connection(db, wid)
        if connection:
            connection.last_error = 'Most recent sync failed. Check permissions, API availability or order volume.'
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(502, 'Square synchronization did not complete. See developer logs without credentials.')


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
            'connected': conn is not None, 'environment': 'sandbox',
            'merchant_id': conn.merchant_id if conn else None,
            'credential_mode': conn.credential_mode if conn else None,
            'last_sync_at': conn.last_sync_at if conn else None,
            'last_error': conn.last_error if conn else None,
            'developer_token_configured': bool(os.getenv('SQUARE_SANDBOX_ACCESS_TOKEN')),
            'oauth_configured': all(os.getenv(x) for x in ('SQUARE_SANDBOX_APP_ID', 'SQUARE_SANDBOX_APP_SECRET',
                                 'SQUARE_SANDBOX_REDIRECT_URI', 'TABLESIGNAL_CREDENTIAL_KEY')),
            'runs': [{'status': x.status, 'started_at': x.started_at, 'completed_at': x.completed_at,
                      'scanned': x.scanned, 'inserted': x.inserted, 'updated': x.updated, 'skipped': x.skipped}
                     for x in runs],
            'assisted_requests': [{'provider': x.provider, 'status': x.status, 'created_at': x.created_at}
                                  for x in requests],
            'production_enabled': False,
        }


@router.post('/connect-developer-sandbox')
def connect_developer(sub: str = Depends(authenticated_subject)):
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
def oauth_start(sub: str = Depends(authenticated_subject)):
    app_id = os.getenv('SQUARE_SANDBOX_APP_ID', '')
    secret = os.getenv('SQUARE_SANDBOX_APP_SECRET', '')
    redirect = os.getenv('SQUARE_SANDBOX_REDIRECT_URI', '')
    if not all((app_id, secret, redirect)):
        raise HTTPException(503, 'Configure the Square Sandbox OAuth application first.')
    _key()
    state = secrets.token_urlsafe(40)
    with Session(engine) as db:
        wid = _workspace(db, sub)
        db.add(SquareOAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(),
                                workspace_id=wid, expires_at=int(time.time()) + 600))
        db.commit()
    url = SQUARE_URL + '/oauth2/authorize?' + urlencode({
        'client_id': app_id, 'scope': 'ORDERS_READ PAYMENTS_READ MERCHANT_PROFILE_READ',
        'state': state, 'response_type': 'code', 'redirect_uri': redirect,
    })
    return {'url': url, 'environment': 'sandbox', 'expires_in_seconds': 600}


@router.get('/oauth/callback')
def oauth_callback(code: str = '', state: str = '', error: str = ''):
    # Square redirects from its domain; no session cookie is used here.
    # A random single-use 10-minute state binds the callback to the initiating workspace.
    if error:
        return RedirectResponse('http://localhost:3000/connections?square=denied', status_code=303)
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
            response = client.post(SQUARE_URL + '/oauth2/token', json={
                'client_id': os.getenv('SQUARE_SANDBOX_APP_ID'),
                'client_secret': os.getenv('SQUARE_SANDBOX_APP_SECRET'),
                'code': code, 'grant_type': 'authorization_code',
                'redirect_uri': os.getenv('SQUARE_SANDBOX_REDIRECT_URI'),
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
    return RedirectResponse('http://localhost:3000/connections?square=connected', status_code=303)


@router.post('/sync')
def sync(sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        wid = _workspace(db, sub)
        connection = _connection(db, wid)
        if connection is None:
            raise HTTPException(409, 'Connect a Square Sandbox account before syncing.')
        token = _refresh_oauth(connection, db)
        return _synchronise(wid, db, token)


@router.post('/disconnect')
def disconnect(sub: str = Depends(authenticated_subject)):
    # Deletes only this workspace's Sandbox records and encrypted credentials.
    # For OAuth, the seller should also revoke app access in Square's Sandbox Dashboard.
    with Session(engine) as db:
        wid = _workspace(db, sub)
        db.execute(delete(SquareOrder).where(SquareOrder.workspace_id == wid))
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
