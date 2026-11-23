"""P1: never convert missing or stale Square data into confident restaurant recommendations."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import connections, insight_loop, saas, square_sync, weekly
from journey_support import harness  # noqa: F401


def synced(h):
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    response = h.post('/api/integrations/square/sync')
    assert response.status_code == 200, response.text
    return h


def expect_paused(h, phrase):
    brief = h.get('/api/briefs/latest').json()
    assert brief['data_status'] == 'incomplete'
    assert brief['findings'] == []
    assert brief['totals'] is None
    assert phrase in ' '.join(brief['caveats']).lower()
    assert 'nothing changed' not in brief['headline'].lower()


def test_partial_backfill_never_generates_false_sales_dip(harness):
    h = synced(harness)
    original = h.get('/api/briefs/latest').json()
    assert original['data_status'] == 'ready' and original['findings']
    with Session(saas.engine) as db:
        loc = db.scalar(select(square_sync.SquareLocationState).where(
            square_sync.SquareLocationState.location_id == 'LOC_MARKET'))
        loc.backfill_complete = False
        db.commit()
    expect_paused(h, 'importing')
    with Session(saas.engine) as db:
        loc = db.scalar(select(square_sync.SquareLocationState).where(
            square_sync.SquareLocationState.location_id == 'LOC_MARKET'))
        loc.backfill_complete = True
        db.commit()
    assert h.get('/api/briefs/latest').json()['data_status'] == 'ready'


def test_stale_success_timestamp_does_not_support_new_claims(harness):
    h = synced(harness)
    with Session(saas.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        conn.last_sync_at = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        db.commit()
    expect_paused(h, 'stale')


def test_checkpoint_must_include_all_local_days_of_report(harness):
    h = synced(harness)
    with Session(saas.engine) as db:
        loc = db.scalar(select(square_sync.SquareLocationState).where(
            square_sync.SquareLocationState.location_id == 'LOC_MARKET'))
        today = insight_loop.local_today('America/Los_Angeles')
        end_of_week = weekly.last_complete_week(today) + timedelta(days=7)
        loc.synced_through = (datetime.combine(end_of_week - timedelta(days=1),
                                                datetime.min.time(), tzinfo=timezone.utc)).isoformat()
        db.commit()
    expect_paused(h, 'complete reporting period')


def test_missing_baseline_does_not_become_an_artificial_decline(harness):
    h = synced(harness)
    with Session(saas.engine) as db:
        loc = db.scalar(select(square_sync.SquareLocationState).where(
            square_sync.SquareLocationState.location_id == 'LOC_MARKET'))
        loc.backfill_start = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        db.commit()
    expect_paused(h, 'comparison baseline')


def test_decision_outcome_is_deferred_and_can_recover_after_resync(harness):
    h = synced(harness)
    with Session(saas.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        old = conn.last_sync_at
        conn.last_sync_at = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        db.commit()
    start = (date.today() - timedelta(days=35)).isoformat()
    response = h.post('/api/decisions/plans', {
        'title': 'Test data trust gate', 'objective': 'returning_guests', 'offer_type': 'no_offer',
        'offer_value': 0, 'target_redemptions': 1, 'reference_basket_minor': 2500,
        'assumed_margin_percent': 35, 'metric': 'orders', 'location_id': 'LOC_HARBOR',
        'start_date': start, 'follow_up_weeks': 4})
    assert response.status_code == 201, response.text
    plan_id = response.json()['plan']['id']
    plan = next(p for p in h.get('/api/decisions/plans').json()['plans'] if p['id'] == plan_id)
    assert plan['outcome']['available'] is False and 'stale' in plan['outcome']['message'].lower()
    with Session(saas.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        conn.last_sync_at = old
        db.commit()
    plan = next(p for p in h.get('/api/decisions/plans').json()['plans'] if p['id'] == plan_id)
    assert plan['outcome']['available'] is True


def test_no_weekly_email_from_incomplete_window(harness):
    h = synced(harness)
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    scheduled = monday.replace(hour=16, minute=0, second=0, microsecond=0)
    with Session(saas.engine) as db:
        conn = db.scalar(select(connections.SquareConnection))
        conn.last_sync_at = scheduled.isoformat()
        for loc in db.scalars(select(square_sync.SquareLocationState)):
            loc.synced_through = scheduled.isoformat()
            loc.backfill_complete = True
            if loc.location_id == 'LOC_MARKET':
                loc.backfill_complete = False
        db.commit()
    with Session(saas.engine) as db:
        result = insight_loop.run_due(db, now=scheduled)
    assert result['queued']['weekly_digest'] == 0
