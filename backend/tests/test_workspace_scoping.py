"""Workspace isolation for the demo tables, plus a guardrail for future tables."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app import database
from app.adapters import parse
from app.campaigns import import_campaign_csvs
from app.database import (
    DEMO_WORKSPACE_ID, Base, CampaignRecord, OrderRecord, WORKSPACE_SCOPED_TABLES,
    campaign_reports, customer_summary, metrics, persist, recent_runs, reset_db,
)
from app.main import app

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'campaigns'
A, B = 'workspace-a', 'workspace-b'


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    eng = create_engine(f"sqlite:///{tmp_path / 'scope.sqlite'}", connect_args={'check_same_thread': False})
    monkeypatch.setattr(database, 'engine', eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _campaign_files():
    return (FIXTURES / 'Campaigns.csv').read_bytes(), (FIXTURES / 'Redemptions.csv').read_bytes()


def test_same_orders_can_exist_in_two_workspaces(engine):
    orders = parse('toast')
    assert persist(orders, A)[:2] == (28, 0)
    # Previously these were "duplicates" because uniqueness was global.
    assert persist(orders, B)[:2] == (28, 0)
    assert persist(orders, A)[:2] == (0, 28)  # replay inside one workspace is still idempotent


def test_metrics_runs_and_summary_do_not_leak(engine):
    persist(parse('toast'), A)
    assert metrics(workspace_id=A)['order_count'] == 28
    assert metrics(workspace_id=B)['order_count'] == 0
    assert metrics()['order_count'] == 0  # default is the demo workspace, not "everything"
    assert len(recent_runs(A)) == 1 and recent_runs(B) == []
    assert customer_summary(workspace_id=B)['total_orders'] == 0


def test_reset_only_clears_one_workspace(engine):
    persist(parse('toast'), A)
    persist(parse('square'), B)
    reset_db(A)
    assert metrics(workspace_id=A)['order_count'] == 0
    assert metrics(workspace_id=B)['order_count'] == 28


def test_campaigns_and_redemptions_are_workspace_scoped(engine):
    campaigns, redemptions = _campaign_files()
    persist(parse('toast'), A)
    persist(parse('toast'), B)
    persist(parse('square'), A)
    persist(parse('square'), B)
    first = import_campaign_csvs(campaigns, redemptions, A)
    assert first['campaigns_inserted'] == 2 and first['redemptions_inserted'] == 21 and first['rejected'] == 0
    # B sees nothing of A's campaigns or redemptions.
    assert campaign_reports(workspace_id=B)['campaigns'] == []
    assert campaign_reports(workspace_id=B)['total_redemptions'] == 0
    # The same campaign and redemption ids are valid in B: no cross-workspace collision.
    second = import_campaign_csvs(campaigns, redemptions, B)
    assert second['campaigns_inserted'] == 2 and second['redemptions_inserted'] == 21 and second['rejected'] == 0
    assert campaign_reports(workspace_id=A)['total_redemptions'] == 21
    with Session(engine) as db:
        rows = db.scalars(select(CampaignRecord)).all()
        assert {r.workspace_id for r in rows} == {A, B}


def test_redemption_cannot_reference_another_workspaces_order(engine):
    campaigns, redemptions = _campaign_files()
    persist(parse('toast'), A)
    persist(parse('square'), A)
    # B has no orders, so every redemption must be rejected rather than borrow A's orders.
    result = import_campaign_csvs(campaigns, redemptions, B)
    assert result['redemptions_inserted'] == 0
    assert any('import POS orders first' in issue for issue in result['issues'])


def test_demo_api_uses_only_the_public_demo_workspace(engine):
    with TestClient(app) as client:
        assert client.post('/api/import/toast').json()['inserted'] == 28
        client.post('/api/campaigns/demo/load')
    with Session(engine) as db:
        assert {o.workspace_id for o in db.scalars(select(OrderRecord)).all()} == {DEMO_WORKSPACE_ID}
        assert {c.workspace_id for c in db.scalars(select(CampaignRecord)).all()} == {DEMO_WORKSPACE_ID}
    assert metrics(workspace_id=A)['order_count'] == 0


def test_init_db_upgrades_a_pre_scoping_database(tmp_path, monkeypatch):
    """A local DB created before workspace_id existed keeps its data and gains the column."""
    eng = create_engine(f"sqlite:///{tmp_path / 'old.sqlite'}", connect_args={'check_same_thread': False})
    with eng.begin() as c:
        c.exec_driver_sql(
            'CREATE TABLE campaigns (campaign_id VARCHAR(80) PRIMARY KEY, code VARCHAR(80) NOT NULL, '
            'name VARCHAR(160) NOT NULL, offer_type VARCHAR(30) NOT NULL, start_date VARCHAR(10) NOT NULL, '
            'end_date VARCHAR(10) NOT NULL, variable_cost_minor INTEGER NOT NULL, '
            'fixed_cost_minor INTEGER NOT NULL, description TEXT NOT NULL)')
        c.exec_driver_sql("INSERT INTO campaigns VALUES ('c1','C','n','pct','2026-01-01','2026-02-01',0,0,'')")
    monkeypatch.setattr(database, 'engine', eng)
    database.init_db()
    with eng.connect() as c:
        assert c.execute(text('SELECT workspace_id, campaign_id FROM campaigns')).all() == [(DEMO_WORKSPACE_ID, 'c1')]
    for table in WORKSPACE_SCOPED_TABLES:
        assert 'workspace_id' in {col['name'] for col in inspect(eng).get_columns(table)}
    eng.dispose()


# Tables that are intentionally not owned by a single workspace. Anything new must
# either carry workspace_id or be added here with a reason in code review.
NOT_WORKSPACE_OWNED = {
    'saas_workspaces': 'the workspace itself',
    'local_users': 'identity, one row per login',
    'local_sessions': 'identity, keyed by user',
    'saas_billing_events': 'global Stripe event-id idempotency log',
}


def test_every_table_is_workspace_scoped_or_explicitly_exempt():
    import app.main  # noqa: F401  (registers every model)
    unscoped = {name for name, table in Base.metadata.tables.items() if 'workspace_id' not in table.c}
    assert unscoped <= set(NOT_WORKSPACE_OWNED), (
        f'Tables without workspace_id: {sorted(unscoped - set(NOT_WORKSPACE_OWNED))}. '
        'Scope them by workspace or add them to NOT_WORKSPACE_OWNED with a reason.')
