"""Schema lifecycle on PostgreSQL. Runs when TEST_POSTGRES_URL points at a server we may create
databases on (CI's migrations-postgres job; locally any throwaway postgres:16).

Regression tests for P0 (PR #29), each reproduced on the code before the fix:
- API and worker starting together on a fresh database: DeadlockDetected (the reported Docker failure)
- the real local compose database: "relation uq_square_sync_jobs_one_open already exists" (worker restart loop)
- M3 / pre-M2 databases started by M4 code: queries fail on columns create_all() never adds
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from db_lifecycle import (UPGRADE, assert_upgraded_with_data_intact, head_revision, load_schema, revision,
                          run_concurrently, run_upgrade, schema_gaps, seed_legacy_data)

ADMIN = os.getenv('TEST_POSTGRES_URL', '')
pytestmark = pytest.mark.skipif(not ADMIN, reason='set TEST_POSTGRES_URL to run PostgreSQL lifecycle tests')


@pytest.fixture
def pg_url():
    """A brand-new, empty database for one test (dropped afterwards; never a real one)."""
    name = 'lifecycle_' + uuid.uuid4().hex[:12]
    admin = create_engine(ADMIN, isolation_level='AUTOCOMMIT')
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE {name}'))
    yield make_url(ADMIN).set(database=name).render_as_string(hide_password=False)
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)'))
    admin.dispose()


def test_concurrent_startup_on_fresh_postgres(pg_url):
    """Docker started the API and worker together; both ran DDL and deadlocked."""
    results = run_concurrently(pg_url, [[sys.executable, '-c', UPGRADE]] * 6)
    failures = [out for code, out in results if code != 0]
    assert not failures, 'concurrent startup failed:\n' + '\n----\n'.join(f[-1500:] for f in failures)
    assert revision(pg_url) == head_revision() and schema_gaps(pg_url) == []


@pytest.mark.parametrize('legacy', ['mixed_local_compose', 'v013_pre_m2', 'm3'])
def test_legacy_database_upgrades_with_data_intact(pg_url, monkeypatch, legacy):
    """Older create_all() databases, including the real local compose one, reach head with their data."""
    load_schema(pg_url, legacy)
    seeded = seed_legacy_data(pg_url)
    r = run_upgrade(pg_url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert_upgraded_with_data_intact(pg_url, monkeypatch, seeded)


def test_alembic_managed_m3_database_upgrades_to_m4(pg_url, monkeypatch):
    import subprocess
    from db_lifecycle import BACKEND, _env
    r = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', '0005'], cwd=BACKEND, env=_env(pg_url),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    seeded = seed_legacy_data(pg_url)
    r = run_upgrade(pg_url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert_upgraded_with_data_intact(pg_url, monkeypatch, seeded)


def test_api_and_worker_start_once_concurrent_migrations_finish(pg_url, tmp_path):
    """Compose order, made harder: API and worker start first, then three migrate runs race each other."""
    import json
    import signal
    import subprocess
    import time
    import urllib.request
    from db_lifecycle import BACKEND, _env
    from test_service_startup import _port, _wait_http
    port = _port()
    api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--port', str(port)], cwd=BACKEND,
                           env=_env(pg_url, GUESTLIFT_ALLOWED_ORIGINS='http://localhost:3000'),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    worker = subprocess.Popen([sys.executable, '-m', 'app.worker'], cwd=BACKEND,
                              env=_env(pg_url, GUESTLIFT_WORKER_IDLE_SECONDS='0.2',
                                       GUESTLIFT_WORKER_HEARTBEAT_FILE=str(tmp_path / 'beat')),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(2)
        assert api.poll() is None and worker.poll() is None, 'services must wait for the schema, not fail'
        results = run_concurrently(pg_url, [[sys.executable, '-m', 'app.migrate']] * 3)
        assert all(code == 0 for code, _ in results), [out[-800:] for code, out in results if code]
        assert _wait_http(f'http://127.0.0.1:{port}/api/ready')[0] == 200
        deadline = time.monotonic() + 20
        while not (tmp_path / 'beat').exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        assert (tmp_path / 'beat').exists(), 'worker did not start'
        # Signing up and signing in works against the freshly migrated database.
        creds = json.dumps({'email': 'fresh@pg.test', 'password': 'a-long-startup-password'}).encode()
        for path, want in (('/api/local-auth/register', 201), ('/api/local-auth/login', 200)):
            req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=creds, method='POST',
                                         headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:3000'})
            with urllib.request.urlopen(req, timeout=10) as r:
                assert r.status == want
    finally:
        for p in (api, worker):
            p.send_signal(signal.SIGTERM)
        outs = [p.communicate(timeout=30)[0] for p in (api, worker)]
    assert worker.returncode == 0, outs[1][-2000:]
    assert 'Deadlock' not in outs[0] + outs[1] and 'already exists' not in outs[0] + outs[1]


def test_one_open_sync_job_is_enforced_after_upgrade(pg_url):
    assert run_upgrade(pg_url).returncode == 0
    eng = create_engine(pg_url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO saas_workspaces (id, owner_sub, name, restaurant_type, goal, subscription_plan, "
                       "subscription_status, created_at) VALUES ('w', 'u', 'W', 'cafe', 'g', 'sandbox', 'none', 'now')"))
        c.execute(text("INSERT INTO square_sync_jobs (id, workspace_id, kind, status, attempts, run_after, locked_until, "
                       "progress, last_error, created_at, updated_at) VALUES ('j1', 'w', 'manual', 'queued', 0, 0, 0, '{}', '', 'a', 'a')"))
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with eng.begin() as c:
            c.execute(text("INSERT INTO square_sync_jobs (id, workspace_id, kind, status, attempts, run_after, locked_until, "
                           "progress, last_error, created_at, updated_at) VALUES ('j2', 'w', 'manual', 'running', 0, 0, 0, '{}', '', 'b', 'b')"))
    with eng.begin() as c:  # a finished job doesn't count
        c.execute(text("INSERT INTO square_sync_jobs (id, workspace_id, kind, status, attempts, run_after, locked_until, "
                       "progress, last_error, created_at, updated_at) VALUES ('j3', 'w', 'manual', 'succeeded', 0, 0, 0, '{}', '', 'c', 'c')"))
    eng.dispose()
