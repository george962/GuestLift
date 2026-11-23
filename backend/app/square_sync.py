"""Square sync engine: checkpointed backfill + incremental sync (docs/PRODUCT_PLAN.md M3).

How it works
- Each monitored location is synced in 7-day windows of order creation time, oldest first.
  A window's payments (for guest IDs), orders and refunds are written in one transaction,
  then the location's `synced_through` checkpoint moves forward. A crash or a 429 loses at
  most the window in progress; the next run resumes from the checkpoint. Upserts are keyed
  on Square's IDs, so re-reading a window never duplicates anything.
- First sync backfills GUESTLIFT_BACKFILL_DAYS (default 395, about 13 months). Later syncs
  re-read the last 3 days (late edits, tips) and continue to now.
- There is no order-count cap: a run stops after a time budget and the job continues later.
- Daily figures use each location's own time zone, like Square's reports.
- Refunds come from the Refunds API and are counted on the day they happened.
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base

WINDOW = timedelta(days=7)
INCREMENTAL_OVERLAP = timedelta(days=3)
PAYMENT_LAG = timedelta(days=1)  # a payment can be created shortly after its order
MAX_PAGES_PER_CALL = 2000  # runaway-cursor guard only; not a business limit
PAGE_SIZE = 100
STALE_AFTER = timedelta(hours=12)


def backfill_days() -> int:
    try:
        return max(1, min(800, int(os.getenv('GUESTLIFT_BACKFILL_DAYS', '395'))))
    except ValueError:
        return 395


def sync_interval_seconds() -> int:
    try:
        return max(900, int(float(os.getenv('GUESTLIFT_SYNC_INTERVAL_HOURS', '4')) * 3600))
    except ValueError:
        return 4 * 3600


class SquareLocationState(Base):
    __tablename__ = 'square_location_state'
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), default='')
    timezone: Mapped[str] = mapped_column(String(64), default='UTC')
    backfill_start: Mapped[str] = mapped_column(String(32))
    synced_through: Mapped[str | None] = mapped_column(String(32), nullable=True)
    backfill_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[str] = mapped_column(String(48))


class SquareRefund(Base):
    __tablename__ = 'square_refunds'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    source_refund_id: Mapped[str] = mapped_column(String(160))
    order_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_id: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[str] = mapped_column(String(55))
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    __table_args__ = (UniqueConstraint('workspace_id', 'source_refund_id', name='uq_square_refund_owner'),)


class SquareSyncJob(Base):
    __tablename__ = 'square_sync_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # manual | scheduled
    status: Mapped[str] = mapped_column(String(20), index=True)  # queued | running | succeeded | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    run_after: Mapped[int] = mapped_column(Integer, index=True)
    locked_until: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[str] = mapped_column(Text, default='{}')
    last_error: Mapped[str] = mapped_column(String(220), default='')
    created_at: Mapped[str] = mapped_column(String(48))
    updated_at: Mapped[str] = mapped_column(String(48))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or 'UTC')
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo('UTC')


def local_date(ts: str, tz: str) -> str:
    try:
        return _parse(ts).astimezone(_zone(tz)).date().isoformat()
    except ValueError:
        return ts[:10]


def _pages(fetch, key: str):
    """Yield every item across cursor pages; refuse repeating cursors."""
    cursor, seen = None, set()
    for _ in range(MAX_PAGES_PER_CALL):
        result = fetch(cursor)
        items = result.get(key) or []
        if not isinstance(items, list):
            raise HTTPException(502, f'Unexpected Square {key} response.')
        yield from (x for x in items if isinstance(x, dict))
        cursor = result.get('cursor')
        if not cursor:
            return
        if cursor in seen:
            raise HTTPException(502, 'Square returned a repeated pagination cursor.')
        seen.add(cursor)
    raise HTTPException(502, 'Square pagination did not finish.')


def _sync_window(db: Session, wid: str, token: str, loc: SquareLocationState, start: datetime,
                 end: datetime, counts: dict) -> None:
    from .connections import SquareOrder, _api, _parse_order
    begin, finish = _iso(start), _iso(end)
    guests: dict[str, str] = {}
    for p in _pages(lambda c: _api(token, 'GET', '/v2/payments', {
            'location_id': loc.location_id, 'begin_time': begin, 'end_time': _iso(min(end + PAYMENT_LAG, datetime.now(timezone.utc))),
            'limit': PAGE_SIZE, 'sort_order': 'ASC', **({'cursor': c} if c else {})}), 'payments'):
        if p.get('order_id') and p.get('customer_id') and p.get('status') == 'COMPLETED':
            guests[str(p['order_id'])] = str(p['customer_id'])
    for raw in _pages(lambda c: _api(token, 'POST', '/v2/orders/search', {
            'location_ids': [loc.location_id], 'limit': PAGE_SIZE, 'return_entries': False,
            'query': {'filter': {'date_time_filter': {'created_at': {'start_at': begin, 'end_at': finish}}},
                      'sort': {'sort_field': 'CREATED_AT', 'sort_order': 'ASC'}},
            **({'cursor': c} if c else {})}), 'orders'):
        counts['scanned'] += 1
        parsed = _parse_order(raw)
        if parsed is None or parsed['location_id'] != loc.location_id:
            counts['skipped'] += 1
            continue
        parsed['customer_id'] = parsed['customer_id'] or guests.get(parsed['source_order_id'])
        parsed['local_date'] = local_date(parsed['created_at'], loc.timezone)
        existing = db.scalar(select(SquareOrder).where(
            SquareOrder.workspace_id == wid, SquareOrder.source_order_id == parsed['source_order_id']))
        if existing is None:
            db.add(SquareOrder(id=str(uuid.uuid4()), workspace_id=wid, **parsed))
            counts['inserted'] += 1
        elif parsed['updated_at'] >= existing.updated_at:
            for key, value in parsed.items():
                setattr(existing, key, value)
            counts['updated'] += 1
    for r in _pages(lambda c: _api(token, 'GET', '/v2/refunds', {
            'location_id': loc.location_id, 'begin_time': begin, 'end_time': finish,
            'limit': PAGE_SIZE, 'sort_order': 'ASC', **({'cursor': c} if c else {})}), 'refunds'):
        money = r.get('amount_money') or {}
        if not r.get('id') or r.get('status') != 'COMPLETED' or money.get('currency') != 'USD' \
                or not isinstance(money.get('amount'), int):
            continue
        created = str(r.get('created_at') or begin)
        existing = db.scalar(select(SquareRefund).where(
            SquareRefund.workspace_id == wid, SquareRefund.source_refund_id == str(r['id'])))
        values = dict(order_id=str(r['order_id']) if r.get('order_id') else None, location_id=loc.location_id,
                      created_at=created, local_date=local_date(created, loc.timezone),
                      amount_minor=int(money['amount']), status='COMPLETED')
        if existing is None:
            db.add(SquareRefund(id=str(uuid.uuid4()), workspace_id=wid, source_refund_id=str(r['id']), **values))
            counts['refunds'] += 1
        else:
            for key, value in values.items():
                setattr(existing, key, value)
    loc.synced_through = finish
    loc.updated_at = _iso(datetime.now(timezone.utc))


def _location_states(db: Session, wid: str, token: str, merchant: str) -> list[SquareLocationState]:
    """Create or refresh per-location state for the locations this workspace syncs."""
    from .connections import _merchant_from_locations
    from .location_entitlements import eligible_location, selected_rows, selection_enabled
    found_merchant, locations = _merchant_from_locations(token)
    if found_merchant != merchant:
        raise HTTPException(409, 'This Square token belongs to a different merchant.')
    if selection_enabled():
        chosen = {x.location_id for x in selected_rows(db, wid, merchant)}
        authorized = {str(l['id']) for l in locations if eligible_location(l)}
        if not chosen or not chosen <= authorized:
            raise HTTPException(409, 'Choose currently eligible Square locations before syncing.')
        wanted = [l for l in locations if str(l['id']) in chosen]
    else:
        wanted = [l for l in locations if l.get('status') != 'INACTIVE'] or locations
    now = datetime.now(timezone.utc)
    states = []
    for l in wanted:
        state = db.get(SquareLocationState, (wid, str(l['id'])))
        if state is None:
            state = SquareLocationState(workspace_id=wid, location_id=str(l['id']),
                                        backfill_start=_iso(now - timedelta(days=backfill_days())),
                                        updated_at=_iso(now))
            db.add(state)
        state.name = str(l.get('name') or l['id'])[:160]
        state.timezone = str(l.get('timezone') or 'UTC')[:64]
        states.append(state)
    db.commit()
    return states


def run_sync(db: Session, wid: str, token: str, merchant: str, budget_seconds: float = 20.0) -> dict:
    """Advance every location's checkpoint until caught up or the time budget runs out."""
    deadline = time.monotonic() + budget_seconds
    counts = {'scanned': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'refunds': 0, 'windows': 0}
    now = datetime.now(timezone.utc)
    for loc in _location_states(db, wid, token, merchant):
        start = _parse(loc.synced_through) if loc.synced_through else _parse(loc.backfill_start)
        if loc.backfill_complete:
            start = start - INCREMENTAL_OVERLAP
        while start < now:
            if time.monotonic() > deadline:
                db.commit()
                return {**counts, 'complete': False}
            end = min(start + WINDOW, now)
            try:
                _sync_window(db, wid, token, loc, start, end, counts)
                if end >= now:
                    loc.backfill_complete = True
                db.commit()
            except Exception:
                db.rollback()
                raise
            counts['windows'] += 1
            start = end
    return {**counts, 'complete': True}


def progress(db: Session, wid: str) -> dict:
    """How far the history import has got, across monitored locations."""
    states = db.scalars(select(SquareLocationState).where(SquareLocationState.workspace_id == wid)).all()
    if not states:
        return {'locations': 0, 'percent': 0, 'complete': False, 'synced_through': None}
    now = datetime.now(timezone.utc)
    done, total, through = 0.0, 0.0, []
    for s in states:
        begin = _parse(s.backfill_start)
        span = max(1.0, (now - begin).total_seconds())
        reached = _parse(s.synced_through) if s.synced_through else begin
        total += span
        done += span if s.backfill_complete else max(0.0, (reached - begin).total_seconds())
        through.append(s.synced_through or s.backfill_start)
    return {'locations': len(states), 'percent': round(100 * done / total), 'complete': all(s.backfill_complete for s in states),
            'synced_through': min(through)}


def enqueue(db: Session, wid: str, kind: str, delay_seconds: int = 0, claimed: bool = False,
            lease_seconds: int = 300) -> SquareSyncJob:
    """One open job per workspace; a second request reuses it.

    `claimed=True` creates the job already leased to the caller, so a worker polling the queue
    can't take it in the gap between creating and claiming it.
    """
    open_job = db.scalar(select(SquareSyncJob).where(SquareSyncJob.workspace_id == wid,
                                                     SquareSyncJob.status.in_(('queued', 'running'))))
    if open_job:
        return open_job
    now_ts, now = int(time.time()), _iso(datetime.now(timezone.utc))
    job = SquareSyncJob(id=str(uuid.uuid4()), workspace_id=wid, kind=kind,
                        status='running' if claimed else 'queued', attempts=0,
                        run_after=now_ts + delay_seconds, locked_until=now_ts + lease_seconds if claimed else 0,
                        progress='{}', last_error='', created_at=now, updated_at=now)
    db.add(job)
    db.commit()
    job.claimed_here = claimed  # transient marker for the caller
    return job


def claim(db: Session, job_id: str, lease_seconds: int = 300) -> bool:
    """Atomically take a job; safe with several workers on PostgreSQL or SQLite."""
    now = int(time.time())
    result = db.execute(update(SquareSyncJob).where(
        SquareSyncJob.id == job_id, SquareSyncJob.locked_until < now,
        SquareSyncJob.status.in_(('queued', 'running'))).values(
        status='running', locked_until=now + lease_seconds, updated_at=_iso(datetime.now(timezone.utc))))
    db.commit()
    return result.rowcount == 1


RETRYABLE = (429, 500, 502, 503, 504)


def classify(exc: Exception) -> str:
    """retry | reconnect | fail."""
    if isinstance(exc, HTTPException):
        if exc.status_code == 422 and 'authoriz' in str(exc.detail).lower():
            return 'reconnect'
        if exc.status_code in RETRYABLE:
            return 'retry'
        return 'fail'
    return 'retry'


def backoff_seconds(attempts: int) -> int:
    return int(min(3600, 60 * 2 ** max(0, attempts - 1)) * random.uniform(0.8, 1.2))


def execute(db: Session, job: SquareSyncJob, budget_seconds: float) -> dict:
    """Run one slice of a job and record the outcome. Returns the run result (or raises after recording)."""
    from .connections import SquareSyncRun, _connection, _refresh_oauth
    started = _iso(datetime.now(timezone.utc))
    run = SquareSyncRun(id=str(uuid.uuid4()), workspace_id=job.workspace_id, started_at=started, status='running')
    db.add(run)
    db.commit()
    conn = _connection(db, job.workspace_id)
    try:
        if conn is None or conn.status != 'active':
            raise HTTPException(409, 'Square is not connected. Reconnect Square to resume syncing.')
        token = _refresh_oauth(conn, db)
        result = run_sync(db, job.workspace_id, token, conn.merchant_id, budget_seconds)
    except Exception as exc:
        db.rollback()
        outcome = classify(exc)
        job = db.get(SquareSyncJob, job.id)
        run = db.get(SquareSyncRun, run.id)
        conn = _connection(db, job.workspace_id)
        job.attempts += 1
        message = str(exc.detail) if isinstance(exc, HTTPException) else 'Unexpected sync error.'
        job.last_error = message[:220]
        if outcome == 'retry' and job.attempts < 6:
            job.status, job.run_after = 'queued', int(time.time()) + backoff_seconds(job.attempts)
        else:
            job.status = 'failed'
        job.locked_until = 0
        run.status, run.completed_at = 'failed', _iso(datetime.now(timezone.utc))
        run.message = message[:200]
        if conn:
            conn.last_error = ('Square needs you to reconnect.' if outcome == 'reconnect'
                               else 'Most recent sync did not finish; it will retry automatically.'
                               if job.status == 'queued' else 'Most recent sync failed.')[:220]
            if outcome == 'reconnect':
                conn.status = 'needs_reconnect'
        db.commit()
        raise
    job = db.get(SquareSyncJob, job.id)
    run = db.get(SquareSyncRun, run.id)
    conn = _connection(db, job.workspace_id)
    run.scanned, run.inserted, run.updated, run.skipped = (result['scanned'], result['inserted'],
                                                           result['updated'], result['skipped'])
    run.completed_at = _iso(datetime.now(timezone.utc))
    run.status = 'completed' if result['complete'] else 'partial'
    job.progress = json.dumps(progress(db, job.workspace_id))
    job.locked_until = 0
    if result['complete']:
        job.status, job.last_error = 'succeeded', ''
        conn.last_sync_at, conn.last_error = run.completed_at, None
    else:
        job.status, job.run_after = 'queued', int(time.time())
    job.updated_at = run.completed_at
    db.commit()
    return result


def health(db: Session, wid: str) -> dict:
    """What the owner needs to know before trusting the numbers."""
    from .connections import SquareOrder, _connection, square_environment
    conn = _connection(db, wid)
    base = {'environment': square_environment(), 'connected': conn is not None}
    if conn is None:
        return {**base, 'status': 'not_connected', 'message': 'Connect Square to see your numbers.',
                'last_success_at': None, 'backfill': None, 'job': None, 'gaps': []}
    p = progress(db, wid)
    job = db.scalar(select(SquareSyncJob).where(SquareSyncJob.workspace_id == wid)
                    .order_by(SquareSyncJob.updated_at.desc(), SquareSyncJob.created_at.desc()).limit(1))
    last = conn.last_sync_at
    stale = bool(last) and datetime.now(timezone.utc) - _parse(last) > STALE_AFTER
    if conn.status == 'needs_reconnect':
        status, message = 'needs_reconnect', 'Square stopped accepting our access. Reconnect Square to resume updates.'
    elif conn.status == 'revoked':
        status, message = 'revoked', 'Access was turned off in Square. Reconnect to resume updates.'
    elif not p['complete']:
        status, message = 'importing', f"Importing your sales history: {p['percent']}% done."
    elif job and job.status == 'failed' and conn.last_error:
        status, message = 'error', 'The last sync failed. Numbers may be out of date.'
    elif stale or not last:
        status, message = 'stale', 'Numbers have not been updated in over 12 hours.'
    else:
        status, message = 'healthy', 'Up to date.'
    orders = db.scalars(select(SquareOrder).where(SquareOrder.workspace_id == wid,
                                                  SquareOrder.status == 'COMPLETED')).all()
    identified = sum(1 for o in orders if o.customer_id)
    gaps = ['Gift card sales and comps are not imported separately.',
            'Service charges are excluded from net sales, as in Square reports.']
    if orders and identified / len(orders) < 0.5:
        gaps.append(f'Only {round(100 * identified / len(orders))}% of orders are linked to a known guest; '
                    'guest figures describe that share only.')
    if any(s.timezone == 'UTC' for s in db.scalars(select(SquareLocationState).where(SquareLocationState.workspace_id == wid))):
        gaps.append('A location has no time zone in Square; its days are counted in UTC.')
    return {**base, 'status': status, 'message': message, 'last_success_at': last, 'backfill': p,
            'job': ({'status': job.status, 'attempts': job.attempts, 'last_error': job.last_error or None}
                    if job else None), 'gaps': gaps}


def reconciliation(db: Session, wid: str, start: date, end: date, location_ids: list[str] | None = None) -> dict:
    """Per location and local day, the figures to compare with Square's Sales Summary."""
    from .connections import SquareOrder
    states = {s.location_id: s for s in db.scalars(select(SquareLocationState).where(SquareLocationState.workspace_id == wid))}
    lo, hi = start.isoformat(), end.isoformat()
    rows: dict[tuple[str, str], dict[str, Any]] = {}

    def row(loc: str, day: str) -> dict:
        return rows.setdefault((loc, day), {'location_id': loc, 'location': states[loc].name if loc in states else loc,
                                            'date': day, 'orders': 0, 'gross_sales_minor': 0, 'discounts_minor': 0,
                                            'refunds_minor': 0, 'net_sales_minor': 0, 'tax_minor': 0, 'tips_minor': 0})
    q = select(SquareOrder).where(SquareOrder.workspace_id == wid, SquareOrder.status == 'COMPLETED',
                                  SquareOrder.local_date >= lo, SquareOrder.local_date <= hi)
    for o in db.scalars(q):
        if location_ids and o.location_id not in location_ids:
            continue
        r = row(o.location_id, o.local_date)
        r['orders'] += 1
        r['gross_sales_minor'] += o.net_sales_minor + o.discount_minor
        r['discounts_minor'] += o.discount_minor
        r['net_sales_minor'] += o.net_sales_minor
        r['tax_minor'] += o.tax_minor
        r['tips_minor'] += o.tip_minor
    for f in db.scalars(select(SquareRefund).where(SquareRefund.workspace_id == wid,
                                                   SquareRefund.local_date >= lo, SquareRefund.local_date <= hi)):
        if location_ids and f.location_id not in location_ids:
            continue
        r = row(f.location_id, f.local_date)
        r['refunds_minor'] += f.amount_minor
        r['net_sales_minor'] -= f.amount_minor
    ordered = sorted(rows.values(), key=lambda r: (r['location'], r['date']))
    keys = ('orders', 'gross_sales_minor', 'discounts_minor', 'refunds_minor', 'net_sales_minor', 'tax_minor', 'tips_minor')
    totals: dict[str, dict] = {}
    for r in ordered:
        t = totals.setdefault(r['location_id'], {'location_id': r['location_id'], 'location': r['location'], **{k: 0 for k in keys}})
        for k in keys:
            t[k] += r[k]
    return {'start': lo, 'end': hi, 'days': ordered, 'totals': list(totals.values()),
            'definitions': {
                'orders': 'Completed orders created that local day.',
                'gross_sales_minor': 'Net sales before discounts (Square: Gross sales).',
                'discounts_minor': 'Order-level discounts (Square: Discounts & comps).',
                'refunds_minor': 'Completed refunds that local day (Square: Returns / Refunds by amount).',
                'net_sales_minor': 'Gross sales − discounts − refunds, excluding tax, tips and service charges (Square: Net sales).',
                'tax_minor': 'Tax on completed orders (Square: Tax).', 'tips_minor': 'Tips on completed orders (Square: Tip).'},
            'how_to_compare': 'In Square Dashboard → Reports → Sales summary, pick the same dates and one location at a time.'}
