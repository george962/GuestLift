"""Transactional email: weekly digest, decision outcomes and trial reminders (docs/PRODUCT_PLAN.md M4).

Every message goes through the `email_outbox` table:

1. `enqueue()` records the rendered message once per dedupe key (the unique constraint means two
   workers can't both claim the same message). Nothing is sent yet.
2. `deliver_pending()` (each worker pass) sends whatever is still `pending`, through Resend when
   RESEND_API_KEY and EMAIL_FROM are set. Without them messages wait, so they go out once the
   provider is configured, as long as they're still within their delivery window.

Sending is idempotent: each row is sent with a Resend `Idempotency-Key` derived from its id, so a
retry after a timeout or a worker restart can't deliver a second copy (Resend keeps keys 24h).
Before each attempt the recipient's current preferences are checked again, so unsubscribing
stops messages that were already queued. Every message has a signed one-click unsubscribe link.

Statuses: pending (legacy rows: not_sent) -> sent | failed | expired | skipped.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import ForeignKey, String, Text, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import config
from .database import Base

logger = logging.getLogger('guestlift.email')

class EmailOutbox(Base):
    __tablename__ = 'email_outbox'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # weekly_digest | outcome | trial_ending
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    to_address: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    html_body: Mapped[str] = mapped_column(Text)
    text_body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))  # see STATUSES
    provider_id: Mapped[str] = mapped_column(String(120), default='')
    created_at: Mapped[str] = mapped_column(String(48))


# The member preference (a WorkspaceMember column) that controls each kind of email. Trial reminders
# share `outcome_emails`, the owner-notices switch: their unsubscribe links have always turned that
# off, so links already in inboxes keep working. Splitting it out needs a migration, see
# docs/EMAIL_OUTBOX_MIGRATION.md.
PREFERENCE = {'weekly_digest': 'weekly_digest', 'outcome': 'outcome_emails', 'trial_ending': 'outcome_emails'}


def _secret() -> bytes:
    return (os.getenv('GUESTLIFT_EMAIL_SECRET') or os.getenv('TABLESIGNAL_CREDENTIAL_KEY') or 'dev-only-email-secret').encode()


def unsubscribe_token(member_id: str, kind: str) -> str:
    sig = hmac.new(_secret(), f'{member_id}:{kind}'.encode(), hashlib.sha256).hexdigest()[:32]
    return f'{member_id}.{kind}.{sig}'


def verify_unsubscribe(token: str) -> tuple[str, str] | None:
    try:
        member_id, kind, sig = token.split('.')
    except ValueError:
        return None
    good = unsubscribe_token(member_id, kind).split('.')[2]
    return (member_id, kind) if kind in PREFERENCE and hmac.compare_digest(sig, good) else None


def unsubscribe_url(member_id: str, kind: str) -> str:
    base = os.getenv('GUESTLIFT_API_URL', '').rstrip('/') or config.app_url().replace(':3000', ':8000')
    return f'{base}/api/email/unsubscribe?token={unsubscribe_token(member_id, kind)}'


def _money(minor: float) -> str:
    return f'${minor / 100:,.0f}'


def _shell(title: str, body_html: str, unsubscribe: str, reason: str) -> str:
    e = html.escape
    return f"""<!doctype html><html><body style="margin:0;background:#f3f6f5;font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#14201d">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" style="max-width:600px;background:#ffffff;border:1px solid #dfe6e3;border-radius:12px">
<tr><td style="padding:24px 24px 8px"><div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#5b6b66">TableSignal</div>
<h1 style="font-size:22px;line-height:1.3;margin:8px 0 0">{e(title)}</h1></td></tr>
<tr><td style="padding:8px 24px 24px;font-size:15px;line-height:1.55">{body_html}</td></tr>
<tr><td style="padding:16px 24px;border-top:1px solid #dfe6e3;font-size:12px;color:#5b6b66">{e(reason)}
<a href="{e(unsubscribe)}" style="color:#0f6b5c">Unsubscribe</a> · <a href="{e(config.app_url())}/settings" style="color:#0f6b5c">Email settings</a></td></tr>
</table></td></tr></table></body></html>"""


def render_weekly(brief: dict, workspace_name: str, unsubscribe: str) -> tuple[str, str, str]:
    e = html.escape
    subject = f"{workspace_name}: {brief['headline']}"[:200]
    totals = (brief.get('totals') or {}).get('this_week') or {}
    rows = ''.join(
        f"<tr><td style='padding:10px 0;border-top:1px solid #dfe6e3'><b>{e(f['title'])}</b>"
        f"<span style='font-size:12px;color:#5b6b66'> · {'clear change' if f['confidence'] == 'clear' else 'possible change'}</span>"
        f"<br>{e(f['detail'])}</td></tr>" for f in brief['findings'])
    body = (f"<p style='margin:0 0 12px;color:#5b6b66'>Week of {e(brief['week_start'])} to {e(brief['week_end'])}</p>"
            f"<p style='margin:0 0 16px'>Net sales {_money(totals.get('net_sales', 0))} · {totals.get('orders', 0):,} orders</p>"
            f"<table role='presentation' width='100%'>{rows or '<tr><td>Nothing changed more than usual. That is useful to know too.</td></tr>'}</table>"
            + ''.join(f"<p style='font-size:13px;color:#5b6b66'>{e(c)}</p>" for c in brief.get('caveats', []))
            + f"<p style='font-size:13px;color:#5b6b66'>{e(brief['method'])}</p>"
            f"<p><a href='{e(config.app_url())}/analyst' style='color:#0f6b5c;font-weight:600'>Open this week's brief</a></p>")
    text = '\n'.join([brief['headline'], f"Week of {brief['week_start']} to {brief['week_end']}", ''] +
                     [f"- {f['title']} ({f['confidence']}): {f['detail']}" for f in brief['findings']] +
                     ['', *brief.get('caveats', []), brief['method'], '', f'Unsubscribe: {unsubscribe}'])
    return subject, _shell(brief['headline'], body, unsubscribe, 'You get this weekly because you are on this workspace.'), text


def render_outcome(plan: dict, result: dict, workspace_name: str, unsubscribe: str) -> tuple[str, str, str]:
    e = html.escape
    subject = f"{workspace_name}: how “{plan['title']}” turned out"[:200]
    body = (f"<p style='margin:0 0 12px'><b>{e(result['headline'])}</b></p><p>{e(result['explanation'])}</p>"
            f"<p><a href='{e(config.app_url())}/experiments' style='color:#0f6b5c;font-weight:600'>See the readout and decide what's next</a></p>")
    text = f"{result['headline']}\n\n{result['explanation']}\n\nUnsubscribe: {unsubscribe}"
    return subject, _shell(f"How “{plan['title']}” turned out", body, unsubscribe, 'You get this when a decision reaches its follow-up date.'), text


def render_trial_ending(days_left: int, workspace_name: str, unsubscribe: str) -> tuple[str, str, str]:
    e = html.escape
    when = 'tomorrow' if days_left <= 1 else f'in {days_left} days'
    subject = f'{workspace_name}: your free trial ends {when}'
    body = (f"<p>Your TableSignal trial ends {e(when)}. After that, your numbers stay visible, but syncing, the weekly brief "
            "and the analyst pause until you subscribe.</p>"
            f"<p><a href='{e(config.app_url())}/billing' style='color:#0f6b5c;font-weight:600'>Choose a plan</a></p>")
    text = f"Your TableSignal trial ends {when}. Subscribe at {config.app_url()}/billing\n\nUnsubscribe: {unsubscribe}"
    return subject, _shell(f'Your free trial ends {when}', body, unsubscribe,
                           'You get this near the end of your trial. Unsubscribing also stops decision outcome emails.'), text




# ---- Outbox: record once, deliver (and retry) from the worker -------------------------------------

PENDING, SENT, FAILED, EXPIRED, SKIPPED = 'pending', 'sent', 'failed', 'expired', 'skipped'
STATUSES = (PENDING, SENT, FAILED, EXPIRED, SKIPPED)
WAITING = (PENDING, 'not_sent')  # rows recorded before retries existed say not_sent; they are pending
# How long a message stays worth sending. A Monday brief delivered on Friday is stale, and a
# "trial ends in 3 days" reminder is wrong a day later.
DELIVERY_WINDOW = {'weekly_digest': timedelta(days=3), 'outcome': timedelta(days=14), 'trial_ending': timedelta(hours=24)}
DEFAULT_WINDOW = timedelta(days=3)
RESEND_URL = 'https://api.resend.com/emails'


# Dedupe keys name the message and its recipient. The outbox has no member column, so delivery reads
# the recipient back from the key (_recipient_member_id); keep the two in step.
def digest_key(member_id: str, week_start: str) -> str:
    return f'digest:{member_id}:{week_start}'


def outcome_key(plan_id: str, member_id: str) -> str:
    return f'outcome:{plan_id}:{member_id}'


def trial_key(workspace_id: str, member_id: str, days_left: int) -> str:
    return f'trial:{workspace_id}:{member_id}:{days_left}'


def legacy_trial_key(workspace_id: str, days_left: int) -> str:
    """Before trial reminders were keyed per recipient: one key per workspace, so a second owner never got one."""
    return f'trial:{workspace_id}:{days_left}'


def _recipient_member_id(row: EmailOutbox) -> str | None:
    parts = row.dedupe_key.split(':')
    if row.kind == 'weekly_digest' and len(parts) == 3:
        return parts[1]
    if row.kind == 'outcome' and len(parts) == 3:
        return parts[2]
    if row.kind == 'trial_ending' and len(parts) == 4:
        return parts[2]
    return None


def provider_configured() -> bool:
    return bool(os.getenv('RESEND_API_KEY') and os.getenv('EMAIL_FROM'))


def idempotency_key(row: EmailOutbox) -> str:
    """Stable for the row's lifetime, so every retry of one message is the same request to Resend."""
    return f'tablesignal-email/{row.id}'


def already_recorded(db: Session, dedupe_key: str, to: str | None = None) -> bool:
    q = select(EmailOutbox.id).where(EmailOutbox.dedupe_key == dedupe_key)
    if to is not None:
        q = q.where(func.lower(EmailOutbox.to_address) == to.lower())
    return db.scalar(q) is not None


def enqueue(db: Session, workspace_id: str, kind: str, dedupe_key: str, to: str, subject: str, html_body: str,
            text: str, now: datetime | None = None) -> bool:
    """Record a message for delivery, once per dedupe key. False if it was already recorded.

    Committed before any send is attempted: the unique dedupe key is the claim, so two workers
    (or a restarted one) can't both decide to send the same message.
    """
    if already_recorded(db, dedupe_key):
        return False
    db.add(EmailOutbox(id=str(uuid.uuid4()), workspace_id=workspace_id, kind=kind, dedupe_key=dedupe_key, to_address=to,
                       subject=subject, html_body=html_body, text_body=text, status=PENDING, provider_id='',
                       created_at=(now or datetime.now(timezone.utc)).isoformat()))
    try:
        db.commit()
    except IntegrityError:  # another worker recorded it first
        db.rollback()
        return False
    return True


def _parse(ts: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _recipient(db: Session, row: EmailOutbox):
    from .membership import WorkspaceMember
    member_id = _recipient_member_id(row)
    if member_id:
        member = db.get(WorkspaceMember, member_id)
        return member if member and member.workspace_id == row.workspace_id else None
    return db.scalar(select(WorkspaceMember).where(  # legacy trial key: find the owner it was addressed to
        WorkspaceMember.workspace_id == row.workspace_id,
        func.lower(WorkspaceMember.email) == row.to_address.lower()).limit(1))


def _not_deliverable(db: Session, row: EmailOutbox, now: datetime) -> str | None:
    """EXPIRED or SKIPPED when the message should no longer go out; None when it should."""
    created = _parse(row.created_at)
    if created is None or now - created > DELIVERY_WINDOW.get(row.kind, DEFAULT_WINDOW):
        return EXPIRED
    member = _recipient(db, row)
    if member is None:  # no longer on this workspace
        return SKIPPED
    preference = PREFERENCE.get(row.kind)
    if preference and not getattr(member, preference):
        return SKIPPED  # unsubscribed after the message was queued
    if row.kind == 'trial_ending':
        from .billing import entitlement
        from .saas import Workspace
        workspace = db.get(Workspace, row.workspace_id)
        if workspace is None or entitlement(workspace, now)['state'] != 'trial':
            return SKIPPED  # subscribed (or the trial already ended): the reminder is no longer true
    return None


def _client() -> httpx.Client:
    return httpx.Client(timeout=10)


def _send_interval() -> float:
    """Pause between sends; Resend allows 10 requests per second per team by default."""
    try:
        return max(0.0, float(os.getenv('GUESTLIFT_EMAIL_SEND_INTERVAL_SECONDS', '0.15')))
    except ValueError:
        return 0.15


def _attempt(client: httpx.Client, row: EmailOutbox, key: str, sender: str) -> tuple[str, str, bool]:
    """One send through Resend: (status, provider id, stop this pass).

    PENDING means try again on a later pass. Only a rejection of this message itself is FAILED;
    a bad key, an unverified domain, rate limits and outages leave everything pending.
    """
    payload = {'from': sender, 'to': [row.to_address], 'subject': row.subject, 'html': row.html_body, 'text': row.text_body}
    try:
        r = client.post(RESEND_URL, json=payload,
                        headers={'Authorization': f'Bearer {key}', 'Idempotency-Key': idempotency_key(row)})
    except httpx.HTTPError as exc:  # includes timeouts: Resend may have accepted it; the key makes a retry safe
        logger.warning('email %s: provider unreachable (%s); will retry', row.id, type(exc).__name__)
        return PENDING, '', True
    try:
        body = r.json()
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {}
    if r.status_code < 300:
        return SENT, str(body.get('id', ''))[:120], False
    error = str(body.get('name') or body.get('type') or '')
    if r.status_code == 409 and error == 'concurrent_idempotent_requests':
        return PENDING, '', False  # the same message is mid-send elsewhere
    if r.status_code in (400, 409, 422):
        # This message was rejected (bad address, or its key was already used for different content).
        logger.warning('email %s rejected by provider: %s %s', row.id, r.status_code, error)
        return FAILED, '', False
    logger.warning('email delivery paused: provider returned %s %s', r.status_code, error)
    return PENDING, '', True


def deliver_pending(db: Session, now: datetime | None = None, limit: int = 200) -> dict:
    """Send (or retry) everything pending, oldest first. Returns this pass's counts plus what's still pending."""
    now = now or datetime.now(timezone.utc)
    report = {SENT: 0, FAILED: 0, EXPIRED: 0, SKIPPED: 0}
    key, sender = os.getenv('RESEND_API_KEY', ''), os.getenv('EMAIL_FROM', '')
    client = _client() if key and sender else None
    ids = db.scalars(select(EmailOutbox.id).where(EmailOutbox.status.in_(WAITING))
                     .order_by(EmailOutbox.created_at).limit(limit)).all()
    attempts = 0
    try:
        for row_id in ids:
            # Hold the row while sending it. Postgres skips rows another worker holds; SQLite ignores
            # this, and the idempotency key still stops a second copy.
            row = db.scalar(select(EmailOutbox).where(EmailOutbox.id == row_id, EmailOutbox.status.in_(WAITING))
                            .with_for_update(skip_locked=True))
            if row is None:  # finished or held by another worker
                db.commit()
                continue
            status, provider_id, stop = _not_deliverable(db, row, now), '', False
            if status is None and client is not None:
                if attempts:
                    time.sleep(_send_interval())
                attempts += 1
                status, provider_id, stop = _attempt(client, row, key, sender)
            if status and status != PENDING:
                row.status, row.provider_id = status, provider_id
                report[status] += 1
            db.commit()
            if stop:
                break
    finally:
        if client is not None:
            client.close()
    report[PENDING] = db.scalar(select(func.count()).select_from(EmailOutbox)
                                .where(EmailOutbox.status.in_(WAITING))) or 0
    return report


def outbox_counts(db: Session, workspace_id: str | None = None) -> dict:
    """Messages by status. Each row counts once; legacy not_sent rows count as pending, never as sent."""
    q = select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)
    if workspace_id:
        q = q.where(EmailOutbox.workspace_id == workspace_id)
    counts = dict.fromkeys(STATUSES, 0)
    for status, n in db.execute(q):
        bucket = PENDING if status in WAITING else status if status in counts else FAILED
        counts[bucket] += n
    return counts
