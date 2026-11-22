"""Square SANDBOX-only selected locations; not a live merchant entitlement service.

The owner may only select a fresh server-fetched, physically typed ACTIVE location
from their connected Square Sandbox merchant. No browser-supplied price or quantity
is trusted. All code is feature-flagged OFF by default during transition.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base


class SandboxMonitoredLocation(Base):
    __tablename__ = 'sandbox_monitored_locations'
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    selected_at: Mapped[str] = mapped_column(String(48), nullable=False)


def selection_enabled() -> bool:
    return os.getenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0') == '1'


def eligible_location(raw: dict) -> bool:
    # Deliberately conservative. Square type absent/virtual/inactive needs review.
    return (raw.get('status') == 'ACTIVE' and raw.get('type') == 'PHYSICAL'
            and isinstance(raw.get('id'), str) and bool(raw['id'].strip()))


def selected_rows(db: Session, workspace_id: str, merchant_id: str) -> list[SandboxMonitoredLocation]:
    return list(db.scalars(select(SandboxMonitoredLocation).where(
        SandboxMonitoredLocation.workspace_id == workspace_id,
        SandboxMonitoredLocation.merchant_id == merchant_id
    ).order_by(SandboxMonitoredLocation.location_id)).all())


def snapshot(db: Session, workspace_id: str, merchant_id: str) -> dict:
    rows = selected_rows(db, workspace_id, merchant_id)
    ids = [r.location_id for r in rows]
    text = '\n'.join([workspace_id, merchant_id, *ids])
    return {'quantity': len(ids), 'ids': ids,
            'digest': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'verified_at': [r.selected_at for r in rows]}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
