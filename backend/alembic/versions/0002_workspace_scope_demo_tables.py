"""scope the shared demo tables by workspace

Adds ``workspace_id`` to the five demo tables (canonical_orders, import_runs,
campaigns, campaign_redemptions, campaign_import_runs). Existing rows are
backfilled into the ``public-demo`` workspace by the column's server default.
Uniqueness that used to be global (one order per provider+id, one redemption
id, one campaign id) becomes unique *per workspace*.

Safe to re-run against databases that already have the column, and against
legacy databases whose demo tables were created by the old create_all() path.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO = 'public-demo'
# Names SQLite assigns to reflected, unnamed UNIQUE constraints inside batch mode.
NAMING = {'uq': 'uq_%(table_name)s_%(column_0_name)s'}


def _inspector():
    return sa.inspect(op.get_bind())


def _columns(table: str) -> set[str]:
    return {c['name'] for c in _inspector().get_columns(table)}


def _has_table(table: str) -> bool:
    return table in _inspector().get_table_names()


def _has_index(table: str, name: str) -> bool:
    return any(i['name'] == name for i in _inspector().get_indexes(table))


def _unique_name(table: str, columns: list[str]):
    """Name of the UNIQUE constraint over exactly ``columns`` (or None if absent)."""
    for uc in _inspector().get_unique_constraints(table):
        if list(uc['column_names']) == columns:
            return uc['name'] or NAMING['uq'] % {'table_name': table, 'column_0_name': columns[0]}
    return None


def _has_unique(table: str, name: str) -> bool:
    return any(uc['name'] == name for uc in _inspector().get_unique_constraints(table))


def _workspace_column():
    return sa.Column('workspace_id', sa.String(length=36), nullable=False, server_default=DEMO)


def _scope_table(table: str, drop_uniques: list[list[str]], new_uniques: dict[str, list[str]]) -> None:
    if not _has_table(table):
        return  # created later by create_all/baseline with the workspace column already
    present = _columns(table)
    with op.batch_alter_table(table, naming_convention=NAMING) as batch:
        if 'workspace_id' not in present:
            batch.add_column(_workspace_column())
        for cols in drop_uniques:
            name = _unique_name(table, cols)
            if name:
                batch.drop_constraint(name, type_='unique')
        for name, cols in new_uniques.items():
            # Legacy stub tables may lack the columns; skip rather than fail.
            if set(cols) - {'workspace_id'} <= present and not _has_unique(table, name):
                batch.create_unique_constraint(name, cols)
    index = f'ix_{table}_workspace_id'
    if not _has_index(table, index):
        op.create_index(index, table, ['workspace_id'], unique=False)


def _scope_campaigns() -> None:
    table = 'campaigns'
    if not _has_table(table) or 'workspace_id' in _columns(table):
        return
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        # SQLite cannot alter a primary key in place: rebuild and copy.
        op.rename_table(table, 'campaigns_pre_scope')
        op.create_table(
            table,
            sa.Column('workspace_id', sa.String(length=36), nullable=False, server_default=DEMO),
            sa.Column('campaign_id', sa.String(length=80), nullable=False),
            sa.Column('code', sa.String(length=80), nullable=False),
            sa.Column('name', sa.String(length=160), nullable=False),
            sa.Column('offer_type', sa.String(length=30), nullable=False),
            sa.Column('start_date', sa.String(length=10), nullable=False),
            sa.Column('end_date', sa.String(length=10), nullable=False),
            sa.Column('variable_cost_minor', sa.Integer(), nullable=False),
            sa.Column('fixed_cost_minor', sa.Integer(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint('workspace_id', 'campaign_id'),
        )
        op.execute(
            "INSERT INTO campaigns (workspace_id, campaign_id, code, name, offer_type, start_date, end_date, "
            "variable_cost_minor, fixed_cost_minor, description) "
            f"SELECT '{DEMO}', campaign_id, code, name, offer_type, start_date, end_date, "
            "variable_cost_minor, fixed_cost_minor, description FROM campaigns_pre_scope"
        )
        op.drop_table('campaigns_pre_scope')
    else:
        pk = _inspector().get_pk_constraint(table)
        op.add_column(table, _workspace_column())
        if pk.get('name'):
            op.drop_constraint(pk['name'], table, type_='primary')
        op.create_primary_key(pk.get('name') or 'campaigns_pkey', table, ['workspace_id', 'campaign_id'])
    # No separate index: the composite primary key already leads with workspace_id.


def upgrade() -> None:
    _scope_table(
        'canonical_orders',
        drop_uniques=[['provider', 'source_order_id']],
        new_uniques={'uq_workspace_provider_order': ['workspace_id', 'provider', 'source_order_id']},
    )
    _scope_table('import_runs', drop_uniques=[], new_uniques={})
    _scope_table(
        'campaign_redemptions',
        drop_uniques=[['redemption_id'], ['provider', 'source_order_id']],
        new_uniques={
            'uq_workspace_redemption': ['workspace_id', 'redemption_id'],
            'uq_workspace_one_campaign_per_order': ['workspace_id', 'provider', 'source_order_id'],
        },
    )
    _scope_table('campaign_import_runs', drop_uniques=[], new_uniques={})
    _scope_campaigns()


def downgrade() -> None:
    """Return to global uniqueness. Rows from any non-demo workspace are deleted first,
    because they could collide once the workspace column is gone."""
    bind = op.get_bind()
    for table in ('canonical_orders', 'import_runs', 'campaign_redemptions', 'campaign_import_runs', 'campaigns'):
        if _has_table(table) and 'workspace_id' in _columns(table):
            bind.execute(sa.text(f'DELETE FROM {table} WHERE workspace_id <> :demo'), {'demo': DEMO})

    for table, new, old in (
        ('canonical_orders', ['uq_workspace_provider_order'], {'uq_provider_order': ['provider', 'source_order_id']}),
        ('campaign_redemptions', ['uq_workspace_redemption', 'uq_workspace_one_campaign_per_order'],
         {'uq_one_campaign_per_demo_order': ['provider', 'source_order_id'], 'uq_campaign_redemptions_redemption_id': ['redemption_id']}),
    ):
        if not _has_table(table):
            continue
        with op.batch_alter_table(table, naming_convention=NAMING) as batch:
            for name in new:
                if _has_unique(table, name):
                    batch.drop_constraint(name, type_='unique')
            for name, cols in old.items():
                batch.create_unique_constraint(name, cols)

    for table in ('canonical_orders', 'import_runs', 'campaign_redemptions', 'campaign_import_runs'):
        if not _has_table(table) or 'workspace_id' not in _columns(table):
            continue
        if _has_index(table, f'ix_{table}_workspace_id'):
            op.drop_index(f'ix_{table}_workspace_id', table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column('workspace_id')

    if _has_table('campaigns') and 'workspace_id' in _columns('campaigns'):
        if bind.dialect.name == 'sqlite':
            op.rename_table('campaigns', 'campaigns_scoped')
            op.create_table(
                'campaigns',
                sa.Column('campaign_id', sa.String(length=80), nullable=False),
                sa.Column('code', sa.String(length=80), nullable=False),
                sa.Column('name', sa.String(length=160), nullable=False),
                sa.Column('offer_type', sa.String(length=30), nullable=False),
                sa.Column('start_date', sa.String(length=10), nullable=False),
                sa.Column('end_date', sa.String(length=10), nullable=False),
                sa.Column('variable_cost_minor', sa.Integer(), nullable=False),
                sa.Column('fixed_cost_minor', sa.Integer(), nullable=False),
                sa.Column('description', sa.Text(), nullable=False),
                sa.PrimaryKeyConstraint('campaign_id'),
            )
            op.execute(
                'INSERT INTO campaigns SELECT campaign_id, code, name, offer_type, start_date, end_date, '
                'variable_cost_minor, fixed_cost_minor, description FROM campaigns_scoped'
            )
            op.drop_table('campaigns_scoped')
        else:
            pk = _inspector().get_pk_constraint('campaigns')
            op.drop_constraint(pk['name'], 'campaigns', type_='primary')
            op.drop_column('campaigns', 'workspace_id')
            op.create_primary_key(pk['name'], 'campaigns', ['campaign_id'])
