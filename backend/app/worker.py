"""Background sync worker (docs/PRODUCT_PLAN.md M3). Run: python -m app.worker

- Every GUESTLIFT_SYNC_INTERVAL_HOURS (default 4), queues a sync for each active Square connection.
- Runs due jobs in slices (GUESTLIFT_WORKER_SLICE_SECONDS, default 60), so a long history import
  makes steady progress and several workers can share the queue safely.
- Retries 429s, Square outages and network errors with exponential backoff; stops and asks the
  owner to reconnect when Square rejects the token.
"""
from __future__ import annotations

import logging
import os
import signal
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config, square_sync
from . import main as _main  # noqa: F401  (registers every model, as alembic/env.py does)
from .database import engine, init_db
from .logging_config import setup_logging

logger = logging.getLogger('guestlift.worker')
_running = True


def schedule(db: Session, now: int | None = None) -> int:
    """Queue a scheduled sync for each active connection that has had none recently."""
    from .connections import SquareConnection
    now = now or int(time.time())
    interval = square_sync.sync_interval_seconds()
    queued = 0
    for conn in db.scalars(select(SquareConnection).where(SquareConnection.status == 'active')):
        last = db.scalar(select(square_sync.SquareSyncJob).where(
            square_sync.SquareSyncJob.workspace_id == conn.workspace_id)
            .order_by(square_sync.SquareSyncJob.created_at.desc()).limit(1))
        if last and last.status in ('queued', 'running'):
            continue
        if last and square_sync._parse(last.updated_at).timestamp() > now - interval:
            continue
        from .location_entitlements import selected_rows, selection_enabled
        if selection_enabled() and not selected_rows(db, conn.workspace_id, conn.merchant_id):
            continue  # just connected: wait until the owner picks locations, rather than fail
        from .billing import READ_ONLY, entitlement
        from .saas import Workspace
        workspace = db.get(Workspace, conn.workspace_id)
        if workspace is None or entitlement(workspace)['access'] == READ_ONLY:
            continue  # no new data while the trial has ended or payment has lapsed
        square_sync.enqueue(db, conn.workspace_id, 'scheduled')
        queued += 1
    return queued


_last_insights = 0.0


def run_insights(force: bool = False) -> dict | None:
    """Weekly digests and outcome emails, at most every 10 minutes."""
    global _last_insights
    if not force and time.time() - _last_insights < 600:
        return None
    _last_insights = time.time()
    from .insight_loop import run_due
    with Session(engine) as db:
        try:
            return run_due(db)
        except Exception:  # never let email stop syncing
            logger.exception('weekly brief / outcome run failed')
            return None


def run_once(slice_seconds: float | None = None) -> bool:
    """Schedule, then run at most one due job slice. Returns True if a job ran."""
    slice_seconds = slice_seconds or float(os.getenv('GUESTLIFT_WORKER_SLICE_SECONDS', '60'))
    run_insights()
    with Session(engine) as db:
        schedule(db)
        now = int(time.time())
        due = db.scalars(select(square_sync.SquareSyncJob).where(
            square_sync.SquareSyncJob.status.in_(('queued', 'running')),
            square_sync.SquareSyncJob.run_after <= now,
            square_sync.SquareSyncJob.locked_until < now).order_by(square_sync.SquareSyncJob.run_after).limit(5)).all()
        for job in due:
            if not square_sync.claim(db, job.id):
                continue  # another worker took it
            try:
                result = square_sync.execute(db, db.get(square_sync.SquareSyncJob, job.id), slice_seconds)
                logger.info('sync job %s: %s', job.id, {k: result[k] for k in ('inserted', 'updated', 'refunds', 'complete')})
            except Exception as exc:  # recorded on the job by execute(); keep the worker alive
                logger.warning('sync job %s did not finish: %s', job.id, getattr(exc, 'detail', type(exc).__name__))
            return True
    return False


def main() -> None:
    setup_logging()
    config.validate_auth_config()
    config.validate_production_config()
    from .connections import validate_square_config
    validate_square_config()
    init_db()

    def stop(*_):
        global _running
        _running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    idle = float(os.getenv('GUESTLIFT_WORKER_IDLE_SECONDS', '5'))
    logger.info('worker started')
    while _running:
        if not run_once():
            time.sleep(idle)
    logger.info('worker stopped')


if __name__ == '__main__':
    main()
