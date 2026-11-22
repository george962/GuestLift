import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

BACKEND = Path(__file__).resolve().parents[1]


def _alembic(db_url, *args):
    env = {'DATABASE_URL': db_url, 'PATH': '/usr/bin:/bin:/usr/local/bin'}
    return subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True)


def test_upgrade_on_fresh_database_has_no_schema_drift(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    up = _alembic(url, 'upgrade', 'head')
    assert up.returncode == 0, up.stderr
    check = _alembic(url, 'check')
    assert check.returncode == 0, check.stdout + check.stderr
    tables = inspect(create_engine(url)).get_table_names()
    assert 'canonical_orders' in tables and 'alembic_version' in tables


def test_upgrade_adopts_legacy_database_and_adds_customer_id(tmp_path):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE canonical_orders (id INTEGER PRIMARY KEY)')
    up = _alembic(url, 'upgrade', 'head')
    assert up.returncode == 0, up.stderr
    cols = {c['name'] for c in inspect(create_engine(url)).get_columns('canonical_orders')}
    assert 'customer_id' in cols
