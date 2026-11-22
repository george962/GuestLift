"""Mock Square API for the journey harness. Never deploy this.

Implements the subset TableSignal calls: OAuth authorize/token, ListLocations,
SearchOrders and ListPayments, with cursor pagination. The dataset is
deterministic (seeded) and dated relative to "now", so every run produces the
same counts. GET /__mock/truth returns the expected totals for assertions.
Fault injection: POST /__mock/faults {"status": 429, "count": 1, "after": 0}.

Run: uvicorn mock_square.app:app --port 8100
"""
from __future__ import annotations

import os
import random
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

MERCHANT_ID = 'MOCK_MERCHANT_1'
DEV_TOKEN = 'mock-dev-token'
LOCATIONS = [
    {'id': 'LOC_HARBOR', 'name': 'Harbor Street', 'status': 'ACTIVE', 'type': 'PHYSICAL'},
    {'id': 'LOC_MARKET', 'name': 'Market Square', 'status': 'ACTIVE', 'type': 'PHYSICAL'},
    {'id': 'LOC_ONLINE', 'name': 'Online Store', 'status': 'ACTIVE', 'type': 'MOBILE'},
    {'id': 'LOC_CLOSED', 'name': 'Old Pier (closed)', 'status': 'INACTIVE', 'type': 'PHYSICAL'},
]
DAYS = 60

app = FastAPI(title='Mock Square API', docs_url=None, redoc_url=None)
_state: dict = {'tokens': {DEV_TOKEN}, 'codes': {}, 'refresh': {}, 'faults': []}


def _app_id() -> str:
    return os.getenv('MOCK_SQUARE_APP_ID', 'mock-app-id')


def _app_secret() -> str:
    return os.getenv('MOCK_SQUARE_APP_SECRET', 'mock-app-secret')


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds').replace('+00:00', 'Z')


def build_dataset(now: datetime | None = None, seed: int = 7) -> tuple[list[dict], list[dict]]:
    """Orders and payments for the two eligible locations plus noise the importer must skip."""
    rng = random.Random(seed)
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    customers = [f'CUST_{i:03d}' for i in range(30)]
    orders, payments = [], []
    n = 0
    for day in range(DAYS):
        for loc in LOCATIONS[:2]:
            for _ in range(rng.randint(2, 4)):
                n += 1
                created = now - timedelta(days=day, hours=rng.randint(1, 12), minutes=rng.randint(0, 59))
                subtotal = rng.randint(900, 6500)
                discount = rng.choice([0, 0, 0, 0, 200, 500])
                tax = round((subtotal - discount) * 0.08)
                tip = rng.choice([0, 100, 200, 300])
                state = 'CANCELED' if n % 41 == 0 else ('OPEN' if n % 53 == 0 else 'COMPLETED')
                oid = f'ORD_{n:05d}'
                orders.append({
                    'id': oid, 'location_id': loc['id'], 'state': state,
                    'created_at': _iso(created), 'updated_at': _iso(created + timedelta(minutes=5)),
                    'total_money': {'amount': subtotal - discount + tax + tip, 'currency': 'USD'},
                    'total_tax_money': {'amount': tax, 'currency': 'USD'},
                    'total_tip_money': {'amount': tip, 'currency': 'USD'},
                    'total_discount_money': {'amount': discount, 'currency': 'USD'},
                })
                if state == 'COMPLETED' and rng.random() < 0.55:
                    payments.append({'id': f'PAY_{n:05d}', 'order_id': oid, 'location_id': loc['id'],
                                     'status': 'COMPLETED', 'customer_id': rng.choice(customers),
                                     'created_at': _iso(created)})
    return orders, payments


def truth(orders: list[dict], payments: list[dict]) -> dict:
    imported = [o for o in orders if o['state'] in ('COMPLETED', 'CANCELED')]
    completed = [o for o in imported if o['state'] == 'COMPLETED']
    net = lambda o: o['total_money']['amount'] - o['total_tax_money']['amount'] - o['total_tip_money']['amount']
    return {
        'merchant_id': MERCHANT_ID,
        'eligible_location_ids': [l['id'] for l in LOCATIONS if l['status'] == 'ACTIVE' and l['type'] == 'PHYSICAL'],
        'importable_orders': len(imported), 'completed_orders': len(completed),
        'skipped_open_orders': sum(1 for o in orders if o['state'] == 'OPEN'),
        'completed_net_sales_minor': sum(net(o) for o in completed),
        'identified_completed_orders': len({p['order_id'] for p in payments}),
        'distinct_customers': len({p['customer_id'] for p in payments}),
    }


ORDERS, PAYMENTS = build_dataset()


def _authorize(authorization: str | None) -> None:
    token = (authorization or '').removeprefix('Bearer ').strip()
    if token not in _state['tokens']:
        raise HTTPException(401, 'UNAUTHORIZED')
    if _state['faults']:
        fault = _state['faults'].pop(0)
        if fault:
            raise HTTPException(fault, 'INJECTED_FAULT')


def _page(items: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    start = int(cursor or 0)
    end = start + max(1, min(limit, 100))
    return items[start:end], (str(end) if end < len(items) else None)


@app.get('/oauth2/authorize')
def authorize(client_id: str, state: str, redirect_uri: str, scope: str = '', response_type: str = 'code'):
    if client_id != _app_id():
        raise HTTPException(400, 'unknown client_id')
    code = 'mock-code-' + secrets.token_urlsafe(12)
    _state['codes'][code] = redirect_uri
    return RedirectResponse(redirect_uri + '?' + urlencode({'code': code, 'state': state}), status_code=302)


@app.post('/oauth2/token')
async def token(request: Request):
    body = await request.json()
    if body.get('client_id') != _app_id() or body.get('client_secret') != _app_secret():
        return JSONResponse({'errors': [{'code': 'UNAUTHORIZED'}]}, status_code=401)
    grant = body.get('grant_type')
    if grant == 'authorization_code':
        if _state['codes'].pop(body.get('code'), None) != body.get('redirect_uri'):
            return JSONResponse({'errors': [{'code': 'INVALID_GRANT'}]}, status_code=400)
    elif grant == 'refresh_token':
        if body.get('refresh_token') not in _state['refresh']:
            return JSONResponse({'errors': [{'code': 'INVALID_GRANT'}]}, status_code=400)
    else:
        return JSONResponse({'errors': [{'code': 'UNSUPPORTED_GRANT'}]}, status_code=400)
    access, refresh = 'mock-at-' + secrets.token_urlsafe(16), 'mock-rt-' + secrets.token_urlsafe(16)
    _state['tokens'].add(access)
    _state['refresh'][refresh] = access
    return {'access_token': access, 'refresh_token': refresh, 'token_type': 'bearer',
            'merchant_id': MERCHANT_ID, 'expires_at': _iso(datetime.now(timezone.utc) + timedelta(days=30))}


@app.get('/v2/locations')
def locations(authorization: str | None = Header(None)):
    _authorize(authorization)
    return {'locations': [{**l, 'merchant_id': MERCHANT_ID, 'currency': 'USD', 'business_name': 'Harbor Café Group'}
                          for l in LOCATIONS]}


@app.post('/v2/orders/search')
async def search_orders(request: Request, authorization: str | None = Header(None)):
    _authorize(authorization)
    body = await request.json()
    wanted = set(body.get('location_ids') or [])
    start_at = (((body.get('query') or {}).get('filter') or {}).get('date_time_filter') or {}).get('created_at', {}).get('start_at')
    items = [o for o in ORDERS if o['location_id'] in wanted and (not start_at or o['created_at'] >= start_at)]
    page, cursor = _page(items, body.get('cursor'), int(body.get('limit') or 100))
    return {'orders': page, **({'cursor': cursor} if cursor else {})}


@app.get('/v2/payments')
def list_payments(location_id: str, begin_time: str | None = None, cursor: str | None = None, limit: int = 100,
                  authorization: str | None = Header(None), sort_order: str = 'DESC'):
    _authorize(authorization)
    items = [p for p in PAYMENTS if p['location_id'] == location_id and (not begin_time or p['created_at'] >= begin_time)]
    page, nxt = _page(items, cursor, limit)
    return {'payments': page, **({'cursor': nxt} if nxt else {})}


@app.get('/__mock/truth')
def mock_truth():
    return truth(ORDERS, PAYMENTS)


@app.post('/__mock/faults')
async def faults(request: Request):
    body = await request.json()
    # `after` lets that many API calls succeed first, to fail mid-sync.
    _state['faults'] = [0] * int(body.get('after', 0)) + [int(body.get('status', 429))] * int(body.get('count', 1))
    return {'queued': len(_state['faults'])}
