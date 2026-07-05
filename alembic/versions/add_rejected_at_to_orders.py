"""add rejected_at column to orders

Revision ID: add_rejected_at
Revises: add_rejection_reasons
Create Date: 2026-07-05 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_rejected_at'
down_revision: Union[str, Sequence[str], None] = 'add_rejection_reasons'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rejected_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('rejected_at')
