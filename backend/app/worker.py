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
        square_sync.enqueue(db, conn.workspace_id, 'scheduled')
        queued += 1
    return queued


def run_once(slice_seconds: float | None = None) -> bool:
    """Schedule, then run at most one due job slice. Returns True if a job ran."""
    slice_seconds = slice_seconds or float(os.getenv('GUESTLIFT_WORKER_SLICE_SECONDS', '60'))
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
