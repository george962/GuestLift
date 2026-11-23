"""Transactional email: weekly digest and decision outcomes (docs/PRODUCT_PLAN.md M4).

Sends through Resend when RESEND_API_KEY and EMAIL_FROM are set. Otherwise each message is
recorded in `email_outbox` with status `not_sent` so it can be previewed and nothing is lost.
Every message has a one-click unsubscribe link (signed, no login needed).
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import config
from .database import Base


class EmailOutbox(Base):
    __tablename__ = 'email_outbox'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # weekly_digest | outcome
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    to_address: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    html_body: Mapped[str] = mapped_column(Text)
    text_body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))  # sent | not_sent | failed
    provider_id: Mapped[str] = mapped_column(String(120), default='')
    created_at: Mapped[str] = mapped_column(String(48))


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
    return (member_id, kind) if kind in ('weekly_digest', 'outcome') and hmac.compare_digest(sig, good) else None


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
    return subject, _shell(f'Your free trial ends {when}', body, unsubscribe, 'You get this once, near the end of your trial.'), text


def send(db: Session, workspace_id: str, kind: str, dedupe_key: str, to: str, subject: str, html_body: str, text: str) -> str:
    """Send once per dedupe_key. Returns the outbox status."""
    from sqlalchemy import select
    existing = db.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key))
    if existing and existing.status != 'failed':
        return existing.status
    if existing:  # a failed attempt is retried on the next run
        db.delete(existing)
        db.flush()
    row = EmailOutbox(id=str(uuid.uuid4()), workspace_id=workspace_id, kind=kind, dedupe_key=dedupe_key, to_address=to,
                      subject=subject, html_body=html_body, text_body=text, status='not_sent',
                      created_at=datetime.now(timezone.utc).isoformat())
    key, sender = os.getenv('RESEND_API_KEY', ''), os.getenv('EMAIL_FROM', '')
    if key and sender:
        try:
            r = httpx.post('https://api.resend.com/emails', timeout=15, headers={'Authorization': f'Bearer {key}'},
                           json={'from': sender, 'to': [to], 'subject': subject, 'html': html_body, 'text': text})
            if r.status_code < 300:
                row.status, row.provider_id = 'sent', str(r.json().get('id', ''))[:120]
            else:
                row.status = 'failed'
        except httpx.HTTPError:
            row.status = 'failed'
    db.add(row)
    db.commit()
    return row.status
