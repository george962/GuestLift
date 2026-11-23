"""Entitlements: who can use what, decided in one place (docs/PRODUCT_PLAN.md M5).

States
- setup         No trial yet. Connect Square and sync; the trial starts after the first complete sync.
- trial         14-day no-card trial (GUESTLIFT_TRIAL_DAYS). Full access.
- trial_expired Trial over and no subscription. Read-only: existing numbers stay visible.
- active        Paid subscription. Full access.
- canceling     Canceled at period end. Full access until then.
- past_due      A payment failed. Full access for a grace period (GUESTLIFT_PAYMENT_GRACE_DAYS, 7).
- read_only     Grace over, unpaid, or canceled. Read-only until payment is fixed or a new subscription starts.

Access
- full      everything
- setup     connect, select locations, sync, view (needed to start the trial)
- read_only view existing data; no syncing, AI analyst or new decisions
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from .local_auth import authenticated_subject

FULL, SETUP, READ_ONLY = 'full', 'setup', 'read_only'


def trial_days() -> int:
    try:
        return max(1, int(os.getenv('GUESTLIFT_TRIAL_DAYS', '14')))
    except ValueError:
        return 14


def grace_days() -> int:
    try:
        return max(0, int(os.getenv('GUESTLIFT_PAYMENT_GRACE_DAYS', '7')))
    except ValueError:
        return 7


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _days_left(until: datetime | None, now: datetime) -> int | None:
    return None if until is None else max(0, -(-int((until - now).total_seconds()) // 86400))


def entitlement(w, now: datetime | None = None) -> dict:
    """The single answer to 'what can this workspace do right now, and why'."""
    now = now or datetime.now(timezone.utc)
    status = w.subscription_status or 'none'
    period_end = datetime.fromtimestamp(w.current_period_end, timezone.utc) if w.current_period_end else None
    subscribed = bool(w.stripe_subscription_id) and status not in ('none', 'incomplete')
    if subscribed and status in ('active', 'trialing'):
        if w.cancel_at_period_end:
            return _result('canceling', FULL, period_end, now,
                           f"Your subscription ends on {period_end:%b %d}." if period_end else 'Your subscription is set to end.')
        return _result('active', FULL, period_end, now, 'Subscription active.')
    if subscribed and status == 'past_due':
        failed = _dt(w.payment_failed_at) or now
        grace_end = failed + timedelta(days=grace_days())
        if now < grace_end:
            return _result('past_due', FULL, grace_end, now,
                           f"A payment failed. Update your card by {grace_end:%b %d} to keep full access.")
        return _result('read_only', READ_ONLY, None, now, 'A payment failed. Update your card to resume updates and the analyst.')
    if subscribed:  # unpaid, canceled, incomplete_expired, paused
        return _result('read_only', READ_ONLY, None, now,
                       'Your subscription has ended. Your numbers stay visible; subscribe to resume updates.')
    trial_end = _dt(w.trial_ends_at)
    if trial_end is None:
        return _result('setup', SETUP, None, now, f'Connect Square and sync to start your {trial_days()}-day free trial.')
    if now < trial_end:
        return _result('trial', FULL, trial_end, now, f"Free trial: ends {trial_end:%b %d}. No card needed until then.")
    return _result('trial_expired', READ_ONLY, None, now,
                   'Your free trial has ended. Your numbers stay visible; subscribe to resume updates and the analyst.')


def _result(state: str, access: str, until: datetime | None, now: datetime, message: str) -> dict:
    return {'state': state, 'access': access, 'until': until.isoformat() if until else None,
            'days_left': _days_left(until, now), 'message': message}


def start_trial_if_eligible(db: Session, workspace_id: str, now: datetime | None = None) -> bool:
    """Called after a complete sync. Starts the one-time no-card trial."""
    from .saas import Workspace
    w = db.get(Workspace, workspace_id)
    if w is None or w.trial_started_at or w.stripe_subscription_id:
        return False
    now = now or datetime.now(timezone.utc)
    w.trial_started_at = now.isoformat()
    w.trial_ends_at = (now + timedelta(days=trial_days())).isoformat()
    db.commit()
    return True


def _require(levels: tuple[str, ...], what: str):
    def dependency(sub: str = Depends(authenticated_subject)) -> str:
        from . import saas  # workspaces live with the SaaS module; use its engine
        with Session(saas.engine) as db:
            e = entitlement(saas._get_workspace(db, sub))
        if e['access'] not in levels:
            raise HTTPException(402, f"{e['message']} ({what} needs an active trial or subscription.)",
                                headers={'X-Entitlement-State': e['state']})
        return sub
    return dependency


# Every paid route depends on exactly one of these; tests/test_billing_m5.py lists them.
paid_subject = _require((FULL,), 'This feature')
sync_subject = _require((FULL, SETUP), 'Syncing new data')
