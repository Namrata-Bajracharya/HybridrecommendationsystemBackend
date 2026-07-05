"""add rejection_reasons table

Revision ID: add_rejection_reasons
Revises: f28f951eaca3
Create Date: 2026-07-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_rejection_reasons'
down_revision: Union[str, Sequence[str], None] = '0eabdd916d8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rejection_reasons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reason'),
    )


def downgrade() -> None:
    op.drop_table('rejection_reasons')
