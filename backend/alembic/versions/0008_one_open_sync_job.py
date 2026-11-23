"""At most one queued/running sync job per workspace (prevents two syncs writing the same orders).

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

WHERE = sa.text("status IN ('queued', 'running')")


def upgrade():
    # Close duplicates left by the old race before adding the constraint: keep the newest open job.
    op.execute("""
        UPDATE square_sync_jobs SET status = 'failed', last_error = 'Superseded by another sync.'
        WHERE status IN ('queued', 'running') AND id NOT IN (
            SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY workspace_id ORDER BY created_at DESC) AS n
                            FROM square_sync_jobs WHERE status IN ('queued', 'running')) ranked WHERE n = 1)
    """)
    op.create_index("uq_square_sync_jobs_one_open", "square_sync_jobs", ["workspace_id"], unique=True,
                    sqlite_where=WHERE, postgresql_where=WHERE)


def downgrade():
    op.drop_index("uq_square_sync_jobs_one_open", table_name="square_sync_jobs")
