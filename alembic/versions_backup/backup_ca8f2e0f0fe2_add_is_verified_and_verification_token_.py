"""add is_verified and verification_token to users

Revision ID: ca8f2e0f0fe2
Revises: 32858744f370
Create Date: 2026-07-04 13:43:07.401773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ca8f2e0f0fe2'
down_revision: Union[str, Sequence[str], None] = '32858744f370'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET is_verified = 0 WHERE is_verified IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
