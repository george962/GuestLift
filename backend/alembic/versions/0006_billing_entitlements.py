"""Billing state for entitlements: no-card trial, period end, cancel-at-period-end, failed payment.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("trial_started_at", sa.String(length=40), nullable=True),
    sa.Column("trial_ends_at", sa.String(length=40), nullable=True),
    sa.Column("current_period_end", sa.Integer(), nullable=True),
    sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("payment_failed_at", sa.String(length=40), nullable=True),
]


def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("saas_workspaces")}
    with op.batch_alter_table("saas_workspaces") as batch:
        for column in COLUMNS:
            if column.name not in existing:
                batch.add_column(column.copy())


def downgrade():
    with op.batch_alter_table("saas_workspaces") as batch:
        for column in reversed(COLUMNS):
            batch.drop_column(column.name)
