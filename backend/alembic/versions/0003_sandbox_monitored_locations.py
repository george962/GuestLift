"""Add the v0.13 Sandbox monitored-location table.

Revision ID: 0003
Revises: 0002

The migration also supports local databases where development
create_all() created the table before Alembic was introduced.
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLE = "sandbox_monitored_locations"


def upgrade():
    if sa.inspect(op.get_bind()).has_table(TABLE):
        return

    op.create_table(
        TABLE,
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "merchant_id",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "selected_at",
            sa.String(length=48),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["saas_workspaces.id"],
        ),
        sa.PrimaryKeyConstraint(
            "workspace_id",
            "location_id",
        ),
    )


def downgrade():
    if sa.inspect(op.get_bind()).has_table(TABLE):
        op.drop_table(TABLE)
