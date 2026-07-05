"""Add refund timestamp columns to orders table

Revision ID: 001
Revises:
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa


revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('refund_requested_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('refund_out_for_pickup_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('item_retrieved_from_customer_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('item_retrieved_by_admin_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('refund_on_the_way_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('refund_successful_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('refund_requested_at')
        batch_op.drop_column('refund_out_for_pickup_at')
        batch_op.drop_column('item_retrieved_from_customer_at')
        batch_op.drop_column('item_retrieved_by_admin_at')
        batch_op.drop_column('refund_on_the_way_at')
        batch_op.drop_column('refund_successful_at')
