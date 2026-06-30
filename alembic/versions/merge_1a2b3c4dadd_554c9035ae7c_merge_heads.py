"""merge heads

Revision ID: merge_1a2b3c4dadd_554c9035ae7c
Revises: 1a2b3c4dadd, 554c9035ae7c
Create Date: 2026-06-30 23:45:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "merge_1a2b3c4dadd_554c9035ae7c"
down_revision = ("1a2b3c4dadd", "554c9035ae7c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration: no schema changes (merge two heads)."""
    pass


def downgrade() -> None:
    pass
