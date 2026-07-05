"""add reply and replied_at to reviews

Revision ID: add_reply_to_reviews
Revises: add_rejected_at
Create Date: 2026-07-05 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_reply_to_reviews'
down_revision: Union[str, Sequence[str], None] = 'add_rejected_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reply', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('replied_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('reply')
        batch_op.drop_column('replied_at')
