"""P2 regressions: retryable, idempotent email delivery; preferences at send time; accurate counts;
per-recipient trial reminders; 422s for bad dates. Resend is always a local fake (httpx.MockTransport)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import connections, emailer, insight_loop, membership, saas, square_sync
from journey_support import harness  # noqa: F401

# The journey harness swaps httpx.Client for the mock Square client; keep the real class for the fake.
RealClient = httpx.Client


class FakeResend:
    """Behaves like Resend's POST /emails, including 24h idempotency keys.

    `script` holds responses for the next requests: an int status code, 'accept_then_timeout'
    (Resend accepts the email but the reply never arrives), or 'network'. Then 200s.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.accepted: dict[str, str] = {}  # idempotency key -> email id
        self.script: list = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = request.headers.get('Idempotency-Key', '')
        if key in self.accepted:  # same key, same payload: same answer, no second email
            return httpx.Response(200, json={'id': self.accepted[key]})
        step = self.script.pop(0) if self.script else 200
        if step == 'network':
            raise httpx.ConnectError('no route', request=request)
        if step in (200, 'accept_then_timeout'):
            self.accepted[key] = f're_{uuid.uuid4().hex[:12]}'
            if step == 'accept_then_timeout':
                raise httpx.ReadTimeout('reply lost', request=request)
            return httpx.Response(200, json={'id': self.accepted[key]})
        names = {401: 'validation_error', 409: 'concurrent_idempotent_requests', 422: 'invalid_parameter',
                 429: 'rate_limit_exceeded', 503: 'service_unavailable'}
        return httpx.Response(step, json={'statusCode': step, 'name': names.get(step, 'application_error'), 'message': 'x'})

    def about(self, word: str) -> list[httpx.Request]:
        return [r for r in self.requests if word in r.content.decode()]

    @property
    def emails_delivered(self) -> int:
        return len(self.accepted)


@pytest.fixture
def resend(monkeypatch):
    fake = FakeResend()

    def configure():
        monkeypatch.setenv('RESEND_API_KEY', 're_test_not_a_real_key')
        monkeypatch.setenv('EMAIL_FROM', 'TableSignal <brief@example.test>')
        monkeypatch.setattr(emailer, '_client', lambda: RealClient(transport=httpx.MockTransport(fake.handler)))
    fake.configure = configure
    return fake


def _synced(h):
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    assert h.post('/api/integrations/square/sync').status_code == 200


def _monday_8am_pacific():
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(hour=16, minute=0, second=0, microsecond=0)


def _run(now):
    # These P2 tests time-travel the worker to exercise email delivery. The mock
    # data was otherwise synced at real wall-clock time, which can be *before*
    # the last local Sunday has ended at the simulated Monday. P1 must reject
    # that incomplete reporting window. For an email-only test, explicitly
    # simulate a successful complete provider sync at the worker's test time.
    with Session(saas.engine) as db:
        states = db.scalars(select(square_sync.SquareLocationState)).all()
        if states:
            zone = insight_loop.workspace_timezone((s.timezone for s in states), now=now)
            local = now.astimezone(ZoneInfo(zone))
            if local.weekday() == 0 and local.hour >= 7:
                conn = db.scalar(select(connections.SquareConnection))
                if conn:
                    through = now.astimezone(timezone.utc).isoformat()
                    conn.last_sync_at = through
                    conn.last_error = None
                    for state in states:
                        state.backfill_complete = True
                        state.synced_through = through
                    db.commit()
        return insight_loop.run_due(db, now=now)


def _rows(kind=None):
    with Session(saas.engine) as db:
        q = select(emailer.EmailOutbox)
        if kind:
            q = q.where(emailer.EmailOutbox.kind == kind)
        return db.scalars(q.order_by(emailer.EmailOutbox.created_at)).all()


def _trial_end():
    with Session(saas.engine) as db:
        return datetime.fromisoformat(db.scalar(select(saas.Workspace)).trial_ends_at)


def _unsubscribe_link_from(mail) -> str:
    return '/api/email/unsubscribe?token=' + mail.text_body.split('token=')[1].split()[0]


# Bug 1: messages recorded while no provider was configured were never sent.

def test_pending_digest_is_sent_once_the_provider_is_configured(harness, resend):
    _synced(harness)
    monday = _monday_8am_pacific()
    assert _run(monday)['pending'] == 1 and not resend.requests
    resend.configure()
    report = _run(monday + timedelta(hours=1))
    assert report['sent'] == 1 and report['pending'] == 0
    [mail] = _rows('weekly_digest')
    assert mail.status == 'sent' and mail.provider_id == next(iter(resend.accepted.values()))
    [request] = resend.requests
    assert request.headers['Idempotency-Key'] == f'tablesignal-email/{mail.id}'
    assert _run(monday + timedelta(hours=2))['sent'] == 0 and len(resend.requests) == 1  # nothing left to send


def test_legacy_not_sent_rows_are_retried(harness, resend):
    _synced(harness)
    _run(_monday_8am_pacific())
    with Session(saas.engine) as db:  # what the old code recorded when no provider was configured
        db.scalar(select(emailer.EmailOutbox)).status = 'not_sent'
        db.commit()
    resend.configure()
    assert _run(_monday_8am_pacific() + timedelta(hours=1))['sent'] == 1
    assert [m.status for m in _rows()] == ['sent'] and resend.emails_delivered == 1


def test_stale_messages_expire_instead_of_going_out_late(harness, resend):
    _synced(harness)
    _run(_monday_8am_pacific())
    resend.configure()
    report = _run(_monday_8am_pacific() + timedelta(days=4))  # Friday: the Monday brief is out of date
    assert report['expired'] == 1 and report['sent'] == 0 and not resend.requests
    assert [m.status for m in _rows()] == ['expired']


# Retries and restarts must not deliver twice; provider errors are classified.

def test_retry_after_a_lost_reply_does_not_send_a_second_copy(harness, resend):
    _synced(harness)
    resend.configure()
    resend.script = ['accept_then_timeout']
    first = _run(_monday_8am_pacific())
    assert first['sent'] == 0 and first['pending'] == 1  # we don't know it went out, so it stays pending
    second = _run(_monday_8am_pacific() + timedelta(minutes=10))  # the next pass, or a restarted worker
    assert second['sent'] == 1 and second['pending'] == 0
    keys = {r.headers['Idempotency-Key'] for r in resend.requests}
    assert len(resend.requests) == 2 and len(keys) == 1 and resend.emails_delivered == 1


def test_two_workers_cannot_both_record_the_same_message(harness, monkeypatch):
    _synced(harness)
    with Session(saas.engine) as db:
        wid = db.scalar(select(saas.Workspace)).id
        args = (wid, 'weekly_digest', 'digest:m1:2026-11-16', 'owner@harbor.test', 's', '<p>h</p>', 't')
        assert emailer.enqueue(db, *args) is True
        monkeypatch.setattr(emailer, 'already_recorded', lambda *a, **k: False)  # lost the race to check first
        assert emailer.enqueue(db, *args) is False  # the unique key refuses it instead
    assert len(_rows()) == 1


def test_provider_outage_keeps_mail_pending_and_rejections_fail(harness, resend):
    _synced(harness)
    resend.configure()
    resend.script = [503]
    assert _run(_monday_8am_pacific())['pending'] == 1
    assert _run(_monday_8am_pacific() + timedelta(minutes=10))['sent'] == 1  # retried after the outage
    with Session(saas.engine) as db:
        wid = db.scalar(select(saas.Workspace)).id
        owner = db.scalar(select(membership.WorkspaceMember))
        for n in range(3):
            emailer.enqueue(db, wid, 'outcome', emailer.outcome_key(f'plan{n}', owner.id), owner.email, 's', 'h', 't',
                            now=_monday_8am_pacific())
    resend.script = [422, 401]  # this address rejected; then the key stops working
    report = _run(_monday_8am_pacific() + timedelta(minutes=20))
    assert report['failed'] == 1 and report['sent'] == 0 and report['pending'] == 2
    assert len(resend.requests) == 4  # the pass stopped at the 401 instead of trying every message
    resend.script = [409]  # Resend still processing the same key elsewhere: try later
    assert _run(_monday_8am_pacific() + timedelta(minutes=30))['pending'] == 1
    assert _run(_monday_8am_pacific() + timedelta(minutes=40))['pending'] == 0
    with Session(saas.engine) as db:
        assert emailer.outbox_counts(db) == {'pending': 0, 'sent': 3, 'failed': 1, 'expired': 0, 'skipped': 0}


# Bug 2: trial reminders ignored unsubscribing. Preferences are checked again at delivery.

def test_unsubscribing_from_a_trial_reminder_stops_the_next_one(harness, resend):
    _synced(harness)
    ends = _trial_end()
    _run(ends - timedelta(days=3) + timedelta(hours=1))
    [first] = _rows('trial_ending')
    assert harness.api.get(_unsubscribe_link_from(first)).status_code == 200
    resend.configure()
    report = _run(ends - timedelta(days=3) + timedelta(hours=2))
    assert report['skipped'] == 1 and not resend.about('trial')  # the queued one is not delivered either
    assert _run(ends - timedelta(days=1) + timedelta(hours=1))['queued']['trial_ending'] == 0
    assert [m.status for m in _rows('trial_ending')] == ['skipped'] and not resend.about('trial')


def test_links_in_trial_emails_already_sent_still_unsubscribe(harness):
    _synced(harness)
    with Session(saas.engine) as db:  # older trial emails linked to the outcome-email switch
        owner_id = db.scalar(select(membership.WorkspaceMember)).id
    old_link = f"/api/email/unsubscribe?token={emailer.unsubscribe_token(owner_id, 'outcome')}"
    assert harness.api.get(old_link).status_code == 200
    assert _run(_trial_end() - timedelta(days=3) + timedelta(hours=1))['queued']['trial_ending'] == 0


def test_queued_digest_is_not_sent_after_the_member_opts_out(harness, resend):
    _synced(harness)
    _run(_monday_8am_pacific())
    assert harness.post('/api/team/me/email', {'weekly_digest': False, 'outcome_emails': True}).status_code == 200
    resend.configure()
    assert _run(_monday_8am_pacific() + timedelta(hours=1))['skipped'] == 1 and not resend.requests


def test_trial_reminder_is_dropped_once_the_workspace_subscribes(harness, resend):
    _synced(harness)
    ends = _trial_end()
    _run(ends - timedelta(days=3) + timedelta(hours=1))
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        w.stripe_subscription_id, w.subscription_status = 'sub_test', 'active'
        db.commit()
    resend.configure()
    _run(ends - timedelta(days=3) + timedelta(hours=2))
    assert [m.status for m in _rows('trial_ending')] == ['skipped'] and not resend.about('trial')


# Bug 3: counts. not_sent was counted as sent, and reruns counted again.

def test_counts_report_what_actually_happened(harness, resend):
    _synced(harness)
    monday = _monday_8am_pacific()
    first, again = _run(monday), _run(monday)
    assert (first['queued']['weekly_digest'], first['sent'], first['pending']) == (1, 0, 1)
    assert (again['queued']['weekly_digest'], again['sent'], again['pending']) == (0, 0, 1)
    with Session(saas.engine) as db:
        db.scalar(select(emailer.EmailOutbox)).status = 'not_sent'
        db.commit()
        assert emailer.outbox_counts(db)['sent'] == 0 and emailer.outbox_counts(db)['pending'] == 1
    resend.configure()
    resend.script = [422]
    assert _run(monday + timedelta(hours=1))['failed'] == 1
    with Session(saas.engine) as db:
        assert emailer.outbox_counts(db) == {'pending': 0, 'sent': 0, 'failed': 1, 'expired': 0, 'skipped': 0}


# Bug 4: trial reminders were deduplicated per workspace, so a second owner never got one.

def _add_owner(email):
    with Session(saas.engine) as db:
        wid = db.scalar(select(saas.Workspace)).id
        db.add(membership.WorkspaceMember(id=str(uuid.uuid4()), workspace_id=wid, subject=f'local:{email}', role='owner',
                                          email=email, created_at=datetime.now(timezone.utc).isoformat()))
        db.commit()
        return wid


def test_every_owner_gets_their_own_trial_reminder(harness):
    _synced(harness)
    _add_owner('co-owner@harbor.test')
    ends = _trial_end()
    for hours in (1, 2):
        _run(ends - timedelta(days=3) + timedelta(hours=hours))
    assert sorted(m.to_address for m in _rows('trial_ending')) == ['co-owner@harbor.test', 'owner@harbor.test']


def test_reminder_recorded_under_the_old_key_is_not_repeated(harness):
    _synced(harness)
    wid = _add_owner('co-owner@harbor.test')
    with Session(saas.engine) as db:  # the old code recorded the first owner's reminder per workspace
        emailer.enqueue(db, wid, 'trial_ending', emailer.legacy_trial_key(wid, 3), 'owner@harbor.test', 's', 'h', 't')
    _run(_trial_end() - timedelta(days=3) + timedelta(hours=1))
    new = [m.to_address for m in _rows('trial_ending') if m.dedupe_key != emailer.legacy_trial_key(wid, 3)]
    assert new == ['co-owner@harbor.test']


# Bug 5: impossible or out-of-range dates crashed the server.

PLAN = {'title': 'Open brunch an hour earlier', 'objective': 'returning_guests', 'offer_type': 'no_offer', 'offer_value': 0,
        'target_redemptions': 1, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35, 'metric': 'orders'}


@pytest.mark.parametrize('bad', ['2026-02-30', '2026-13-01', '0001-01-05', '2026-1-5', '20261116', 'soon'])
def test_bad_decision_start_dates_get_a_clear_422(harness, bad):
    _synced(harness)
    r = harness.post('/api/decisions/plans', {**PLAN, 'start_date': bad})
    assert r.status_code == 422 and isinstance(r.json()['detail'], str) and 'date' in r.json()['detail'].lower(), r.text
    assert harness.get('/api/decisions/plans').status_code == 200


def test_valid_start_dates_still_work(harness):
    _synced(harness)
    r = harness.post('/api/decisions/plans', {**PLAN, 'start_date': (date.today() - timedelta(days=35)).isoformat()})
    assert r.status_code == 201, r.text


@pytest.mark.parametrize('query', ['start=2026-02-30', 'end=2026-04-31', 'end=0001-01-03', 'start=2026-11-1', 'end=x'])
def test_bad_reconciliation_dates_get_a_clear_422(harness, query):
    _synced(harness)
    r = harness.get(f'/api/integrations/square/reconciliation?{query}')
    assert r.status_code == 422 and isinstance(r.json()['detail'], str), r.text


# The email preferences interface is unchanged.

def test_email_preferences_interface_is_unchanged(harness):
    _synced(harness)
    prefs = harness.get('/api/team/me/email').json()
    assert set(prefs) == {'email', 'weekly_digest', 'outcome_emails', 'provider_configured'}
    assert prefs['provider_configured'] is False
    r = harness.post('/api/team/me/email', {'weekly_digest': False, 'outcome_emails': True})
    assert r.json() == {'weekly_digest': False, 'outcome_emails': True}
