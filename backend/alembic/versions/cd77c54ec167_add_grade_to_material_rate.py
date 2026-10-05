"""add grade to material rate

Revision ID: cd77c54ec167
Revises: 37f07db72bfa
Create Date: 2026-09-28 20:08:19.857449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd77c54ec167'
down_revision: Union[str, Sequence[str], None] = '37f07db72bfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('material_rate', sa.Column('grade', sa.String(length=100), nullable=True))
    op.drop_index(op.f('uq_one_current_rate_per_point_material'), table_name='material_rate', postgresql_where='(effective_to IS NULL)')
    op.create_index('uq_one_current_graded_rate', 'material_rate', ['material_id', 'collection_point_id', 'grade'], unique=True, postgresql_where=sa.text('effective_to IS NULL AND grade IS NOT NULL'))
    op.create_index('uq_one_current_ungraded_rate', 'material_rate', ['material_id', 'collection_point_id'], unique=True, postgresql_where=sa.text('effective_to IS NULL AND grade IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_one_current_ungraded_rate', table_name='material_rate', postgresql_where=sa.text('effective_to IS NULL AND grade IS NULL'))
    op.drop_index('uq_one_current_graded_rate', table_name='material_rate', postgresql_where=sa.text('effective_to IS NULL AND grade IS NOT NULL'))
    op.create_index(op.f('uq_one_current_rate_per_point_material'), 'material_rate', ['material_id', 'collection_point_id'], unique=True, postgresql_where='(effective_to IS NULL)')
    op.drop_column('material_rate', 'grade')
