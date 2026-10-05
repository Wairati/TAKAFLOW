"""simplify buyer orders: drop dispatch and payment verification

Recording a buyer-order payment is now itself the approval (no separate
admin verification step), and dispatch/fulfilment tracking is dropped
entirely — once paid, an order is done. This drops the columns that only
existed to support those two removed flows.

Any pre-existing rows left over from the old dispatch flow are folded into
the new, smaller lifecycle rather than deleted outright: a buyer_order in
'partially_dispatched' or 'fulfilled' is now simply 'paid' (dispatch, by
definition, could only happen once a payment had been verified), and the
inventory_sale rows that recorded those dispatches are left in place as
ordinary sales — only their now-meaningless link back to the buyer_order is
dropped. The 'partially_dispatched'/'fulfilled' labels are left on the
Postgres enum type itself (harmless, unused) rather than attempting a risky
enum-recreation.

Revision ID: 6b74a782586e
Revises: 9045fb2b7440
Create Date: 2026-10-01 19:37:20.022611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b74a782586e'
down_revision: Union[str, Sequence[str], None] = '9045fb2b7440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fold any leftover dispatch-flow rows into the new lifecycle before
    # dropping the columns that described them.
    op.execute("UPDATE buyer_order SET status = 'PAID' WHERE status IN ('PARTIALLY_DISPATCHED', 'FULFILLED')")

    op.drop_constraint('fk_inventory_sale_buyer_order_id_buyer_order', 'inventory_sale', type_='foreignkey')
    op.drop_column('inventory_sale', 'buyer_order_id')
    op.drop_column('buyer_order_payment', 'verified_at')
    op.drop_column('buyer_order_payment', 'verified_by_user_id')
    op.drop_column('buyer_order', 'quantity_dispatched')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('buyer_order', sa.Column('quantity_dispatched', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.alter_column('buyer_order', 'quantity_dispatched', server_default=None)
    op.add_column('buyer_order_payment', sa.Column('verified_by_user_id', sa.Integer(), nullable=True))
    op.add_column('buyer_order_payment', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_buyer_order_payment_verified_by_user_id_user', 'buyer_order_payment', 'user', ['verified_by_user_id'], ['id'])
    op.add_column('inventory_sale', sa.Column('buyer_order_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_inventory_sale_buyer_order_id_buyer_order', 'inventory_sale', 'buyer_order', ['buyer_order_id'], ['id'])
