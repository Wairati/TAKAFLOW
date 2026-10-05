"""drop inventory sale; add collection_point to buyer_order

The "record a sale" feature (InventorySale) is removed: recording a buyer
order's payment now posts the SALE movement itself, against the order's own
branch. That requires a buyer order to know which branch it belongs to,
hence the new, required `buyer_order.collection_point_id`.

Revision ID: fdcda4c7d58f
Revises: 6b74a782586e
Create Date: 2026-10-01 21:21:58.435151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdcda4c7d58f'
down_revision: Union[str, Sequence[str], None] = '6b74a782586e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('inventory_sale')

    # No existing buyer_order row can be assigned a real branch retroactively
    # (the column never existed), so any pre-existing rows are cleared before
    # the column is added NOT NULL.
    op.execute("DELETE FROM buyer_order_payment")
    op.execute("DELETE FROM buyer_order")

    op.add_column('buyer_order', sa.Column('collection_point_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'fk_buyer_order_collection_point_id_collection_point',
        'buyer_order', 'collection_point', ['collection_point_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_buyer_order_collection_point_id_collection_point', 'buyer_order', type_='foreignkey')
    op.drop_column('buyer_order', 'collection_point_id')

    op.create_table('inventory_sale',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_point_id', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('sold_to', sa.String(length=255), nullable=True),
        sa.Column('recorded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['collection_point_id'], ['collection_point.id'], ),
        sa.ForeignKeyConstraint(['material_id'], ['material.id'], ),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
