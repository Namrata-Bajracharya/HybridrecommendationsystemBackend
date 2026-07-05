"""add documents table and image_document_id refs

Revision ID: 1a2b3c4dadd
Revises: e34fcd50def9
Create Date: 2026-06-30 23:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4dadd"
down_revision = "e34fcd50def9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("absolute_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add image_document_id to products and categories
    op.add_column("products", sa.Column("image_document_id", sa.String(length=36), nullable=True))
    op.add_column("categories", sa.Column("image_document_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "image_document_id")
    op.drop_column("products", "image_document_id")
    op.drop_table("documents")
