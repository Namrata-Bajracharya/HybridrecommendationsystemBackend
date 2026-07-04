"""add variant_id to cartitems and orderitems

Revision ID: 32858744f370
Revises: 44e3f8596ae6
Create Date: 2026-07-04 13:01:04.607335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32858744f370'
down_revision: Union[str, Sequence[str], None] = '44e3f8596ae6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('cartitems') as batch_op:
        batch_op.add_column(sa.Column('variant_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_cartitems_variant_id', 'product_variants',
            ['variant_id'], ['id'], ondelete='SET NULL',
        )
    with op.batch_alter_table('orderitems') as batch_op:
        batch_op.add_column(sa.Column('variant_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_orderitems_variant_id', 'product_variants',
            ['variant_id'], ['id'], ondelete='SET NULL',
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('orderitems') as batch_op:
        batch_op.drop_constraint('fk_orderitems_variant_id', type_='foreignkey')
        batch_op.drop_column('variant_id')
    with op.batch_alter_table('cartitems') as batch_op:
        batch_op.drop_constraint('fk_cartitems_variant_id', type_='foreignkey')
        batch_op.drop_column('variant_id')
