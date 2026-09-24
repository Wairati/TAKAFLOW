"""add username to user

Revision ID: 9a91684dc822
Revises: 9300d85bc3d5
Create Date: 2026-09-24 19:15:13.952384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a91684dc822'
down_revision: Union[str, Sequence[str], None] = '9300d85bc3d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user', sa.Column('username', sa.String(length=255), nullable=True))
    op.create_unique_constraint('user_username_key', 'user', ['username'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('user_username_key', 'user', type_='unique')
    op.drop_column('user', 'username')
