"""baseline schema

Idempotent: tables that already exist (databases created by the old
create_all() startup path) are left untouched, so `alembic upgrade head` is
safe on both new and existing databases.

Revision ID: 0001
Revises: 
Create Date: 2026-11-22 12:34:26.319722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_existing: set[str] = set()
_created: set[str] = set()


def _create_table(name, *args, **kwargs):
    if name not in _existing:
        op.create_table(name, *args, **kwargs)
        _created.add(name)


def _create_index(name, table, *args, **kwargs):
    if table in _created:
        op.create_index(name, table, *args, **kwargs)


def upgrade() -> None:
    """Upgrade schema."""
    _existing.update(sa.inspect(op.get_bind()).get_table_names())
    _created.clear()
    _create_table('campaign_import_runs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('processed_at', sa.String(length=40), nullable=False),
    sa.Column('campaigns_inserted', sa.Integer(), nullable=False),
    sa.Column('redemptions_inserted', sa.Integer(), nullable=False),
    sa.Column('duplicates', sa.Integer(), nullable=False),
    sa.Column('rejected', sa.Integer(), nullable=False),
    sa.Column('issues_json', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    _create_table('campaign_redemptions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('redemption_id', sa.String(length=120), nullable=False),
    sa.Column('campaign_id', sa.String(length=80), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('source_order_id', sa.String(length=120), nullable=False),
    sa.Column('redeemed_at', sa.String(length=40), nullable=False),
    sa.Column('discount_minor', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'source_order_id', name='uq_one_campaign_per_demo_order'),
    sa.UniqueConstraint('redemption_id')
    )
    _create_index(op.f('ix_campaign_redemptions_campaign_id'), 'campaign_redemptions', ['campaign_id'], unique=False)
    _create_table('campaigns',
    sa.Column('campaign_id', sa.String(length=80), nullable=False),
    sa.Column('code', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('offer_type', sa.String(length=30), nullable=False),
    sa.Column('start_date', sa.String(length=10), nullable=False),
    sa.Column('end_date', sa.String(length=10), nullable=False),
    sa.Column('variable_cost_minor', sa.Integer(), nullable=False),
    sa.Column('fixed_cost_minor', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('campaign_id')
    )
    _create_table('canonical_orders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('source_order_id', sa.String(length=120), nullable=False),
    sa.Column('location_id', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.String(length=80), nullable=False),
    sa.Column('customer_id', sa.String(length=120), nullable=True),
    sa.Column('net_sales_minor', sa.Integer(), nullable=False),
    sa.Column('discount_minor', sa.Integer(), nullable=False),
    sa.Column('refund_minor', sa.Integer(), nullable=False),
    sa.Column('payload_json', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'source_order_id', name='uq_provider_order')
    )
    _create_table('import_runs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('processed_at', sa.String(length=40), nullable=False),
    sa.Column('inserted', sa.Integer(), nullable=False),
    sa.Column('duplicates', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    _create_table('local_users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=320), nullable=False),
    sa.Column('created_at', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_local_users_email'), 'local_users', ['email'], unique=True)
    _create_table('saas_billing_events',
    sa.Column('stripe_event_id', sa.String(length=160), nullable=False),
    sa.Column('processed_at', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('stripe_event_id')
    )
    _create_table('saas_workspaces',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('owner_sub', sa.String(length=160), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('restaurant_type', sa.String(length=35), nullable=False),
    sa.Column('goal', sa.String(length=40), nullable=False),
    sa.Column('subscription_plan', sa.String(length=20), nullable=False),
    sa.Column('subscription_status', sa.String(length=35), nullable=False),
    sa.Column('stripe_customer_id', sa.String(length=120), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stripe_customer_id'),
    sa.UniqueConstraint('stripe_subscription_id')
    )
    _create_index(op.f('ix_saas_workspaces_owner_sub'), 'saas_workspaces', ['owner_sub'], unique=True)
    _create_table('assisted_setup_requests',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('provider', sa.String(length=30), nullable=False),
    sa.Column('note', sa.String(length=300), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.String(length=48), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_assisted_setup_requests_workspace_id'), 'assisted_setup_requests', ['workspace_id'], unique=False)
    _create_table('local_sessions',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('csrf_token', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['local_users.id'], ),
    sa.PrimaryKeyConstraint('token_hash')
    )
    _create_index(op.f('ix_local_sessions_expires_at'), 'local_sessions', ['expires_at'], unique=False)
    _create_index(op.f('ix_local_sessions_user_id'), 'local_sessions', ['user_id'], unique=False)
    _create_table('saas_workspace_demo_orders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('source_order_id', sa.String(length=140), nullable=False),
    sa.Column('location_id', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.String(length=80), nullable=False),
    sa.Column('status', sa.String(length=35), nullable=False),
    sa.Column('customer_id', sa.String(length=140), nullable=True),
    sa.Column('net_sales_minor', sa.Integer(), nullable=False),
    sa.Column('discount_minor', sa.Integer(), nullable=False),
    sa.Column('campaign_code', sa.String(length=100), nullable=True),
    sa.Column('campaign_discount_minor', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'provider', 'source_order_id', name='uq_saas_demo_order')
    )
    _create_index(op.f('ix_saas_workspace_demo_orders_workspace_id'), 'saas_workspace_demo_orders', ['workspace_id'], unique=False)
    _create_table('square_sandbox_connections',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('merchant_id', sa.String(length=160), nullable=False),
    sa.Column('credential_mode', sa.String(length=30), nullable=False),
    sa.Column('token_ciphertext', sa.Text(), nullable=True),
    sa.Column('refresh_ciphertext', sa.Text(), nullable=True),
    sa.Column('token_expires_at', sa.String(length=48), nullable=True),
    sa.Column('connected_at', sa.String(length=48), nullable=False),
    sa.Column('last_sync_at', sa.String(length=48), nullable=True),
    sa.Column('last_error', sa.String(length=220), nullable=True),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('merchant_id')
    )
    _create_index(op.f('ix_square_sandbox_connections_workspace_id'), 'square_sandbox_connections', ['workspace_id'], unique=True)
    _create_table('square_sandbox_oauth_states',
    sa.Column('state_hash', sa.String(length=64), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('expires_at', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('state_hash')
    )
    _create_index(op.f('ix_square_sandbox_oauth_states_workspace_id'), 'square_sandbox_oauth_states', ['workspace_id'], unique=False)
    _create_table('square_sandbox_orders',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('source_order_id', sa.String(length=160), nullable=False),
    sa.Column('location_id', sa.String(length=160), nullable=False),
    sa.Column('created_at', sa.String(length=55), nullable=False),
    sa.Column('updated_at', sa.String(length=55), nullable=False),
    sa.Column('status', sa.String(length=40), nullable=False),
    sa.Column('customer_id', sa.String(length=140), nullable=True),
    sa.Column('net_sales_minor', sa.Integer(), nullable=False),
    sa.Column('discount_minor', sa.Integer(), nullable=False),
    sa.Column('tax_minor', sa.Integer(), nullable=False),
    sa.Column('tip_minor', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=4), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'source_order_id', name='uq_sandbox_order_owner')
    )
    _create_index(op.f('ix_square_sandbox_orders_workspace_id'), 'square_sandbox_orders', ['workspace_id'], unique=False)
    _create_table('square_sandbox_sync_runs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('started_at', sa.String(length=48), nullable=False),
    sa.Column('completed_at', sa.String(length=48), nullable=True),
    sa.Column('status', sa.String(length=18), nullable=False),
    sa.Column('scanned', sa.Integer(), nullable=False),
    sa.Column('inserted', sa.Integer(), nullable=False),
    sa.Column('updated', sa.Integer(), nullable=False),
    sa.Column('skipped', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=200), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_square_sandbox_sync_runs_workspace_id'), 'square_sandbox_sync_runs', ['workspace_id'], unique=False)
    _create_table('tablesignal_decision_plans',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=140), nullable=False),
    sa.Column('objective', sa.String(length=40), nullable=False),
    sa.Column('offer_type', sa.String(length=30), nullable=False),
    sa.Column('offer_value', sa.Integer(), nullable=False),
    sa.Column('target_redemptions', sa.Integer(), nullable=False),
    sa.Column('reference_basket_minor', sa.Integer(), nullable=False),
    sa.Column('assumed_margin_percent', sa.Integer(), nullable=False),
    sa.Column('discount_budget_minor', sa.Integer(), nullable=False),
    sa.Column('modeled_contribution_minor', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('created_at', sa.String(length=40), nullable=False),
    sa.Column('updated_at', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    _create_index(op.f('ix_tablesignal_decision_plans_workspace_id'), 'tablesignal_decision_plans', ['workspace_id'], unique=False)
    _create_table('tablesignal_onboarding_progress',
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('stage', sa.Integer(), nullable=False),
    sa.Column('plan_choice', sa.String(length=20), nullable=False),
    sa.Column('updated_at', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['saas_workspaces.id'], ),
    sa.PrimaryKeyConstraint('workspace_id')
    )
    # Legacy databases: the old startup code added this column by hand.
    if 'canonical_orders' in _existing:
        cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('canonical_orders')}
        if 'customer_id' not in cols:
            op.add_column('canonical_orders', sa.Column('customer_id', sa.String(length=120), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('tablesignal_onboarding_progress')
    op.drop_index(op.f('ix_tablesignal_decision_plans_workspace_id'), table_name='tablesignal_decision_plans')
    op.drop_table('tablesignal_decision_plans')
    op.drop_index(op.f('ix_square_sandbox_sync_runs_workspace_id'), table_name='square_sandbox_sync_runs')
    op.drop_table('square_sandbox_sync_runs')
    op.drop_index(op.f('ix_square_sandbox_orders_workspace_id'), table_name='square_sandbox_orders')
    op.drop_table('square_sandbox_orders')
    op.drop_index(op.f('ix_square_sandbox_oauth_states_workspace_id'), table_name='square_sandbox_oauth_states')
    op.drop_table('square_sandbox_oauth_states')
    op.drop_index(op.f('ix_square_sandbox_connections_workspace_id'), table_name='square_sandbox_connections')
    op.drop_table('square_sandbox_connections')
    op.drop_index(op.f('ix_saas_workspace_demo_orders_workspace_id'), table_name='saas_workspace_demo_orders')
    op.drop_table('saas_workspace_demo_orders')
    op.drop_index(op.f('ix_local_sessions_user_id'), table_name='local_sessions')
    op.drop_index(op.f('ix_local_sessions_expires_at'), table_name='local_sessions')
    op.drop_table('local_sessions')
    op.drop_index(op.f('ix_assisted_setup_requests_workspace_id'), table_name='assisted_setup_requests')
    op.drop_table('assisted_setup_requests')
    op.drop_index(op.f('ix_saas_workspaces_owner_sub'), table_name='saas_workspaces')
    op.drop_table('saas_workspaces')
    op.drop_table('saas_billing_events')
    op.drop_index(op.f('ix_local_users_email'), table_name='local_users')
    op.drop_table('local_users')
    op.drop_table('import_runs')
    op.drop_table('canonical_orders')
    op.drop_table('campaigns')
    op.drop_index(op.f('ix_campaign_redemptions_campaign_id'), table_name='campaign_redemptions')
    op.drop_table('campaign_redemptions')
    op.drop_table('campaign_import_runs')
    # ### end Alembic commands ###
