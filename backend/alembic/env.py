"""Alembic environment. The database URL comes from DATABASE_URL (see app.database)."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import main  # noqa: F401  (imports every router so all models register on Base)
from app.database import DATABASE_URL, Base

config = context.config
# When the app upgrades a legacy local database at startup it hands us its own
# connection; don't reconfigure the app's logging in that case.
_attached_connection = config.attributes.get('connection')
if config.config_file_name is not None and _attached_connection is None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
config.set_main_option('sqlalchemy.url', DATABASE_URL.replace('%', '%%'))


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={'paramstyle': 'named'})
    with context.begin_transaction():
        context.run_migrations()


# Managed outside the metadata (partial unique index; see app/square_sync.py and migration 0008).
UNMANAGED_INDEXES = {'uq_square_sync_jobs_one_open'}


def include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == 'index' and name in UNMANAGED_INDEXES)


def run_migrations_online() -> None:
    if _attached_connection is not None:
        context.configure(connection=_attached_connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix='sqlalchemy.', poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
