"""add selling_rate to material

Buyer-order payments were priced by whoever recorded them typing in any
amount. This adds a flat, admin-set selling rate per material so a payment's
amount can instead be computed as selling_rate * quantity_requested (see
buyer_order_service.record_payment). Nullable: existing materials have no
rate until an admin sets one, and recording a payment against a material
with no rate set is rejected until then.

Revision ID: a3f7c1e9b2d4
Revises: fdcda4c7d58f
Create Date: 2026-10-02 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c1e9b2d4'
down_revision: Union[str, Sequence[str], None] = 'fdcda4c7d58f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('material', sa.Column('selling_rate', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('material', 'selling_rate')
