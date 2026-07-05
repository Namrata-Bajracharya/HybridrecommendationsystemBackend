"""add_product_variants_table

Revision ID: 44e3f8596ae6
Revises: add_sessions_table
Create Date: 2026-07-04 12:48:34.925956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44e3f8596ae6'
down_revision: Union[str, Sequence[str], None] = 'add_sessions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('product_variants',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('attributes', sa.JSON(), nullable=True),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('stock_quantity', sa.Integer(), nullable=False),
    sa.Column('sku', sa.String(length=100), nullable=True),
    sa.Column('image_document_id', sa.String(length=36), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['image_document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('product_variants')
