"""Weekly briefs, email outbox, decision tracking fields and email preferences.

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

PLAN_COLUMNS = [
    sa.Column("metric", sa.String(length=30), nullable=False, server_default="net_sales"),
    sa.Column("location_id", sa.String(length=160), nullable=True),
    sa.Column("start_date", sa.String(length=10), nullable=True),
    sa.Column("follow_up_date", sa.String(length=10), nullable=True),
    sa.Column("outcome", sa.Text(), nullable=True),
    sa.Column("outcome_at", sa.String(length=48), nullable=True),
]
MEMBER_COLUMNS = [
    sa.Column("weekly_digest", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("outcome_emails", sa.Boolean(), nullable=False, server_default=sa.true()),
]


def _add(table, columns):
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    with op.batch_alter_table(table) as batch:
        for column in columns:
            if column.name not in existing:
                batch.add_column(column.copy())


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("weekly_briefs"):
        op.create_table(
            "weekly_briefs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("week_start", sa.String(length=10), nullable=False),
            sa.Column("generated_at", sa.String(length=48), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.UniqueConstraint("workspace_id", "week_start", name="uq_weekly_brief_week"),
        )
        op.create_index("ix_weekly_briefs_workspace_id", "weekly_briefs", ["workspace_id"])
    if not inspector.has_table("email_outbox"):
        op.create_table(
            "email_outbox",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("kind", sa.String(length=30), nullable=False),
            sa.Column("dedupe_key", sa.String(length=160), nullable=False, unique=True),
            sa.Column("to_address", sa.String(length=254), nullable=False),
            sa.Column("subject", sa.String(length=200), nullable=False),
            sa.Column("html_body", sa.Text(), nullable=False),
            sa.Column("text_body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("provider_id", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.String(length=48), nullable=False),
        )
        op.create_index("ix_email_outbox_workspace_id", "email_outbox", ["workspace_id"])
    _add("tablesignal_decision_plans", PLAN_COLUMNS)
    if "ix_tablesignal_decision_plans_follow_up_date" not in {
            i["name"] for i in sa.inspect(op.get_bind()).get_indexes("tablesignal_decision_plans")}:
        op.create_index("ix_tablesignal_decision_plans_follow_up_date", "tablesignal_decision_plans", ["follow_up_date"])
    _add("workspace_members", MEMBER_COLUMNS)


def downgrade():
    with op.batch_alter_table("workspace_members") as batch:
        for column in reversed(MEMBER_COLUMNS):
            batch.drop_column(column.name)
    op.drop_index("ix_tablesignal_decision_plans_follow_up_date", table_name="tablesignal_decision_plans")
    with op.batch_alter_table("tablesignal_decision_plans") as batch:
        for column in reversed(PLAN_COLUMNS):
            batch.drop_column(column.name)
    op.drop_index("ix_email_outbox_workspace_id", table_name="email_outbox")
    op.drop_table("email_outbox")
    op.drop_index("ix_weekly_briefs_workspace_id", table_name="weekly_briefs")
    op.drop_table("weekly_briefs")
