"""M4: weekly brief, decision outcomes, email digests and unsubscribe."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import decisions, emailer, insight_loop, saas, weekly
from journey_support import harness  # noqa: F401


def _synced(h):
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    assert h.post('/api/integrations/square/sync').status_code == 200
    return h.truth()


def _flat_series(days=120, seed=3, effect=None):
    rng, rows, today = random.Random(seed), [], date(2026, 11, 22)
    for d in range(days):
        day = today - timedelta(days=d)
        n = rng.randint(20, 24) + (effect(day) if effect else 0)
        rows += [{'location_id': 'L1', 'local_date': day.isoformat(), 'net_sales_minor': 2000, 'discount_minor': 0,
                  'customer_id': f'c{i % 40}'} for i in range(n)]
    return rows, today


def test_brief_finds_the_planted_dip_and_says_why(harness):
    truth = _synced(harness)
    brief = harness.get('/api/briefs/latest').json()
    assert brief['week_start'] == truth['planted']['market_weekday_dip_week']
    market = [f for f in brief['findings'] if f['location_id'] == 'LOC_MARKET' and f['metric'] in ('orders', 'net_sales')]
    assert market, brief['findings']
    top = market[0]
    assert top['evidence']['change_percent'] < -15 and top['confidence'] in ('clear', 'possible')
    for key in ('this_week', 'baseline', 'weekly_spread', 'orders_this_week', 'baseline_from'):
        assert key in top['evidence']
    assert 'cause' in brief['method'].lower() or 'not causes' in brief['method'].lower()


def test_brief_stays_quiet_when_nothing_unusual_happened():
    rows, today = _flat_series()
    brief = weekly.build_brief(rows, [], {'L1': 'Only store'}, today)
    assert not [f for f in brief['findings'] if f['confidence'] == 'clear']
    if not brief['findings']:
        assert brief['headline'] == 'Nothing changed more than usual last week.'


def test_outcome_readout_finds_the_planted_lift(harness):
    _synced(harness)
    start = (date.today() - timedelta(days=35)).isoformat()
    plan = harness.post('/api/decisions/plans', {
        'title': 'Open brunch an hour earlier', 'objective': 'returning_guests', 'offer_type': 'no_offer', 'offer_value': 0,
        'target_redemptions': 1, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35,
        'metric': 'orders', 'location_id': 'LOC_HARBOR', 'start_date': start, 'follow_up_weeks': 4})
    assert plan.status_code == 201, plan.text
    readout = next(p for p in harness.get('/api/decisions/plans').json()['plans'] if p['title'].startswith('Open brunch'))['outcome']
    assert readout['available'] and readout['change_percent'] > 10, readout
    assert readout['verdict'] in ('clear', 'possible')
    assert 'not proof' in readout['explanation'] and 'last year' in readout['explanation']


def test_outcome_waits_for_the_follow_up_date(harness):
    _synced(harness)
    r = harness.post('/api/decisions/plans', {
        'title': 'Try a lunch combo', 'objective': 'discount_review', 'offer_type': 'percent', 'offer_value': 10,
        'target_redemptions': 20, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35, 'follow_up_weeks': 4})
    out = r.json()['plan']
    plan = next(p for p in harness.get('/api/decisions/plans').json()['plans'] if p['id'] == out['id'])
    assert plan['outcome']['available'] is False and plan['outcome']['due'] == plan['follow_up_date']


def test_no_effect_decision_is_reported_as_no_clear_change():
    rows, today = _flat_series()
    r = weekly.outcome(rows, [], 'orders', None, today - timedelta(days=56), today - timedelta(days=28), None)
    assert r['available'] and r['verdict'] in ('no_clear_change', 'possible'), r


def test_seasonal_movement_is_separated_out():
    # The same +30% lift happens every year in this window: it's seasonal, not the decision.
    def effect(day):
        return 7 if (day.month, day.day) >= (6, 1) and (day.month, day.day) < (7, 1) else 0
    rows, today = _flat_series(days=600, effect=effect)
    r = weekly.outcome(rows, [], 'orders', None, date(2026, 6, 1), date(2026, 6, 29), today - timedelta(days=599))
    assert r['available'] and r['change_percent'] > 20
    assert r['seasonal_change_percent'] is not None and abs(r['beyond_seasonal_points']) < 8, r


def _monday_8am_local():
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=16, minute=0, second=0, microsecond=0)  # 8am Pacific


def test_weekly_digest_sends_once_and_unsubscribe_works(harness):
    _synced(harness)
    with Session(saas.engine) as db:
        first = insight_loop.run_due(db, now=_monday_8am_local())
        again = insight_loop.run_due(db, now=_monday_8am_local())
        outbox = db.scalars(select(emailer.EmailOutbox).where(emailer.EmailOutbox.kind == 'weekly_digest')).all()
    assert first['digests'] == 1 and again['digests'] == 1 and len(outbox) == 1  # deduplicated
    mail = outbox[0]
    assert mail.to_address == 'owner@harbor.test' and mail.status == 'not_sent'  # no provider configured
    token = mail.text_body.split('token=')[1].split()[0]
    assert harness.api.get(f'/api/email/unsubscribe?token={token}').status_code == 200
    assert harness.get('/api/team/me/email').json()['weekly_digest'] is False
    assert harness.api.get('/api/email/unsubscribe?token=forged.weekly_digest.0000').status_code == 404


def test_outcome_email_goes_to_the_owner_once(harness):
    _synced(harness)
    harness.post('/api/decisions/plans', {
        'title': 'Open brunch an hour earlier', 'objective': 'returning_guests', 'offer_type': 'no_offer', 'offer_value': 0,
        'target_redemptions': 1, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35,
        'metric': 'orders', 'location_id': 'LOC_HARBOR', 'start_date': (date.today() - timedelta(days=35)).isoformat()})
    with Session(saas.engine) as db:
        insight_loop.run_due(db, now=_monday_8am_local() + timedelta(days=1))
        insight_loop.run_due(db, now=_monday_8am_local() + timedelta(days=1))
        mails = db.scalars(select(emailer.EmailOutbox).where(emailer.EmailOutbox.kind == 'outcome')).all()
    assert len(mails) == 1 and 'turned out' in mails[0].subject


def test_email_rendering_escapes_and_includes_unsubscribe():
    rows, today = _flat_series()
    brief = weekly.build_brief(rows, [], {'L1': 'Only store'}, today)
    subject, html_body, text = emailer.render_weekly(brief, 'Harbor Café', 'https://x/unsub?t=1')
    assert 'https://x/unsub?t=1' in html_body and 'Unsubscribe: https://x/unsub?t=1' in text
    assert brief['headline'] in subject and brief['method'] in text
    hostile = {'headline': 'Clear change', 'explanation': '<img src=x onerror=alert(1)> after'}
    _, html_body, _ = emailer.render_outcome({'title': '<script>alert(1)</script>'}, hostile, 'Harbor', 'https://x/u')
    assert '<script>' not in html_body and '&lt;script&gt;' in html_body
    assert '<img src=x' not in html_body and '&lt;img src=x' in html_body


def test_trial_ending_reminders_go_out_once_at_3_days_and_1_day(harness):
    _synced(harness)
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        ends = datetime.fromisoformat(w.trial_ends_at)
    for days_before in (5, 3, 3, 1):
        with Session(saas.engine) as db:
            insight_loop.run_due(db, now=ends - timedelta(days=days_before) + timedelta(hours=1))
    with Session(saas.engine) as db:
        mails = db.scalars(select(emailer.EmailOutbox).where(emailer.EmailOutbox.kind == 'trial_ending')).all()
    assert sorted(m.subject.split('ends ')[1] for m in mails) == ['in 3 days', 'tomorrow']
