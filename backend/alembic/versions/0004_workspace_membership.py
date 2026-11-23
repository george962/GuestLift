"""Workspace members (owner/manager) and invites; backfill an owner row per workspace.

Revision ID: 0004
Revises: 0003
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workspace_members"):
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("subject", sa.String(length=160), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("created_at", sa.String(length=40), nullable=False),
        )
        op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
        op.create_index("ix_workspace_members_subject", "workspace_members", ["subject"], unique=True)
    if not inspector.has_table("workspace_invites"):
        op.create_table(
            "workspace_invites",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("saas_workspaces.id"), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("created_by", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.String(length=40), nullable=False),
            sa.Column("expires_at", sa.Integer(), nullable=False),
            sa.Column("accepted_at", sa.String(length=40), nullable=True),
        )
        op.create_index("ix_workspace_invites_token_hash", "workspace_invites", ["token_hash"], unique=True)
        op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"])
    bind = op.get_bind()
    now = datetime.now(timezone.utc).isoformat()
    existing = {row[0] for row in bind.execute(sa.text("SELECT subject FROM workspace_members"))}
    for wid, owner in bind.execute(sa.text("SELECT id, owner_sub FROM saas_workspaces")).fetchall():
        if owner not in existing:
            bind.execute(sa.text("INSERT INTO workspace_members (id, workspace_id, subject, role, email, created_at) "
                                 "VALUES (:id, :w, :s, 'owner', '', :t)"),
                         {"id": str(uuid.uuid4()), "w": wid, "s": owner, "t": now})


def downgrade():
    op.drop_index("ix_workspace_invites_workspace_id", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_token_hash", table_name="workspace_invites")
    op.drop_table("workspace_invites")
    op.drop_index("ix_workspace_members_subject", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
