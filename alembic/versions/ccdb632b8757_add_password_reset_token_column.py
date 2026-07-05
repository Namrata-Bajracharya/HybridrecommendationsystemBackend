"""add password_reset_token column

Revision ID: ccdb632b8757
Revises: ca8f2e0f0fe2
Create Date: 2026-07-04 14:20:59.439656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccdb632b8757'
down_revision: Union[str, Sequence[str], None] = 'ca8f2e0f0fe2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('brands',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=1024), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('collections',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('emoji', sa.String(length=10), nullable=True),
    sa.Column('color', sa.String(length=7), nullable=True),
    sa.Column('occasion', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('payment_methods',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('provider', sa.String(length=255), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('documents') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=False)
    with op.batch_alter_table('product_images') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=False)
    op.drop_index(op.f('ix_product_images_product_id'), table_name='product_images')
    with op.batch_alter_table('products') as batch_op:
        batch_op.create_foreign_key('fk_products_brand_id_brands', 'brands', ['brand_id'], ['id'])
        batch_op.drop_column('image_url')
        batch_op.drop_column('image_document_id')
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=False)
    op.drop_index(op.f('ix_sessions_refresh_token_hash'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('is_verified', existing_type=sa.BOOLEAN(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('is_verified', existing_type=sa.BOOLEAN(), nullable=True)
    op.drop_column('users', 'password_reset_token')
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_sessions_refresh_token_hash'), 'sessions', ['refresh_token_hash'], unique=False)
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=True)
    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('image_document_id', sa.VARCHAR(length=36), nullable=True))
        batch_op.add_column(sa.Column('image_url', sa.VARCHAR(length=500), nullable=True))
        batch_op.drop_constraint('fk_products_brand_id_brands', type_='foreignkey')
    op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)
    with op.batch_alter_table('product_images') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=True)
    with op.batch_alter_table('documents') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DATETIME(), nullable=True)
    op.drop_table('payment_methods')
    op.drop_table('collections')
    op.drop_table('brands')
