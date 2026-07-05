"""Add test_sessions table for anonymous test state persistence

Revision ID: add_test_sessions_table
Revises: 7831bb55f5f8
Create Date: 2026-07-06 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "add_test_sessions_table"
down_revision: Union[str, None] = "7831bb55f5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_sessions",
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("viewed_ids", sa.Text(), nullable=False, server_default=""),
        sa.Column("cart_ids", sa.Text(), nullable=False, server_default=""),
        sa.Column("wishlist_ids", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("test_sessions")
