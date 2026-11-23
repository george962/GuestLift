"""M6 readiness endpoints: scoped data export, support requests, and minimal product telemetry.

Only Square Sandbox data is exported. No client-submitted IDs, arbitrary event text, user
content, IP addresses, or email addresses enter product telemetry. The owner explicitly
requests the ZIP; no exports are sent to third parties automatically.
"""
from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, String, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import saas
from .database import Base
from .local_auth import authenticated_subject
from .membership import owner_subject

router = APIRouter(prefix='/api/readiness', tags=['M6 customer readiness'])
PREVIEW_VERSION = 'sandbox-preview-2026-11'
EVENTS = {'weekly_brief_view', 'first_insight_view', 'outcome_view', 'client_error'}
CATEGORIES = {'connection', 'billing', 'data_quality', 'account', 'other'}


class WorkspaceProductSignal(Base):
    __tablename__ = 'workspace_product_signals'
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), primary_key=True)
    signal: Mapped[str] = mapped_column(String(36), primary_key=True)
    period: Mapped[str] = mapped_column(String(10), primary_key=True)
    observed_at: Mapped[str] = mapped_column(String(48), nullable=False)


class WorkspacePreviewAck(Base):
    __tablename__ = 'workspace_preview_ack'
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), primary_key=True)
    version: Mapped[str] = mapped_column(String(48), nullable=False)
    acknowledged_at: Mapped[str] = mapped_column(String(48), nullable=False)


class SupportTicket(Base):
    __tablename__ = 'workspace_support_tickets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(36), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[str] = mapped_column(String(48), nullable=False)


class SignalPayload(BaseModel):
    event: str = Field(min_length=1, max_length=36)


class AckPayload(BaseModel):
    version: str
    acknowledged: bool


class SupportPayload(BaseModel):
    category: str = Field(min_length=1, max_length=36)
    description: str = Field(min_length=12, max_length=500)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _date() -> str:
    return _now().date().isoformat()


def _week() -> str:
    today = _now().date()
    return (today - timedelta(days=today.weekday())).isoformat()


@router.get('/preview')
def preview(sub: str = Depends(authenticated_subject)):
    with Session(saas.engine) as db:
        w = saas._get_workspace(db, sub)
        row = db.get(WorkspacePreviewAck, w.id)
        return {'version': PREVIEW_VERSION,
                'acknowledged': bool(row and row.version == PREVIEW_VERSION)}


@router.post('/preview')
def accept_preview(payload: AckPayload, sub: str = Depends(authenticated_subject)):
    if not payload.acknowledged or payload.version != PREVIEW_VERSION:
        raise HTTPException(422, 'Acknowledge the current developer-preview notice to continue.')
    with Session(saas.engine) as db:
        w = saas._get_workspace(db, sub)
        row = db.get(WorkspacePreviewAck, w.id)
        if row is None:
            row = WorkspacePreviewAck(workspace_id=w.id, version=PREVIEW_VERSION,
                                     acknowledged_at=_now().isoformat())
            db.add(row)
        elif row.version != PREVIEW_VERSION:
            row.version, row.acknowledged_at = PREVIEW_VERSION, _now().isoformat()
        db.commit()
    return {'acknowledged': True, 'version': PREVIEW_VERSION,
            'notice': 'Developer-preview acknowledgement recorded. Legal terms remain draft.'}


@router.post('/support', status_code=201)
def support(payload: SupportPayload, sub: str = Depends(authenticated_subject)):
    if payload.category not in CATEGORIES or not payload.description.strip():
        raise HTTPException(422, 'Choose a category and describe the problem.')
    if any(ord(c) < 32 and c not in '\n\t' for c in payload.description):
        raise HTTPException(422, 'Remove control characters from the request.')
    with Session(saas.engine) as db:
        w = saas._get_workspace(db, sub)
        today = _date()
        sent_today = db.scalar(select(func.count()).select_from(SupportTicket).where(
            SupportTicket.workspace_id == w.id, SupportTicket.created_at >= today))
        if sent_today >= 3:
            raise HTTPException(429, 'Three support requests per workspace per day is the limit.')
        item = SupportTicket(id=str(uuid.uuid4()), workspace_id=w.id,
                             category=payload.category, description=payload.description.strip(),
                             status='requested', created_at=_now().isoformat())
        db.add(item)
        db.commit()
        return {'request_id': item.id, 'status': 'requested',
                'notice': 'Request stored for developer review. No email or automatic reply was sent.'}


@router.post('/event')
def event(payload: SignalPayload, sub: str = Depends(authenticated_subject)):
    if payload.event not in EVENTS:
        raise HTTPException(422, 'Unsupported telemetry event.')
    with Session(saas.engine) as db:
        w = saas._get_workspace(db, sub)
        period = _week()
        if payload.event in {'weekly_brief_view', 'first_insight_view'}:
            from .insight_loop import brief_for
            brief = brief_for(db, w.id)
            if brief.get('data_status') != 'ready' or not brief.get('has_data'):
                raise HTTPException(409, 'Only a verified weekly brief counts as an insight view.')
            period = brief['week_start'] if payload.event == 'weekly_brief_view' else 'first'
        elif payload.event == 'outcome_view':
            from .decisions import DecisionPlan
            has_outcome = db.scalar(select(DecisionPlan.id).where(
                DecisionPlan.workspace_id == w.id, DecisionPlan.outcome.is_not(None)).limit(1))
            if not has_outcome:
                raise HTTPException(409, 'No completed decision outcome available to view.')
        key = (w.id, payload.event, period)
        created = db.get(WorkspaceProductSignal, key) is None
        if created:
            db.add(WorkspaceProductSignal(workspace_id=w.id, signal=payload.event,
                                          period=period, observed_at=_now().isoformat()))
            db.commit()
        return {'recorded': created, 'event': payload.event}


def _safe_csv(value):
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        return value
    value = str(value)
    # Protect spreadsheet readers from formula injection in provider-supplied strings.
    if value and (value[0] in '=+@\t\r' or (value[0] == '-' and not value[1:].isdigit())):
        return "'" + value
    return value


def _csv(rows, columns):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_safe_csv(getattr(row, field)) for field in columns])
    return out.getvalue().encode('utf-8-sig')


@router.get('/export')
def export_data(sub: str = Depends(owner_subject)):
    """Owner-only, workspace-scoped data portability ZIP; never includes OAuth tokens."""
    from .connections import SquareOrder
    from .square_sync import SquareRefund
    from .decisions import DecisionPlan
    from .location_entitlements import SandboxMonitoredLocation

    sources = (
        ('square_orders.csv', SquareOrder,
         ['source_order_id', 'location_id', 'created_at', 'updated_at', 'local_date',
          'status', 'currency', 'customer_id', 'net_sales_minor', 'discount_minor',
          'tax_minor', 'tip_minor', 'service_charge_minor']),
        ('square_refunds.csv', SquareRefund,
         ['source_refund_id', 'order_id', 'location_id', 'created_at', 'local_date', 'amount_minor', 'status']),
        ('saved_decisions.csv', DecisionPlan,
         ['id', 'title', 'status', 'metric', 'location_id', 'start_date', 'follow_up_date',
          'notes', 'outcome', 'outcome_at', 'created_at']),
        ('monitored_locations.csv', SandboxMonitoredLocation,
         ['location_id', 'merchant_id', 'name', 'selected_at']),
        ('support_requests.csv', SupportTicket,
         ['id', 'category', 'description', 'status', 'created_at']),
    )
    with Session(saas.engine) as db:
        workspace = saas._get_workspace(db, sub)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('README.txt',
                'TableSignal Square Sandbox workspace export. Do not share with third parties; '
                'guest IDs and business notes may be sensitive. Amounts use currency minor units. '
                'Refunds count on the date they occurred. This is not an audited sales report.\n')
            for name, model, columns in sources:
                rows = db.scalars(select(model).where(model.workspace_id == workspace.id)).all()
                archive.writestr(name, _csv(rows, columns))
        return Response(content=payload.getvalue(), media_type='application/zip',
                        headers={'Content-Disposition':'attachment; filename="tablesignal-workspace-export.zip"',
                                 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'})
