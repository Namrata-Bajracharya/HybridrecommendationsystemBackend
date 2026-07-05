"""bridge missing current revision

Revision ID: ccdb632b8757
Revises: initial_squash
Create Date: 2026-07-06

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "ccdb632b8757"
down_revision: Union[str, Sequence[str], None] = "initial_squash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass