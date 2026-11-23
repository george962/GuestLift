"""At most one queued/running sync job per workspace (prevents two syncs writing the same orders).

Idempotent, like every revision here: databases whose index already exists (made by the former
startup create_all() or its after_create hook) are left as they are.

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

INDEX = "uq_square_sync_jobs_one_open"
WHERE = sa.text("status IN ('queued', 'running')")


def _has_index() -> bool:
    return any(i["name"] == INDEX for i in sa.inspect(op.get_bind()).get_indexes("square_sync_jobs"))


def upgrade():
    # Close duplicates left by the old race before adding the constraint: keep the newest open job.
    op.execute("""
        UPDATE square_sync_jobs SET status = 'failed', last_error = 'Superseded by another sync.'
        WHERE status IN ('queued', 'running') AND id NOT IN (
            SELECT id FROM (SELECT id, ROW_NUMBER() OVER (
                                PARTITION BY workspace_id ORDER BY created_at DESC, id DESC) AS n
                            FROM square_sync_jobs WHERE status IN ('queued', 'running')) ranked WHERE n = 1)
    """)
    if not _has_index():
        op.create_index(INDEX, "square_sync_jobs", ["workspace_id"], unique=True,
                        sqlite_where=WHERE, postgresql_where=WHERE)


def downgrade():
    if _has_index():
        op.drop_index(INDEX, table_name="square_sync_jobs")
