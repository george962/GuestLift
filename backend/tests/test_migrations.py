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


def _seed_pre_scoping(url):
    """Build the schema as it was at revision 0001 and add one row per demo table."""
    assert _alembic(url, 'upgrade', '0001').returncode == 0
    engine = create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql("INSERT INTO canonical_orders (provider, source_order_id, location_id, created_at, "
                          "net_sales_minor, discount_minor, refund_minor, payload_json) "
                          "VALUES ('toast','o1','L1','2026-01-01',100,10,0,'{}')")
        c.exec_driver_sql("INSERT INTO campaigns VALUES ('c1','CODE','Camp','pct','2026-01-01','2026-02-01',5,50,'')")
        c.exec_driver_sql("INSERT INTO campaign_redemptions (redemption_id, campaign_id, provider, source_order_id, "
                          "redeemed_at, discount_minor) VALUES ('r1','c1','toast','o1','2026-01-02',10)")
        c.exec_driver_sql("INSERT INTO import_runs (provider, processed_at, inserted, duplicates, status) "
                          "VALUES ('toast','x',1,0,'completed')")
    return engine


def test_scoping_migration_backfills_existing_rows_into_the_demo_workspace(tmp_path):
    url = f"sqlite:///{tmp_path / 'scope.db'}"
    engine = _seed_pre_scoping(url)
    assert _alembic(url, 'upgrade', 'head').returncode == 0
    with engine.connect() as c:
        for table in ('canonical_orders', 'campaigns', 'campaign_redemptions', 'import_runs'):
            rows = c.exec_driver_sql(f'SELECT DISTINCT workspace_id FROM {table}').fetchall()
            assert rows == [('public-demo',)], table
    assert _alembic(url, 'check').returncode == 0


def test_scoping_migration_makes_uniqueness_per_workspace(tmp_path):
    url = f"sqlite:///{tmp_path / 'unique.db'}"
    engine = _seed_pre_scoping(url)
    assert _alembic(url, 'upgrade', 'head').returncode == 0
    order = ("INSERT INTO canonical_orders (workspace_id, provider, source_order_id, location_id, created_at, "
             "net_sales_minor, discount_minor, refund_minor, payload_json) "
             "VALUES (?,'toast','o1','L1','x',1,0,0,'{}')")
    with engine.begin() as c:
        c.exec_driver_sql(order, ('ws-b',))  # same provider+order id in another workspace: allowed
        c.exec_driver_sql("INSERT INTO campaigns (workspace_id, campaign_id, code, name, offer_type, start_date, "
                          "end_date, variable_cost_minor, fixed_cost_minor, description) "
                          "VALUES ('ws-b','c1','CODE','Camp','pct','a','b',0,0,'')")
    with pytest.raises(Exception, match='UNIQUE'):
        with engine.begin() as c:
            c.exec_driver_sql(order, ('ws-b',))  # same workspace: still rejected


def test_scoping_migration_downgrade_round_trip(tmp_path):
    url = f"sqlite:///{tmp_path / 'down.db'}"
    engine = _seed_pre_scoping(url)
    assert _alembic(url, 'upgrade', 'head').returncode == 0
    with engine.begin() as c:
        c.exec_driver_sql("INSERT INTO import_runs (workspace_id, provider, processed_at, inserted, duplicates, status) "
                          "VALUES ('ws-b','toast','x',1,0,'completed')")
    down = _alembic(url, 'downgrade', '0001')
    assert down.returncode == 0, down.stderr
    with engine.connect() as c:
        # Non-demo rows are removed on downgrade; demo rows survive.
        assert c.exec_driver_sql('SELECT COUNT(*) FROM import_runs').scalar() == 1
        assert c.exec_driver_sql('SELECT campaign_id FROM campaigns').fetchall() == [('c1',)]
    assert 'workspace_id' not in {col['name'] for col in inspect(engine).get_columns('canonical_orders')}
    assert _alembic(url, 'upgrade', 'head').returncode == 0
    assert _alembic(url, 'check').returncode == 0


def test_v013_sandbox_location_migration_round_trip(tmp_path):
    """The monitored-location table must survive normal release upgrades."""
    url = f"sqlite:///{tmp_path / 'v013_locations.db'}"

    before = _alembic(url, 'upgrade', '0002')
    assert before.returncode == 0, before.stderr

    engine = create_engine(url)
    assert 'sandbox_monitored_locations' not in (
        inspect(engine).get_table_names()
    )

    upgraded = _alembic(url, 'upgrade', 'head')
    assert upgraded.returncode == 0, upgraded.stderr

    columns = {
        column['name']
        for column in inspect(engine).get_columns(
            'sandbox_monitored_locations'
        )
    }
    assert columns == {
        'workspace_id',
        'location_id',
        'merchant_id',
        'name',
        'selected_at',
    }

    assert _alembic(url, 'check').returncode == 0

    downgraded = _alembic(url, 'downgrade', '0002')
    assert downgraded.returncode == 0, downgraded.stderr

    assert 'sandbox_monitored_locations' not in (
        inspect(engine).get_table_names()
    )

    upgraded_again = _alembic(url, 'upgrade', 'head')
    assert upgraded_again.returncode == 0, upgraded_again.stderr

    engine.dispose()
