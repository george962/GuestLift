"""Mock Square API for the journey harness. Never deploy this.

Implements the subset TableSignal calls: OAuth authorize/token, ListLocations,
SearchOrders, ListPayments and ListPaymentRefunds, with cursor pagination and date ranges. The dataset is
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
    {'id': 'LOC_HARBOR', 'name': 'Harbor Street', 'status': 'ACTIVE', 'type': 'PHYSICAL', 'timezone': 'America/Los_Angeles'},
    {'id': 'LOC_MARKET', 'name': 'Market Square', 'status': 'ACTIVE', 'type': 'PHYSICAL', 'timezone': 'America/New_York'},
    {'id': 'LOC_ONLINE', 'name': 'Online Store', 'status': 'ACTIVE', 'type': 'MOBILE', 'timezone': 'America/New_York'},
    {'id': 'LOC_CLOSED', 'name': 'Old Pier (closed)', 'status': 'INACTIVE', 'type': 'PHYSICAL', 'timezone': 'America/New_York'},
]
DAYS = 120  # ~1,400 orders: well past the old 800-order sync cap
BOOST_DAYS = 35


def _last_week(now, loc):
    from zoneinfo import ZoneInfo
    today = now.astimezone(ZoneInfo(loc['timezone'])).date()
    return today - timedelta(days=today.weekday() + 7)  # Monday of the last complete week


def _complete_week(now):
    """Monday of the last week that has ended at both eligible locations: what the brief reports."""
    return min(_last_week(now, loc) for loc in LOCATIONS[:2])


app = FastAPI(title='Mock Square API', docs_url=None, redoc_url=None)
_state: dict = {'tokens': {DEV_TOKEN}, 'codes': {}, 'refresh': {}, 'faults': []}


def _app_id() -> str:
    return os.getenv('MOCK_SQUARE_APP_ID', 'mock-app-id')


def _app_secret() -> str:
    return os.getenv('MOCK_SQUARE_APP_SECRET', 'mock-app-secret')


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec='seconds').replace('+00:00', 'Z')


def build_dataset(now: datetime | None = None, seed: int = 7) -> tuple[list[dict], list[dict], list[dict]]:
    """Orders, payments and refunds for the two eligible locations plus noise the importer must skip."""
    rng = random.Random(seed)
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    customers = [f'CUST_{i:03d}' for i in range(30)]
    orders, payments, refunds = [], [], []
    n = 0
    from zoneinfo import ZoneInfo as _Z
    for day in range(DAYS):
        for loc in LOCATIONS[:2]:
            when = (now.astimezone(_Z(loc['timezone'])) - timedelta(days=day)).date()
            count = rng.randint(4, 8)
            # Planted effects the weekly brief and outcome readouts must find (see truth()['planted']):
            if loc['id'] == 'LOC_HARBOR' and when.weekday() >= 5 and day < BOOST_DAYS:
                count += 6  # weekend lift at Harbor Street since the "earlier brunch" change
            if loc['id'] == 'LOC_MARKET' and when.weekday() < 5 and _complete_week(now) <= when < _complete_week(now) + timedelta(days=7):
                count = max(1, count - 4)  # weekday dip at Market Square last week
            for _ in range(count):
                n += 1
                # Opening hours in the store's own time zone (7am-10pm), so evening orders fall on the
                # next UTC day: a sync that ignores time zones gets the daily totals wrong.
                from zoneinfo import ZoneInfo
                local_day = (now.astimezone(ZoneInfo(loc['timezone'])) - timedelta(days=day)).date()
                created = datetime(local_day.year, local_day.month, local_day.day, rng.randint(7, 21), rng.randint(0, 59),
                                   tzinfo=ZoneInfo(loc['timezone'])).astimezone(timezone.utc)
                if created > now:
                    created = now - timedelta(minutes=rng.randint(5, 50))
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
                paid_at = created + timedelta(minutes=1)
                if state == 'COMPLETED' and rng.random() < 0.55:
                    payments.append({'id': f'PAY_{n:05d}', 'order_id': oid, 'location_id': loc['id'],
                                     'status': 'COMPLETED', 'customer_id': rng.choice(customers),
                                     'created_at': _iso(paid_at)})
                refunded_at = created + timedelta(days=1)
                if state == 'COMPLETED' and n % 37 == 0 and refunded_at < now:
                    refunds.append({'id': f'REF_{n:05d}', 'order_id': oid, 'location_id': loc['id'],
                                    'status': 'PENDING' if n % 185 == 0 else 'COMPLETED',
                                    'amount_money': {'amount': (subtotal - discount) // 2, 'currency': 'USD'},
                                    'created_at': _iso(refunded_at)})
    return orders, payments, refunds


def truth(orders: list[dict], payments: list[dict], refunds: list[dict] | None = None, now: datetime | None = None) -> dict:
    """Expected figures, computed independently of TableSignal's importer."""
    reference_now = now if now is not None else DATASET_REFERENCE_NOW
    from zoneinfo import ZoneInfo
    refunds = refunds or []
    imported = [o for o in orders if o['state'] in ('COMPLETED', 'CANCELED')]
    completed = [o for o in imported if o['state'] == 'COMPLETED']
    net = lambda o: o['total_money']['amount'] - o['total_tax_money']['amount'] - o['total_tip_money']['amount']
    tz = {l['id']: ZoneInfo(l['timezone']) for l in LOCATIONS}
    day = lambda ts, loc: datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(tz[loc]).date().isoformat()
    done_refunds = [r for r in refunds if r['status'] == 'COMPLETED']
    daily: dict = {}
    blank = lambda: {'orders': 0, 'gross_sales_minor': 0, 'discounts_minor': 0, 'refunds_minor': 0,
                     'net_sales_minor': 0, 'tax_minor': 0, 'tips_minor': 0}
    for o in completed:
        d = daily.setdefault(o['location_id'], {}).setdefault(day(o['created_at'], o['location_id']), blank())
        d['orders'] += 1
        d['net_sales_minor'] += net(o)
        d['discounts_minor'] += o['total_discount_money']['amount']
        d['gross_sales_minor'] += net(o) + o['total_discount_money']['amount']
        d['tax_minor'] += o['total_tax_money']['amount']
        d['tips_minor'] += o['total_tip_money']['amount']
    for r in done_refunds:
        d = daily.setdefault(r['location_id'], {}).setdefault(day(r['created_at'], r['location_id']), blank())
        d['refunds_minor'] += r['amount_money']['amount']
        d['net_sales_minor'] -= r['amount_money']['amount']
    refunded = sum(r['amount_money']['amount'] for r in done_refunds)
    return {
        'refunds_minor': refunded, 'completed_refunds': len(done_refunds),
        'planted': {'market_weekday_dip_week': _complete_week(reference_now).isoformat(),
                    'harbor_weekend_lift_since_days': BOOST_DAYS},
        'net_sales_after_refunds_minor': sum(net(o) for o in completed) - refunded,
        'daily': daily,
        'merchant_id': MERCHANT_ID,
        'eligible_location_ids': [l['id'] for l in LOCATIONS if l['status'] == 'ACTIVE' and l['type'] == 'PHYSICAL'],
        'importable_orders': len(imported), 'completed_orders': len(completed),
        'skipped_open_orders': sum(1 for o in orders if o['state'] == 'OPEN'),
        'completed_net_sales_minor': sum(net(o) for o in completed),
        'identified_completed_orders': len({p['order_id'] for p in payments}),
        'distinct_customers': len({p['customer_id'] for p in payments}),
    }


DATASET_REFERENCE_NOW = datetime.now(timezone.utc).replace(microsecond=0)
ORDERS, PAYMENTS, REFUNDS = build_dataset(now=DATASET_REFERENCE_NOW)


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
    window = (((body.get('query') or {}).get('filter') or {}).get('date_time_filter') or {}).get('created_at', {})
    start_at, end_at = window.get('start_at'), window.get('end_at')
    items = [o for o in ORDERS if o['location_id'] in wanted and (not start_at or o['created_at'] >= start_at)
             and (not end_at or o['created_at'] < end_at)]
    page, cursor = _page(items, body.get('cursor'), int(body.get('limit') or 100))
    return {'orders': page, **({'cursor': cursor} if cursor else {})}


@app.get('/v2/payments')
def list_payments(location_id: str, begin_time: str | None = None, end_time: str | None = None,
                  cursor: str | None = None, limit: int = 100,
                  authorization: str | None = Header(None), sort_order: str = 'DESC'):
    _authorize(authorization)
    items = [p for p in PAYMENTS if p['location_id'] == location_id and (not begin_time or p['created_at'] >= begin_time)
             and (not end_time or p['created_at'] < end_time)]
    page, nxt = _page(items, cursor, limit)
    return {'payments': page, **({'cursor': nxt} if nxt else {})}


@app.get('/v2/refunds')
def list_refunds(location_id: str, begin_time: str | None = None, end_time: str | None = None,
                 cursor: str | None = None, limit: int = 100,
                 authorization: str | None = Header(None), sort_order: str = 'DESC'):
    _authorize(authorization)
    items = [r for r in REFUNDS if r['location_id'] == location_id and (not begin_time or r['created_at'] >= begin_time)
             and (not end_time or r['created_at'] < end_time)]
    page, nxt = _page(items, cursor, limit)
    return {'refunds': page, **({'cursor': nxt} if nxt else {})}


@app.get('/__mock/truth')
def mock_truth():
    return truth(ORDERS, PAYMENTS, REFUNDS)


@app.post('/__mock/faults')
async def faults(request: Request):
    body = await request.json()
    # `after` lets that many API calls succeed first, to fail mid-sync.
    _state['faults'] = [0] * int(body.get('after', 0)) + [int(body.get('status', 429))] * int(body.get('count', 1))
    return {'queued': len(_state['faults'])}
