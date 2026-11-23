"""Service startup contract (P0): only `python -m app.migrate` changes the schema; the API and worker
wait until it is current, then start. Real processes, real ports."""
from __future__ import annotations

import os
import re
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from db_lifecycle import BACKEND, _env, head_revision, new_sqlite_url, revision, run_concurrently


def _port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _tables(url: str) -> set[str]:
    path = url.removeprefix('sqlite:///')
    if not os.path.exists(path):
        return set()
    with sqlite3.connect(path) as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _migrate(url: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, '-m', 'app.migrate', *args], cwd=BACKEND, env=_env(url),
                          capture_output=True, text=True, timeout=120)


def _api(url: str, port: int, **env) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--port', str(port)], cwd=BACKEND,
                            env=_env(url, **env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _worker(url: str, tmp_path: Path, **env) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, '-m', 'app.worker'], cwd=BACKEND,
                            env=_env(url, GUESTLIFT_WORKER_IDLE_SECONDS='0.2',
                                     GUESTLIFT_WORKER_HEARTBEAT_FILE=str(tmp_path / 'beat'), **env),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _wait_http(url: str, want: int = 200, timeout: float = 30) -> tuple[int, str]:
    deadline, last = time.monotonic() + timeout, (0, '')
    while time.monotonic() < deadline:
        try:
            last = _get(url)
            if last[0] == want:
                return last
        except OSError:
            pass
        time.sleep(0.3)
    return last


def test_application_code_never_changes_the_schema():
    """Only app/migrate.py may run migrations; nothing in the services creates tables or indexes."""
    # Calls and SQL statements, not prose: uppercase SQL keywords, method calls on metadata/engines.
    forbidden = re.compile(r'\.(create_all|drop_all)\(|event\.listen\(|ensure_indexes\(|'
                           r'\b(CREATE (UNIQUE )?(TABLE|INDEX)|ALTER TABLE|DROP (TABLE|INDEX))\b')
    offenders = []
    for path in sorted((BACKEND / 'app').glob('*.py')):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if forbidden.search(line) and not line.lstrip().startswith('#'):
                offenders.append(f'{path.name}:{n}: {line.strip()}')
    assert not offenders, 'schema changes outside Alembic:\n' + '\n'.join(offenders)
    users = [p.name for p in (BACKEND / 'app').glob('*.py') if 'command.upgrade' in p.read_text()]
    assert users == ['migrate.py']


def test_api_refuses_to_start_on_an_unmigrated_database_and_creates_nothing(tmp_path):
    url = new_sqlite_url(tmp_path)
    proc = _api(url, _port(), GUESTLIFT_SCHEMA_WAIT_SECONDS='2')
    out, _ = proc.communicate(timeout=60)
    assert proc.returncode != 0
    assert 'python -m app.migrate' in out and 'has not been migrated' in out, out[-2000:]
    assert _tables(url) == set()  # the API made no schema changes


def test_api_starts_after_migrate_and_ready_tracks_the_schema(tmp_path):
    url, port = new_sqlite_url(tmp_path), _port()
    assert _migrate(url).returncode == 0
    proc = _api(url, port)
    try:
        assert _wait_http(f'http://127.0.0.1:{port}/api/ready')[0] == 200
        with sqlite3.connect(url.removeprefix('sqlite:///')) as c:  # pretend a newer migration hasn't run yet
            c.execute("UPDATE alembic_version SET version_num = '0007'")
        code, body = _get(f'http://127.0.0.1:{port}/api/ready')
        assert code == 503 and '0007' in body and head_revision() in body
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=30)


def test_worker_waits_for_the_schema_then_starts(tmp_path):
    url = new_sqlite_url(tmp_path)
    proc = _worker(url, tmp_path, GUESTLIFT_SCHEMA_WAIT_SECONDS='60')
    try:
        time.sleep(3)
        assert proc.poll() is None, 'the worker exited instead of waiting for the schema'
        assert _tables(url) == set()  # waiting, not creating
        assert not (tmp_path / 'beat').exists()  # not healthy until it actually runs
        assert _migrate(url).returncode == 0
        deadline = time.monotonic() + 20
        while not (tmp_path / 'beat').exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        assert (tmp_path / 'beat').exists(), 'the worker did not start after migration'
    finally:
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=30)
    assert proc.returncode == 0, out
    assert 'waiting for the database schema' in out and 'worker started' in out and 'worker stopped' in out


def test_worker_stops_cleanly_while_waiting(tmp_path):
    proc = _worker(new_sqlite_url(tmp_path), tmp_path, GUESTLIFT_SCHEMA_WAIT_SECONDS='60')
    time.sleep(2)
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=30)
    assert proc.returncode == 0 and 'worker stopped' in out and 'worker started' not in out, out


def test_worker_gives_up_with_a_clear_error(tmp_path):
    proc = _worker(new_sqlite_url(tmp_path), tmp_path, GUESTLIFT_SCHEMA_WAIT_SECONDS='1')
    out, _ = proc.communicate(timeout=60)
    assert proc.returncode == 3 and 'python -m app.migrate' in out, out


def test_migrate_cli_upgrades_once_then_reports_current(tmp_path):
    url = new_sqlite_url(tmp_path)
    assert _migrate(url, '--check').returncode == 1
    first = _migrate(url)
    assert first.returncode == 0 and f'empty -> {head_revision()}' in first.stdout, first.stdout + first.stderr
    again = _migrate(url)
    assert again.returncode == 0 and 'already current' in again.stdout
    assert _migrate(url, '--check').returncode == 0


def test_concurrent_migrate_processes_on_one_sqlite_file(tmp_path):
    url = new_sqlite_url(tmp_path)
    results = run_concurrently(url, [[sys.executable, '-m', 'app.migrate']] * 5)
    assert all(code == 0 for code, _ in results), [out[-800:] for code, out in results if code]
    assert sum('empty ->' in out for _, out in results) == 1  # one did the work; the rest found it done
    assert revision(url) == head_revision()
