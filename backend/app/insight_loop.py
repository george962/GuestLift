"""Insight -> Decision -> Track, wired to data, email and the worker (docs/PRODUCT_PLAN.md M4)."""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, time as day_time, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import config, emailer, weekly
from .database import Base, engine
from .local_auth import authenticated_subject


class WeeklyBrief(Base):
    __tablename__ = 'weekly_briefs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    week_start: Mapped[str] = mapped_column(String(10))
    generated_at: Mapped[str] = mapped_column(String(48))
    payload: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('workspace_id', 'week_start', name='uq_weekly_brief_week'),)


def _workspace_data(db: Session, wid: str, now: datetime | None = None):
    """Completed orders and refunds for the monitored locations, plus location names and time zone."""
    from .connections import SquareConnection, SquareOrder
    from .location_entitlements import selected_rows, selection_enabled
    from .square_sync import SquareLocationState, SquareRefund
    conn = db.scalar(select(SquareConnection).where(SquareConnection.workspace_id == wid))
    states = {s.location_id: s for s in db.scalars(select(SquareLocationState).where(SquareLocationState.workspace_id == wid))}
    allowed = ({r.location_id for r in selected_rows(db, wid, conn.merchant_id)} if conn and selection_enabled() else None)
    orders = [{'location_id': o.location_id, 'local_date': o.local_date or o.created_at[:10], 'net_sales_minor': o.net_sales_minor,
               'discount_minor': o.discount_minor, 'customer_id': o.customer_id}
              for o in db.scalars(select(SquareOrder).where(SquareOrder.workspace_id == wid, SquareOrder.status == 'COMPLETED'))
              if allowed is None or o.location_id in allowed]
    refunds = [{'location_id': f.location_id, 'local_date': f.local_date, 'amount_minor': f.amount_minor}
               for f in db.scalars(select(SquareRefund).where(SquareRefund.workspace_id == wid))
               if allowed is None or f.location_id in allowed]
    names = {loc: s.name for loc, s in states.items() if allowed is None or loc in allowed}
    tz = workspace_timezone((s.timezone for loc, s in states.items() if allowed is None or loc in allowed), now=now)
    earliest = min((date.fromisoformat(o['local_date']) for o in orders), default=None)
    return orders, refunds, names, tz, earliest


def local_today(tz: str, now: datetime | None = None) -> date:
    try:
        zone = ZoneInfo(tz)
    except Exception:
        zone = ZoneInfo('UTC')
    return (now or datetime.now(timezone.utc)).astimezone(zone).date()


def workspace_timezone(zones, now: datetime | None = None) -> str:
    """The workspace's clock: the zone where it is earliest (westernmost), so "last complete week",
    today's date and the Monday digest all wait until the week has ended at every location.
    Deterministic whatever order the locations come back in."""
    now = now or datetime.now(timezone.utc)

    def offset(tz: str):
        try:
            return now.astimezone(ZoneInfo(tz)).utcoffset()
        except Exception:
            return timedelta(0)
    return min(sorted(set(z for z in zones if z)), key=offset, default='UTC')


def _report_quality(db: Session, wid: str, start: date, end: date,
                    now: datetime | None = None) -> tuple[bool, str]:
    """Verify every monitored location covers [start, end), before making business claims.

    Order presence cannot prove that a day was fully imported. Only a completed,
    recent provider sync and each location's durable checkpoint can do that.
    """
    from .connections import SquareConnection
    from .location_entitlements import selected_rows, selection_enabled
    from .square_sync import SquareLocationState, STALE_AFTER, _parse

    now = now or datetime.now(timezone.utc)
    conn = db.scalar(select(SquareConnection).where(SquareConnection.workspace_id == wid))
    if conn is None or conn.status != 'active':
        return False, 'Square is disconnected or needs to be reconnected.'
    if not conn.last_sync_at:
        return False, 'The first successful Square sync is not finished.'
    try:
        last = _parse(conn.last_sync_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False, 'The last successful sync time is invalid.'
    if now - last > STALE_AFTER or last - now > timedelta(minutes=5):
        return False, 'Square data is stale; complete a new sync before interpreting changes.'
    if conn.last_error:
        return False, 'The most recent Square sync reported an error.'

    all_states = list(db.scalars(select(SquareLocationState).where(SquareLocationState.workspace_id == wid)))
    if selection_enabled():
        monitored = {r.location_id for r in selected_rows(db, wid, conn.merchant_id)}
        if not monitored:
            return False, 'No monitored Square locations are selected.'
        known = {s.location_id for s in all_states}
        if not monitored <= known:
            return False, 'A selected location has not completed its initial import.'
        states = [s for s in all_states if s.location_id in monitored]
    else:
        states = all_states
    if not states:
        return False, 'No locations have completed an initial Square sync.'

    for state in states:
        if not state.backfill_complete:
            return False, f'{state.name or state.location_id} is still importing sales history.'
        try:
            zone = ZoneInfo(state.timezone or 'UTC')
            start_utc = datetime.combine(start, day_time.min, tzinfo=zone).astimezone(timezone.utc)
            end_utc = datetime.combine(end, day_time.min, tzinfo=zone).astimezone(timezone.utc)
            first = _parse(state.backfill_start)
            through = _parse(state.synced_through) if state.synced_through else None
        except (ValueError, TypeError, KeyError):
            return False, f'{state.name or state.location_id} has an invalid sync checkpoint or time zone.'
        if first.tzinfo is None:
            first = first.replace(tzinfo=timezone.utc)
        if through is not None and through.tzinfo is None:
            through = through.replace(tzinfo=timezone.utc)
        if first > start_utc:
            return False, f'{state.name or state.location_id} has not imported the full comparison baseline.'
        if through is None or through < end_utc:
            return False, f'{state.name or state.location_id} has not synced through the complete reporting period.'
    return True, ''


def brief_for(db: Session, wid: str, today: date | None = None,
              now: datetime | None = None) -> dict:
    orders, refunds, names, tz, _ = _workspace_data(db, wid, now=now)
    today = today or local_today(tz, now)
    start = weekly.last_complete_week(today)
    ready, reason = _report_quality(db, wid, start - timedelta(days=28),
                                    start + timedelta(days=7), now=now)
    if not ready:
        return {'week_start': start.isoformat(), 'week_end': (start + timedelta(days=6)).isoformat(),
                'headline': 'Weekly findings paused until Square data is complete.',
                'findings': [], 'totals': None, 'caveats': [reason],
                'method': 'Incomplete or stale data is not treated as a real sales decline or as evidence of no change.',
                'has_data': bool(orders), 'data_status': 'incomplete'}
    result = weekly.build_brief(orders, refunds, names, today)
    result['has_data'] = bool(orders)
    result['data_status'] = 'ready'
    result['caveats'].append('Late Square corrections can change past totals; verify material changes against Square reports.')
    return result


def store_brief(db: Session, wid: str, brief: dict) -> None:
    row = db.scalar(select(WeeklyBrief).where(WeeklyBrief.workspace_id == wid, WeeklyBrief.week_start == brief['week_start']))
    if row is None:
        row = WeeklyBrief(id=str(uuid.uuid4()), workspace_id=wid, week_start=brief['week_start'], payload='{}', generated_at='')
        db.add(row)
    row.payload, row.generated_at = json.dumps(brief), datetime.now(timezone.utc).isoformat()
    db.commit()


def plan_outcome(db: Session, plan, today: date | None = None,
                 now: datetime | None = None) -> dict | None:
    """Compute readouts only from fully synchronized comparison periods."""
    if not plan.start_date or not plan.follow_up_date:
        return None
    orders, refunds, _, tz, earliest = _workspace_data(db, plan.workspace_id, now=now)
    today = today or local_today(tz, now)
    follow = date.fromisoformat(plan.follow_up_date)
    if today < follow:
        return {'available': False, 'due': plan.follow_up_date,
                'message': f'Readout on {follow:%b %d}, when there is enough data after the change.'}
    if plan.outcome:
        return json.loads(plan.outcome)
    started = date.fromisoformat(plan.start_date)
    span = max(7, ((follow - started).days // 7) * 7)
    ready, reason = _report_quality(db, plan.workspace_id, started - timedelta(days=span),
                                    started + timedelta(days=span), now=now)
    if not ready:
        return {'available': False, 'due': plan.follow_up_date,
                'message': 'Outcome delayed: ' + reason}
    result = weekly.outcome(orders, refunds, plan.metric or 'net_sales', plan.location_id,
                            started, follow, earliest)
    if result.get('available'):
        plan.outcome, plan.outcome_at = json.dumps(result), datetime.now(timezone.utc).isoformat()
        db.commit()
    return result


def member_email(db: Session, member) -> str:
    """Verified address for a member: cached, local account, or the Clerk user record."""
    if member.email:
        return member.email
    address = ''
    if config.auth_mode() == 'local':
        from .local_auth import LocalUser
        user = db.get(LocalUser, member.subject)
        address = user.email if user else ''
    elif os.getenv('CLERK_SECRET_KEY') and member.subject.startswith('oidc:'):
        try:
            r = httpx.get(f"https://api.clerk.com/v1/users/{member.subject[5:]}", timeout=10,
                          headers={'Authorization': f"Bearer {os.environ['CLERK_SECRET_KEY']}"})
            if r.status_code == 200:
                data = r.json()
                primary = data.get('primary_email_address_id')
                for e in data.get('email_addresses') or []:
                    if e.get('id') == primary and (e.get('verification') or {}).get('status') == 'verified':
                        address = e.get('email_address', '')
        except httpx.HTTPError:
            address = ''
    if address:
        member.email = address[:254]
        db.commit()
    return address


def run_due(db: Session, now: datetime | None = None) -> dict:
    """Worker hook: queue what's due, then deliver everything pending (including earlier retries).

    Due: Monday digests (7am local), outcome emails on follow-up dates, and trial-ending reminders
    3 days and 1 day out. Returns {'queued': {kind: n}, 'sent', 'failed', 'expired', 'skipped': n
    this pass, 'pending': n still waiting}.
    """
    from .billing import entitlement
    from .connections import SquareConnection
    from .decisions import DecisionPlan
    from .membership import WorkspaceMember
    from .saas import Workspace
    now = now or datetime.now(timezone.utc)
    queued = {'weekly_digest': 0, 'outcome': 0, 'trial_ending': 0}

    def queue(w, kind, key, to, rendered) -> None:
        if emailer.enqueue(db, w.id, kind, key, to, *rendered, now=now):
            queued[kind] += 1

    for conn in db.scalars(select(SquareConnection).where(SquareConnection.status == 'active')).all():
        w = db.get(Workspace, conn.workspace_id)
        if w is None or not conn.last_sync_at:
            continue
        e = entitlement(w, now)
        if e['access'] != 'full':
            continue
        members = db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == w.id)).all()
        owners = [m for m in members if m.role == 'owner']
        if e['state'] == 'trial' and e['days_left'] in (1, 3):  # M5 trial-ending reminders, once per owner each
            for m in owners:
                if not m.outcome_emails or not (to := member_email(db, m)):
                    continue
                if emailer.already_recorded(db, emailer.legacy_trial_key(w.id, e['days_left']), to):
                    continue  # sent under the old per-workspace key
                queue(w, 'trial_ending', emailer.trial_key(w.id, m.id, e['days_left']), to,
                      emailer.render_trial_ending(e['days_left'], w.name, emailer.unsubscribe_url(m.id, 'trial_ending')))
        orders, _, _, tz, _ = _workspace_data(db, w.id, now=now)
        local = now.astimezone(ZoneInfo(tz) if tz else ZoneInfo('UTC'))
        if orders and local.weekday() == 0 and local.hour >= 7:
            brief = brief_for(db, w.id, local.date(), now=now)
            if brief['data_status'] == 'ready':
                store_brief(db, w.id, brief)
                for m in members:
                    if not m.weekly_digest or not (to := member_email(db, m)):
                        continue
                    queue(w, 'weekly_digest', emailer.digest_key(m.id, brief['week_start']), to,
                          emailer.render_weekly(brief, w.name, emailer.unsubscribe_url(m.id, 'weekly_digest')))
        for plan in db.scalars(select(DecisionPlan).where(DecisionPlan.workspace_id == w.id,
                                                          DecisionPlan.follow_up_date <= local.date().isoformat())).all():
            result = plan_outcome(db, plan, local.date(), now=now)
            if not result or not result.get('available'):
                continue
            for m in owners:
                if not m.outcome_emails or not (to := member_email(db, m)):
                    continue
                queue(w, 'outcome', emailer.outcome_key(plan.id, m.id), to,
                      emailer.render_outcome({'title': plan.title}, result, w.name, emailer.unsubscribe_url(m.id, 'outcome')))
    return {'queued': queued, **emailer.deliver_pending(db, now)}


router = APIRouter(tags=['Weekly brief and email'])


@router.get('/api/briefs/latest')
def latest_brief(sub: str = Depends(authenticated_subject)):
    from .saas import _get_workspace
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        return brief_for(db, w.id)


class EmailPreferences(BaseModel):
    weekly_digest: bool
    outcome_emails: bool


@router.get('/api/team/me/email')
def my_email_preferences(sub: str = Depends(authenticated_subject)):
    from .membership import WorkspaceMember, resolve
    with Session(engine) as db:
        resolve(db, sub)
        m = db.scalar(select(WorkspaceMember).where(WorkspaceMember.subject == sub))
        return {'email': member_email(db, m) or None, 'weekly_digest': m.weekly_digest, 'outcome_emails': m.outcome_emails,
                'provider_configured': emailer.provider_configured()}


@router.post('/api/team/me/email')
def update_email_preferences(prefs: EmailPreferences, sub: str = Depends(authenticated_subject)):
    from .membership import WorkspaceMember, resolve
    with Session(engine) as db:
        resolve(db, sub)
        m = db.scalar(select(WorkspaceMember).where(WorkspaceMember.subject == sub))
        m.weekly_digest, m.outcome_emails = prefs.weekly_digest, prefs.outcome_emails
        db.commit()
        return {'weekly_digest': m.weekly_digest, 'outcome_emails': m.outcome_emails}


@router.get('/api/email/unsubscribe', response_class=HTMLResponse)
def unsubscribe(token: str = ''):
    """One-click unsubscribe from an email link; no sign-in needed."""
    from .membership import WorkspaceMember
    found = emailer.verify_unsubscribe(token)
    if not found:
        raise HTTPException(404, 'This unsubscribe link is not valid.')
    member_id, kind = found
    with Session(engine) as db:
        m = db.get(WorkspaceMember, member_id)
        if m:
            setattr(m, emailer.PREFERENCE[kind], False)
            db.commit()
    what = {'weekly_digest': 'the weekly brief', 'outcome': 'decision outcome emails or trial reminders',
            'trial_ending': 'trial reminders or decision outcome emails'}[kind]
    return f"<!doctype html><title>Unsubscribed</title><p style='font-family:sans-serif'>You won't get {what} any more. " \
           f"You can turn it back on in <a href='{config.app_url()}/settings'>Settings</a>.</p>"
