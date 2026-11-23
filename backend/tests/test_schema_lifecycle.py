"""Schema lifecycle on SQLite: fresh, concurrent, legacy create_all() databases, and M3 -> M4.

Regression tests for P0 (PR #29): each reproduced a real failure before the fix.
- concurrent startup on one SQLite file: "table campaigns already exists" (journey CI)
- a create_all() database upgraded by Alembic: "index uq_square_sync_jobs_one_open already exists"
- an M3 database started by M4 code: queries fail on columns create_all() never adds
"""
from __future__ import annotations

import sys

import pytest

from db_lifecycle import (UPGRADE, assert_upgraded_with_data_intact, count, head_revision, load_schema,
                          new_sqlite_url, revision, run_concurrently, run_upgrade, schema_gaps, seed_legacy_data)


def test_fresh_database_reaches_head(tmp_path):
    url = new_sqlite_url(tmp_path)
    r = run_upgrade(url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert revision(url) == head_revision() and schema_gaps(url) == []


def test_concurrent_startup_on_one_sqlite_file(tmp_path):
    """The journey started the API and worker together on one file; both created tables."""
    url = new_sqlite_url(tmp_path)
    results = run_concurrently(url, [[sys.executable, '-c', UPGRADE]] * 4)
    failures = [out for code, out in results if code != 0]
    assert not failures, 'concurrent startup failed:\n' + '\n----\n'.join(f[-1500:] for f in failures)
    assert revision(url) == head_revision() and schema_gaps(url) == []


def test_upgrade_of_a_create_all_database_keeps_one_open_job_index(tmp_path):
    """create_all() made the index, then Alembic 0008 tried to create it again."""
    import app.main  # noqa: F401
    from app.database import Base
    from db_lifecycle import engine_for
    url = new_sqlite_url(tmp_path)
    eng = engine_for(url)
    Base.metadata.create_all(eng)
    eng.dispose()
    r = run_upgrade(url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert revision(url) == head_revision()
    assert count(url, "SELECT count(*) FROM sqlite_master WHERE type = 'index' AND name = 'uq_square_sync_jobs_one_open'") == 1


@pytest.mark.parametrize('legacy', ['v013_pre_m2', 'm3'])
def test_legacy_create_all_database_upgrades_with_data_intact(tmp_path, monkeypatch, legacy):
    """Databases made by older versions' startup create_all(), with their data, reach head."""
    url = new_sqlite_url(tmp_path)
    load_schema(url, legacy)
    seeded = seed_legacy_data(url)
    r = run_upgrade(url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert_upgraded_with_data_intact(url, monkeypatch, seeded)


def test_alembic_managed_m3_database_upgrades_to_m4(tmp_path, monkeypatch):
    """A database Alembic left at M3 (0005) gains the M5 and M4 columns and keeps its data."""
    import subprocess
    from db_lifecycle import BACKEND, _env
    url = new_sqlite_url(tmp_path)
    r = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', '0005'], cwd=BACKEND, env=_env(url),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    seeded = seed_legacy_data(url)
    r = run_upgrade(url)
    assert r.returncode == 0, r.stdout + r.stderr
    assert_upgraded_with_data_intact(url, monkeypatch, seeded)


def test_every_migration_can_replay_on_a_current_database(tmp_path, monkeypatch):
    """Adoption runs all migrations over existing objects, so each one must be idempotent.
    A future migration that isn't fails here instead of on someone's database."""
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext
    from app import migrate
    from db_lifecycle import engine_for
    url = new_sqlite_url(tmp_path)
    load_schema(url, 'm3')
    seeded = seed_legacy_data(url)
    assert run_upgrade(url).returncode == 0
    eng = engine_for(url)
    # Run every revision's upgrade() again over the finished schema, oldest first. alembic_version
    # isn't touched: this only proves each migration is safe to run on objects that already exist.
    revisions = list(reversed(list(migrate._script().walk_revisions('base', 'heads'))))
    with eng.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            for rev in revisions:
                rev.module.upgrade()
    eng.dispose()
    assert_upgraded_with_data_intact(url, monkeypatch, seeded)


def test_repeated_upgrade_changes_nothing(tmp_path):
    url = new_sqlite_url(tmp_path)
    assert run_upgrade(url).returncode == 0
    from db_lifecycle import engine_for
    from sqlalchemy import inspect
    eng = engine_for(url)
    before = {t: sorted(c['name'] for c in inspect(eng).get_columns(t)) for t in inspect(eng).get_table_names()}
    eng.dispose()
    r = run_upgrade(url)
    assert r.returncode == 0, r.stdout + r.stderr
    eng = engine_for(url)
    after = {t: sorted(c['name'] for c in inspect(eng).get_columns(t)) for t in inspect(eng).get_table_names()}
    eng.dispose()
    assert before == after and revision(url) == head_revision()
