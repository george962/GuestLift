"""M3: checkpointed backfill, refunds, local days, retries, reconnect/revocation, worker, health."""
import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import connections, square_sync, worker
from journey_support import harness  # noqa: F401


def _ready(h):
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    return h.truth()


def _orders(db):
    return db.scalar(select(func.count()).select_from(connections.SquareOrder))


def test_backfill_passes_the_old_800_order_cap_and_matches_square(harness):
    truth = _ready(harness)
    assert truth['importable_orders'] > 800
    r = harness.post('/api/integrations/square/sync')
    assert r.status_code == 200 and r.json()['status'] == 'completed'
    assert r.json()['inserted'] == truth['importable_orders']
    assert r.json()['refunds'] == truth['completed_refunds']  # the pending refund is ignored
    s = harness.get('/api/saas/me').json()['summary']
    assert s['orders'] == truth['completed_orders']
    assert s['net_sales_minor'] == truth['net_sales_after_refunds_minor']


def test_reconciliation_matches_square_per_location_per_local_day(harness):
    truth = _ready(harness)
    harness.post('/api/integrations/square/sync')
    days = sorted({d for loc in truth['daily'].values() for d in loc})
    # Up to 93 days per request; walk the whole history in chunks.
    got: dict = {}
    start = date.fromisoformat(days[0])
    while start <= date.fromisoformat(days[-1]):
        end = min(start + timedelta(days=92), date.fromisoformat(days[-1]))
        r = harness.get(f'/api/integrations/square/reconciliation?start={start}&end={end}')
        assert r.status_code == 200, r.text
        for row in r.json()['days']:
            got.setdefault(row['location_id'], {})[row['date']] = {k: row[k] for k in (
                'orders', 'gross_sales_minor', 'discounts_minor', 'refunds_minor', 'net_sales_minor', 'tax_minor', 'tips_minor')}
        start = end + timedelta(days=1)
    assert got == truth['daily']


def test_local_day_follows_the_location_time_zone(harness):
    from zoneinfo import ZoneInfo
    _ready(harness)
    harness.post('/api/integrations/square/sync')
    zones = {'LOC_HARBOR': ZoneInfo('America/Los_Angeles'), 'LOC_MARKET': ZoneInfo('America/New_York')}
    crossed = 0
    with Session(connections.engine) as db:
        for o in db.scalars(select(connections.SquareOrder)):
            utc = datetime.fromisoformat(o.created_at.replace('Z', '+00:00'))
            expected = utc.astimezone(zones[o.location_id]).date().isoformat()
            assert o.local_date == expected, (o.source_order_id, o.created_at, o.local_date)
            crossed += expected != utc.date().isoformat()
    assert crossed > 100, 'fixture should include evening orders that fall on the next UTC day'


def test_crash_mid_backfill_resumes_without_duplicates(harness, monkeypatch):
    truth = _ready(harness)
    # 57 weekly windows per location x 3 calls each; fail inside the first location's recent (busy) weeks.
    harness.square.post('/__mock/faults', json={'status': 503, 'count': 50, 'after': 165})
    assert harness.post('/api/integrations/square/sync').status_code == 503
    with Session(connections.engine) as db:
        partial = _orders(db)
        job = db.scalar(select(square_sync.SquareSyncJob))
        assert 0 < partial < truth['importable_orders'], 'expected committed windows before the failure'
        assert job.status == 'queued' and job.attempts == 1  # will retry, with backoff
        job.run_after = 0; db.commit()
    from mock_square import app as mock
    mock._state['faults'] = []
    monkeypatch.setattr(worker, 'engine', connections.engine)
    while worker.run_once(slice_seconds=30):
        pass
    with Session(connections.engine) as db:
        assert _orders(db) == truth['importable_orders']
        ids = db.scalars(select(connections.SquareOrder.source_order_id)).all()
        assert len(ids) == len(set(ids))
        assert db.scalar(select(square_sync.SquareSyncJob)).status == 'succeeded'


def test_time_budget_continues_in_background(harness, monkeypatch):
    truth = _ready(harness)
    monkeypatch.setenv('GUESTLIFT_SYNC_INLINE_SECONDS', '0')
    r = harness.post('/api/integrations/square/sync')
    assert r.status_code == 202 and r.json()['status'] == 'continuing'
    assert harness.get('/api/integrations/square/health').json()['status'] == 'importing'
    monkeypatch.setattr(worker, 'engine', connections.engine)
    while worker.run_once(slice_seconds=30):
        pass
    h = harness.get('/api/integrations/square/health').json()
    assert h['status'] == 'healthy' and h['backfill']['percent'] == 100
    assert harness.get('/api/saas/me').json()['summary']['orders'] == truth['completed_orders']


def test_token_is_refreshed_a_week_before_expiry(harness):
    _ready(harness)
    with Session(connections.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        old = conn.token_ciphertext
        conn.token_expires_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        db.commit()
    assert harness.post('/api/integrations/square/sync').status_code == 200
    with Session(connections.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        assert conn.token_ciphertext != old
        assert datetime.fromisoformat(conn.token_expires_at.replace('Z', '+00:00')) > datetime.now(timezone.utc) + timedelta(days=20)


def test_rejected_token_asks_owner_to_reconnect(harness):
    _ready(harness)
    harness.square.post('/__mock/faults', json={'status': 401, 'count': 1})
    assert harness.post('/api/integrations/square/sync').status_code == 422
    h = harness.get('/api/integrations/square/health').json()
    assert h['status'] == 'needs_reconnect' and 'Reconnect' in h['message']
    assert harness.post('/api/integrations/square/sync').status_code == 409
    harness.connect_oauth()  # reconnecting restores the connection
    assert harness.post('/api/integrations/square/sync').status_code == 200
    assert harness.get('/api/integrations/square/health').json()['status'] == 'healthy'


def _signed(body: dict, key='whkey', url='https://app.example.com/api/integrations/square/webhook'):
    raw = json.dumps(body).encode()
    sig = base64.b64encode(hmac.new(key.encode(), url.encode() + raw, hashlib.sha256).digest()).decode()
    return raw, {'x-square-hmacsha256-signature': sig, 'content-type': 'application/json'}


def test_revocation_webhook_stops_sync_and_deletes_token(harness, monkeypatch):
    _ready(harness)
    monkeypatch.setenv('SQUARE_WEBHOOK_SIGNATURE_KEY', 'whkey')
    monkeypatch.setenv('SQUARE_WEBHOOK_URL', 'https://app.example.com/api/integrations/square/webhook')
    event = {'type': 'oauth.authorization.revoked', 'merchant_id': 'MOCK_MERCHANT_1'}
    raw, headers = _signed(event, key='wrong')
    assert harness.api.post('/api/integrations/square/webhook', content=raw, headers=headers).status_code == 401
    raw, headers = _signed(event)
    assert harness.api.post('/api/integrations/square/webhook', content=raw, headers=headers).status_code == 200
    with Session(connections.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        assert conn.status == 'revoked' and conn.token_ciphertext is None and conn.refresh_ciphertext is None
    assert harness.get('/api/integrations/square/health').json()['status'] == 'revoked'
    assert harness.post('/api/integrations/square/sync').status_code == 409


def test_worker_schedules_an_incremental_sync_after_the_interval(harness, monkeypatch):
    _ready(harness)
    harness.post('/api/integrations/square/sync')
    with Session(connections.engine) as db:
        import time
        assert worker.schedule(db) == 0  # just synced
        assert worker.schedule(db, now=int(time.time()) + square_sync.sync_interval_seconds() + 60) == 1
        assert worker.schedule(db) == 0  # one open job per workspace


def test_health_reports_stale_data(harness):
    _ready(harness)
    harness.post('/api/integrations/square/sync')
    with Session(connections.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        conn.last_sync_at = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        db.commit()
    assert harness.get('/api/integrations/square/health').json()['status'] == 'stale'


def test_square_production_is_locked_until_go_live(monkeypatch):
    monkeypatch.setenv('SQUARE_ENVIRONMENT', 'production')
    monkeypatch.delenv('GUESTLIFT_ALLOW_SQUARE_PRODUCTION', raising=False)
    with pytest.raises(RuntimeError, match='locked'):
        connections.validate_square_config()
    monkeypatch.setenv('GUESTLIFT_ALLOW_SQUARE_PRODUCTION', '1')
    connections.validate_square_config()
    monkeypatch.delenv('SQUARE_API_BASE_URL', raising=False)
    assert connections._square_url() == 'https://connect.squareup.com'


def test_worker_process_starts_and_stops_cleanly(tmp_path):
    """The real `python -m app.worker` boots against a fresh database and exits on SIGTERM."""
    import os, signal, subprocess, sys, time
    env = {**os.environ, 'DATABASE_URL': f"sqlite:///{tmp_path / 'worker.db'}", 'GUESTLIFT_WORKER_IDLE_SECONDS': '0.2'}
    proc = subprocess.Popen([sys.executable, '-m', 'app.worker'], cwd=os.path.dirname(os.path.dirname(__file__)),
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(3)
    assert proc.poll() is None, proc.stdout.read()
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=15)
    assert proc.returncode == 0 and 'worker stopped' in out, out
