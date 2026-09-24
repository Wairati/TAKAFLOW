"""add employee_number to user

Revision ID: be55c430a792
Revises: 9a91684dc822
Create Date: 2026-09-24 21:14:32.440693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be55c430a792'
down_revision: Union[str, Sequence[str], None] = '9a91684dc822'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user', sa.Column('employee_number', sa.String(length=6), nullable=True))
    op.create_unique_constraint('user_employee_number_key', 'user', ['employee_number'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('user_employee_number_key', 'user', type_='unique')
    op.drop_column('user', 'employee_number')
