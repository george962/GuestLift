"""Checkpointed Square sync: location state, refunds, job queue; order local dates and service charges;
connection status and environment.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _has_column(table, column):
    return column in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("square_location_state"):
        op.create_table(
            "square_location_state",
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), primary_key=True),
            sa.Column("location_id", sa.String(length=160), primary_key=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False),
            sa.Column("backfill_start", sa.String(length=32), nullable=False),
            sa.Column("synced_through", sa.String(length=32), nullable=True),
            sa.Column("backfill_complete", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.String(length=48), nullable=False),
        )
    if not inspector.has_table("square_refunds"):
        op.create_table(
            "square_refunds",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("source_refund_id", sa.String(length=160), nullable=False),
            sa.Column("order_id", sa.String(length=160), nullable=True),
            sa.Column("location_id", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.String(length=55), nullable=False),
            sa.Column("local_date", sa.String(length=10), nullable=False),
            sa.Column("amount_minor", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.UniqueConstraint("workspace_id", "source_refund_id", name="uq_square_refund_owner"),
        )
        op.create_index("ix_square_refunds_workspace_id", "square_refunds", ["workspace_id"])
        op.create_index("ix_square_refunds_local_date", "square_refunds", ["local_date"])
    if not inspector.has_table("square_sync_jobs"):
        op.create_table(
            "square_sync_jobs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("run_after", sa.Integer(), nullable=False),
            sa.Column("locked_until", sa.Integer(), nullable=False),
            sa.Column("progress", sa.Text(), nullable=False),
            sa.Column("last_error", sa.String(length=220), nullable=False),
            sa.Column("created_at", sa.String(length=48), nullable=False),
            sa.Column("updated_at", sa.String(length=48), nullable=False),
        )
        op.create_index("ix_square_sync_jobs_workspace_id", "square_sync_jobs", ["workspace_id"])
        op.create_index("ix_square_sync_jobs_status", "square_sync_jobs", ["status"])
        op.create_index("ix_square_sync_jobs_run_after", "square_sync_jobs", ["run_after"])
    with op.batch_alter_table("square_sandbox_orders") as batch:
        if not _has_column("square_sandbox_orders", "service_charge_minor"):
            batch.add_column(sa.Column("service_charge_minor", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column("square_sandbox_orders", "local_date"):
            batch.add_column(sa.Column("local_date", sa.String(length=10), nullable=True))
    if "ix_square_sandbox_orders_local_date" not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("square_sandbox_orders")}:
        op.create_index("ix_square_sandbox_orders_local_date", "square_sandbox_orders", ["local_date"])
    with op.batch_alter_table("square_sandbox_connections") as batch:
        if not _has_column("square_sandbox_connections", "status"):
            batch.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
        if not _has_column("square_sandbox_connections", "environment"):
            batch.add_column(sa.Column("environment", sa.String(length=12), nullable=False, server_default="sandbox"))
    # Orders imported before local dates existed fall back to their UTC date until the next sync rewrites them.
    op.execute("UPDATE square_sandbox_orders SET local_date = substr(created_at, 1, 10) WHERE local_date IS NULL")


def downgrade():
    with op.batch_alter_table("square_sandbox_connections") as batch:
        batch.drop_column("environment")
        batch.drop_column("status")
    op.drop_index("ix_square_sandbox_orders_local_date", table_name="square_sandbox_orders")
    with op.batch_alter_table("square_sandbox_orders") as batch:
        batch.drop_column("local_date")
        batch.drop_column("service_charge_minor")
    op.drop_index("ix_square_sync_jobs_run_after", table_name="square_sync_jobs")
    op.drop_index("ix_square_sync_jobs_status", table_name="square_sync_jobs")
    op.drop_index("ix_square_sync_jobs_workspace_id", table_name="square_sync_jobs")
    op.drop_table("square_sync_jobs")
    op.drop_index("ix_square_refunds_local_date", table_name="square_refunds")
    op.drop_index("ix_square_refunds_workspace_id", table_name="square_refunds")
    op.drop_table("square_refunds")
    op.drop_table("square_location_state")
