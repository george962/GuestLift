"""M6: privacy-minimized workspace signals, preview acknowledgement and support tickets.

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())
    if not insp.has_table('workspace_product_signals'):
        op.create_table('workspace_product_signals',
            sa.Column('workspace_id', sa.String(36), sa.ForeignKey('saas_workspaces.id'), primary_key=True),
            sa.Column('signal', sa.String(36), primary_key=True),
            sa.Column('period', sa.String(10), primary_key=True),
            sa.Column('observed_at', sa.String(48), nullable=False))
    if not insp.has_table('workspace_preview_ack'):
        op.create_table('workspace_preview_ack',
            sa.Column('workspace_id', sa.String(36), sa.ForeignKey('saas_workspaces.id'), primary_key=True),
            sa.Column('version', sa.String(48), nullable=False),
            sa.Column('acknowledged_at', sa.String(48), nullable=False))
    if not insp.has_table('workspace_support_tickets'):
        op.create_table('workspace_support_tickets',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('workspace_id', sa.String(36), sa.ForeignKey('saas_workspaces.id'), nullable=False),
            sa.Column('category', sa.String(36), nullable=False),
            sa.Column('description', sa.String(500), nullable=False),
            sa.Column('status', sa.String(20), nullable=False),
            sa.Column('created_at', sa.String(48), nullable=False))
    existing = {i['name'] for i in sa.inspect(op.get_bind()).get_indexes('workspace_support_tickets')}
    if 'ix_workspace_support_tickets_workspace_id' not in existing:
        op.create_index('ix_workspace_support_tickets_workspace_id','workspace_support_tickets',['workspace_id'])


def downgrade():
    op.drop_table('workspace_product_signals')
    op.drop_table('workspace_preview_ack')
    op.drop_index('ix_workspace_support_tickets_workspace_id',table_name='workspace_support_tickets')
    op.drop_table('workspace_support_tickets')
