"""The only code that changes the database schema (docs/MIGRATIONS.md).

Run it once before the API and worker start:   python -m app.migrate
(Docker: the `migrate` service. Hosted: the release / pre-deploy command.)

- Fresh database: Alembic creates everything.
- Database managed by Alembic: upgraded to the latest revision.
- Older database made by the app's former startup create_all(), with no alembic_version: every
  migration checks for existing objects, so running them all from the start completes whatever the
  old code left (tables, columns, the workspace scoping, the one-open-sync-job index) in place,
  keeping the data.
- After upgrading, the database is checked against the models. If anything is still missing (the
  database was changed outside Alembic), it stops and lists it; it never stamps a version it didn't apply.
- Concurrent runs are safe: a PostgreSQL advisory lock or a SQLite lock file serialises them; later
  runs find nothing to do.

The API and worker never create or alter tables. They call wait_until_ready() and start only when
the schema is at the version this code expects.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import logging
import sys
import time
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url

BACKEND = Path(__file__).resolve().parents[1]
LOCK_KEY = 73072026  # PostgreSQL advisory lock id for "TableSignal schema migration"
logger = logging.getLogger('guestlift.migrate')


class SchemaNotReady(RuntimeError):
    """The database schema isn't at the version this code needs."""


def _config():
    from alembic.config import Config
    cfg = Config(str(BACKEND / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND / 'alembic'))
    return cfg


@functools.lru_cache(maxsize=1)
def _script():
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(_config())


def head() -> str:
    return _script().get_current_head()


def _current(conn) -> str | None:
    from alembic.runtime.migration import MigrationContext
    return MigrationContext.configure(conn).get_current_revision()


def missing_schema(engine: Engine) -> list[str]:
    """Tables and columns the models need that the database doesn't have."""
    from . import main as _registers_every_model  # noqa: F401
    from .database import Base
    insp = inspect(engine)
    present = set(insp.get_table_names())
    gaps = []
    for table in Base.metadata.sorted_tables:
        if table.name not in present:
            gaps.append(f'table {table.name}')
            continue
        have = {c['name'] for c in insp.get_columns(table.name)}
        gaps += [f'column {table.name}.{c.name}' for c in table.columns if c.name not in have]
    return gaps


def status(engine: Engine) -> dict:
    """Whether the schema is at the version this code expects (no changes made)."""
    with engine.connect() as conn:
        current = _current(conn)
    expected = head()
    if current == expected:
        return {'ready': True, 'current': current, 'expected': expected, 'reason': 'current'}
    if current is None:
        return {'ready': False, 'current': None, 'expected': expected,
                'reason': 'the database has not been migrated (no schema version recorded)'}
    if not _known(current):
        # A revision this code doesn't know: the database is newer (e.g. during a rollback).
        return {'ready': True, 'current': current, 'expected': expected,
                'reason': f'the database is at {current}, newer than this code ({expected})'}
    return {'ready': False, 'current': current, 'expected': expected,
            'reason': f'the schema is at {current}; this code needs {expected}'}


def _known(revision: str) -> bool:
    try:
        return _script().get_revision(revision) is not None
    except Exception:
        return False


def wait_until_ready(engine: Engine, timeout: float | None = 120.0, interval: float = 1.0,
                     should_continue=lambda: True) -> dict | None:
    """Block until the schema is ready. Returns None if should_continue() turns false first.

    Raises SchemaNotReady after `timeout` seconds (None waits forever) with what to do next.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    last = None
    while True:
        try:
            state = status(engine)
            if state['ready']:
                if state['reason'] != 'current':
                    logger.warning('starting anyway: %s', state['reason'])
                return state
            reason = state['reason']
        except Exception as exc:  # the database itself isn't reachable yet
            reason = f'the database is not reachable yet ({type(exc).__name__})'
        if reason != last:
            logger.info('waiting for the database schema: %s', reason)
            last = reason
        if not should_continue():
            return None
        if deadline is not None and time.monotonic() >= deadline:
            raise SchemaNotReady(f'Database schema is not ready: {reason}. Run `python -m app.migrate` '
                                 '(with Docker, the `migrate` service runs it) and start again.')
        time.sleep(interval)


@contextlib.contextmanager
def _exclusive(engine: Engine):
    """One migration at a time across processes and containers."""
    if engine.dialect.name == 'postgresql':
        with engine.connect() as lock:
            lock.execute(text('SELECT pg_advisory_lock(:k)'), {'k': LOCK_KEY})
            lock.commit()
            try:
                yield
            finally:
                lock.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': LOCK_KEY})
                lock.commit()
        return
    path = make_url(str(engine.url)).database if engine.dialect.name == 'sqlite' else None
    if not path or path == ':memory:':
        yield
        return
    try:
        import fcntl
    except ImportError:  # no flock on this platform; run unlocked
        yield
        return
    with open(f'{path}.migrate.lock', 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _run(engine: Engine, target: str = 'head') -> None:
    from alembic import command
    with engine.begin() as conn:
        cfg = _config()
        cfg.attributes['connection'] = conn
        command.upgrade(cfg, target)


def upgrade(engine: Engine | None = None) -> dict:
    """Bring the schema to the latest revision. Safe to run repeatedly and concurrently.

    Never stamps a version it didn't apply. If the database still lacks something the models need
    afterwards (it was changed outside Alembic), it stops and says exactly what is missing.
    """
    if engine is None:
        from .database import engine
    with _exclusive(engine):
        with engine.connect() as conn:
            before = _current(conn)
            had_tables = bool(set(inspect(conn).get_table_names()) - {'alembic_version'})
        _run(engine)
        gaps = missing_schema(engine)
        if gaps:
            raise SchemaNotReady('Migrations finished but the database still lacks: ' + ', '.join(gaps)
                                 + '. It was changed outside Alembic; restore it or add a migration for these.')
        with engine.connect() as conn:
            after = _current(conn)
    return {'before': before, 'after': after, 'adopted_legacy_schema': before is None and had_tables}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m app.migrate', description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true', help='report whether the schema is current; change nothing')
    args = parser.parse_args(argv)
    from .logging_config import setup_logging
    setup_logging()
    from .database import engine
    target = make_url(str(engine.url)).render_as_string(hide_password=True)
    if args.check:
        state = status(engine)
        print(f"{target}: {'ready' if state['ready'] else 'NOT READY'} ({state['reason']})")
        return 0 if state['ready'] else 1
    started = time.monotonic()
    try:
        result = upgrade(engine)
    except SchemaNotReady as exc:
        print(f'{target}: {exc}', file=sys.stderr)
        return 1
    if result['before'] == result['after']:
        print(f"{target}: schema already current at {result['after']}")
    else:
        how = 'adopted a database created by an older version' if result['adopted_legacy_schema'] else 'upgraded'
        print(f"{target}: {how}: {result['before'] or 'empty'} -> {result['after']} "
              f"({time.monotonic() - started:.1f}s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
