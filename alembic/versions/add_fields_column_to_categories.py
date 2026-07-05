"""Add fields JSON column to categories table

Revision ID: add_fields_to_categories
Revises: merge_1a2b3c4dadd_554c9035ae7c_merge_heads
Create Date: 2026-07-01 19:35:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "add_fields_to_categories"
down_revision: Union[str, None] = "554c9035ae7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("fields", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "fields")
