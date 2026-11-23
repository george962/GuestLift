"""Helpers for database lifecycle tests: legacy schemas, realistic legacy data, upgrades, checks.

Legacy schemas in fixtures/legacy_schemas/ were produced by older app versions' startup
create_all() (scripts/make-legacy-schema-fixtures.sh), plus a schema-only dump of a real local
compose database. The seed data mirrors what those versions stored, including a local account
whose password must still work after the upgrade.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import psycopg
from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / 'tests' / 'fixtures' / 'legacy_schemas'
PASSWORD = 'legacy-owner-password-1'
EMAIL = 'owner@legacy.test'
UPGRADE = 'import app.main; from app.database import init_db; init_db()'  # the app's own upgrade entry point


def engine_for(url: str) -> Engine:
    return create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {})


def load_schema(url: str, name: str) -> None:
    """Recreate a legacy schema exactly as an old version left it."""
    if url.startswith('sqlite'):
        path = make_url(url).database
        con = sqlite3.connect(path)
        con.executescript((FIXTURES / f'{name}.sqlite.sql').read_text())
        con.close()
        return
    sql = (FIXTURES / f'{name}.postgres.sql').read_text()
    plain = make_url(url).set(drivername='postgresql').render_as_string(hide_password=False)
    with psycopg.connect(plain, autocommit=True) as con:
        con.execute(sql)


def _env(url: str, **extra) -> dict:
    return {**os.environ, 'DATABASE_URL': url, 'PYTHONPATH': str(BACKEND), **extra}


def run_upgrade(url: str, timeout: float = 120) -> subprocess.CompletedProcess:
    """Prepare the database the way the application does (a separate process, like a deploy step)."""
    return subprocess.run([sys.executable, '-c', UPGRADE], cwd=BACKEND, env=_env(url), capture_output=True,
                          text=True, timeout=timeout)


def run_concurrently(url: str, commands: list[list[str]], timeout: float = 180) -> list[tuple[int, str]]:
    """Start every command at the same moment against one database; return (exit code, output) each."""
    procs = [subprocess.Popen(cmd, cwd=BACKEND, env=_env(url), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True) for cmd in commands]
    results = []
    for p in procs:
        out, _ = p.communicate(timeout=timeout)
        results.append((p.returncode, out))
    return results


def seed_legacy_data(url: str) -> dict:
    """Rows an older version would have stored. Columns the schema lacks are simply not written."""
    from app.local_auth import PASSWORD_HASHER
    eng = engine_for(url)
    meta = MetaData()
    meta.reflect(eng)
    now, later = int(time.time()), int(time.time()) + 86400
    ws, user = 'legacy-ws-1', 'legacy-user-1'
    rows = {
        'local_users': [dict(id=user, email=EMAIL, password_hash=PASSWORD_HASHER.hash(PASSWORD), created_at='2026-10-01T00:00:00+00:00')],
        'local_sessions': [dict(token_hash=hashlib.sha256(b'legacy-session').hexdigest(), user_id=user, csrf_token='legacy',
                                created_at=now, expires_at=later)],
        'saas_workspaces': [dict(id=ws, owner_sub=user, name='Legacy Bistro', restaurant_type='cafe', goal='customer_retention',
                                 subscription_plan='growth', subscription_status='active', stripe_customer_id='cus_legacy',
                                 stripe_subscription_id='sub_legacy', created_at='2026-10-01T00:00:00+00:00')],
        'tablesignal_onboarding_progress': [dict(workspace_id=ws, stage=3, plan_choice='growth', updated_at='2026-10-01T00:00:00+00:00')],
        'square_sandbox_connections': [dict(id='legacy-conn-1', workspace_id=ws, merchant_id='LEGACY_MERCHANT', credential_mode='developer_env',
                                            token_ciphertext=None, refresh_ciphertext=None, token_expires_at=None,
                                            connected_at='2026-10-02T00:00:00+00:00', last_sync_at='2026-11-20T00:00:00+00:00', last_error=None)],
        'sandbox_monitored_locations': [dict(workspace_id=ws, location_id='LOC_A', merchant_id='LEGACY_MERCHANT', name='Main St',
                                             selected_at='2026-10-02T00:00:00+00:00')],
        'square_sandbox_orders': [dict(id=f'legacy-order-{i}', workspace_id=ws, source_order_id=f'ORD-{i}', location_id='LOC_A',
                                       created_at=f'2026-11-0{i}T18:00:00Z', updated_at=f'2026-11-0{i}T18:05:00Z', status='COMPLETED',
                                       customer_id='CUST_1', net_sales_minor=1500, discount_minor=0, tax_minor=100, tip_minor=0,
                                       currency='USD', local_date=f'2026-11-0{i}')  # M3+ sync code always wrote local_date
                                  for i in (1, 2, 3)],
        'tablesignal_decision_plans': [dict(id='legacy-plan-1', workspace_id=ws, title='Legacy plan', objective='returning_guests',
                                            offer_type='percent', offer_value=10, target_redemptions=10, reference_basket_minor=2500,
                                            assumed_margin_percent=35, discount_budget_minor=2500, modeled_contribution_minor=6250,
                                            status='draft', notes='', created_at='2026-10-03T00:00:00+00:00',
                                            updated_at='2026-10-03T00:00:00+00:00')],
        'canonical_orders': [dict(provider='square', source_order_id=f'DEMO-{i}', location_id='L1', created_at='2026-10-01T12:00:00Z',
                                  customer_id=None, net_sales_minor=1000, discount_minor=0, refund_minor=0, payload_json='{}')
                             for i in (1, 2)],
        'saas_billing_events': [dict(stripe_event_id='evt_legacy', processed_at='2026-10-04T00:00:00+00:00')],
        'workspace_members': [],  # older versions had none; the upgrade must give the owner a row
        # Two open sync jobs for one workspace: what the old enqueue race could leave behind.
        'square_sync_jobs': [dict(id=f'legacy-job-{i}', workspace_id=ws, kind='scheduled', status='queued', attempts=0, run_after=now,
                                  locked_until=0, progress='{}', last_error='', created_at=f'2026-11-2{i}T00:00:00+00:00',
                                  updated_at=f'2026-11-2{i}T00:00:00+00:00') for i in (1, 2)],
    }
    inserted = {}
    with eng.connect() as conn:
        for table, items in rows.items():
            if table not in meta.tables:
                continue
            cols = set(meta.tables[table].c.keys())
            count = 0
            for item in items:
                try:
                    with conn.begin():
                        conn.execute(meta.tables[table].insert().values({k: v for k, v in item.items() if k in cols}))
                    count += 1
                except Exception:  # e.g. a schema that already enforces one open job per workspace
                    pass
            inserted[table] = count
    eng.dispose()
    return inserted


@contextmanager
def app_using(url: str, monkeypatch):
    """The real API, with every module pointed at this database."""
    from fastapi.testclient import TestClient
    import app.database as database
    eng = engine_for(url)
    for name, mod in list(sys.modules.items()):
        if (name == 'app' or name.startswith('app.')) and isinstance(getattr(mod, 'engine', None), Engine):
            monkeypatch.setattr(mod, 'engine', eng)
    monkeypatch.setattr(database, 'engine', eng)
    from app.main import app
    try:
        yield TestClient(app)
    finally:
        eng.dispose()


def schema_gaps(url: str) -> list[str]:
    """Tables and columns the current models need that the database lacks."""
    import app.main  # noqa: F401  (registers every model)
    from app.database import Base
    eng = engine_for(url)
    insp = inspect(eng)
    tables = set(insp.get_table_names())
    gaps = []
    for table in Base.metadata.sorted_tables:
        if table.name not in tables:
            gaps.append(f'missing table {table.name}')
            continue
        have = {c['name'] for c in insp.get_columns(table.name)}
        gaps += [f'missing column {table.name}.{c.name}' for c in table.columns if c.name not in have]
    eng.dispose()
    return gaps


def missing_constraints(url: str) -> list[str]:
    """Indexes, constraints, tables or columns the models define that the database lacks (per Alembic)."""
    import app.main  # noqa: F401
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext
    from app.database import Base
    eng = engine_for(url)
    try:
        with eng.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        eng.dispose()
    flat = [d for group in diffs for d in (group if isinstance(group, list) else [group])]
    return [f'{d[0]} {getattr(d[1], "name", d[1:])}' for d in flat if isinstance(d, tuple) and str(d[0]).startswith('add_')]


def assert_one_open_job_index(url: str) -> None:
    """The index exists with the right definition and really allows one open job per workspace."""
    from sqlalchemy.exc import IntegrityError
    eng = engine_for(url)
    sql = ("SELECT sql FROM sqlite_master WHERE name = 'uq_square_sync_jobs_one_open'" if url.startswith('sqlite')
           else "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_square_sync_jobs_one_open'")
    job = ("INSERT INTO square_sync_jobs (id, workspace_id, kind, status, attempts, run_after, locked_until, progress, "
           "last_error, created_at, updated_at) VALUES (:id, 'legacy-ws-1', 'manual', :status, 0, 0, 0, '{}', '', 'x', 'x')")
    try:
        with eng.connect() as c:
            definition = (c.execute(text(sql)).scalar() or '').replace('"', '')
            assert 'UNIQUE' in definition.upper() and 'workspace_id' in definition, definition
            assert 'WHERE' in definition.upper() and 'queued' in definition and 'running' in definition, definition
            c.rollback()  # end the read's implicit transaction
            tx = c.begin()  # probe behaviour, then roll back: no data changes
            open_now = c.execute(text("SELECT count(*) FROM square_sync_jobs WHERE workspace_id = 'legacy-ws-1' "
                                      "AND status IN ('queued', 'running')")).scalar()
            if not open_now:
                c.execute(text(job), {'id': 'probe-open-1', 'status': 'queued'})
            c.execute(text(job), {'id': 'probe-done', 'status': 'succeeded'})  # finished jobs don't count
            nested = c.begin_nested()
            try:
                c.execute(text(job), {'id': 'probe-open-2', 'status': 'running'})
                raise AssertionError('a second open sync job for one workspace was accepted')
            except IntegrityError:
                nested.rollback()
            tx.rollback()
    finally:
        eng.dispose()


def revision(url: str) -> str | None:
    eng = engine_for(url)
    try:
        with eng.connect() as c:
            if 'alembic_version' not in inspect(c).get_table_names():
                return None
            return c.execute(text('SELECT version_num FROM alembic_version')).scalar()
    finally:
        eng.dispose()


def head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config(str(BACKEND / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND / 'alembic'))
    return ScriptDirectory.from_config(cfg).get_current_head()


def count(url: str, sql: str) -> int:
    eng = engine_for(url)
    try:
        with eng.connect() as c:
            return c.execute(text(sql)).scalar()
    finally:
        eng.dispose()


def assert_upgraded_with_data_intact(url: str, monkeypatch, seeded: dict) -> None:
    """The upgraded database serves the old data through the real API, and nothing is missing."""
    ORIGIN = {'Origin': 'http://localhost:3000'}
    with app_using(url, monkeypatch) as client:
        login = client.post('/api/local-auth/login', json={'email': EMAIL, 'password': PASSWORD}, headers=ORIGIN)
        assert login.status_code == 200, f'existing account could not sign in after upgrade: {login.text}'
        me = client.get('/api/saas/me')
        assert me.status_code == 200, f'/api/saas/me failed after upgrade: {me.text}'
        body = me.json()
        assert body['workspace']['name'] == 'Legacy Bistro', 'the owner landed in a new, empty workspace'
        assert body['summary']['orders'] == seeded['square_sandbox_orders']
        plans = client.get('/api/decisions/plans')
        assert plans.status_code == 200, plans.text
        assert [p['title'] for p in plans.json()['plans']] == ['Legacy plan']
        status = client.get('/api/integrations/square/status').json()
        assert status['connected'] is True and status['merchant_id'] == 'LEGACY_MERCHANT'
    assert count(url, 'SELECT count(*) FROM local_users') == 1
    assert count(url, "SELECT count(*) FROM saas_workspaces WHERE stripe_subscription_id = 'sub_legacy' AND subscription_status = 'active'") == 1
    assert count(url, 'SELECT count(*) FROM saas_billing_events') == 1
    assert count(url, "SELECT count(*) FROM canonical_orders WHERE workspace_id = 'public-demo'") == seeded['canonical_orders']
    assert count(url, "SELECT count(*) FROM square_sandbox_orders WHERE local_date IS NOT NULL") == seeded['square_sandbox_orders']
    assert count(url, "SELECT count(*) FROM workspace_members WHERE subject = 'legacy-user-1' AND role = 'owner' "
                      "AND workspace_id = 'legacy-ws-1'") == 1
    assert count(url, "SELECT count(*) FROM square_sync_jobs WHERE status IN ('queued', 'running')") <= 1
    assert schema_gaps(url) == []
    assert missing_constraints(url) == []
    assert_one_open_job_index(url)
    assert revision(url) == head_revision()


def new_sqlite_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / ('db-' + uuid.uuid4().hex[:8] + '.sqlite')}"
