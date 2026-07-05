"""sync current models to sqlite schema

Revision ID: 7c1a9d2f4b10
Revises: ccdb632b8757
Create Date: 2026-07-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1a9d2f4b10"
down_revision: Union[str, Sequence[str], None] = "ccdb632b8757"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.engine.reflection.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _column_exists(
    inspector: sa.engine.reflection.Inspector, table_name: str, column_name: str
) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "products", "brand_id"):
        op.add_column("products", sa.Column("brand_id", sa.Integer(), nullable=True))

    if not _table_exists(inspector, "suppliers"):
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("contact_email", sa.String(length=255), nullable=True),
            sa.Column("contact_phone", sa.String(length=50), nullable=True),
            sa.Column("address", sa.String(length=1024), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if not _table_exists(inspector, "rejection_reasons"):
        op.create_table(
            "rejection_reasons",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("reason", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("reason"),
        )

    if not _table_exists(inspector, "coupons"):
        op.create_table(
            "coupons",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("is_percentage", sa.Boolean(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=True),
            sa.Column("ends_at", sa.DateTime(), nullable=True),
            sa.Column("usage_limit", sa.Integer(), nullable=True),
            sa.Column("used_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if not _table_exists(inspector, "inventory_movements"):
        op.create_table(
            "inventory_movements",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("change", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(length=512), nullable=True),
            sa.Column("related_order_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(inspector, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.String(length=1024), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=True),
            sa.Column(
                "order_id",
                sa.Integer(),
                sa.ForeignKey("orders.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("read", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(inspector, "purchase_orders"):
        op.create_table(
            "purchase_orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "supplier_id",
                sa.Integer(),
                sa.ForeignKey("suppliers.id"),
                nullable=False,
            ),
            sa.Column("total_amount", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(inspector, "purchase_order_items"):
        op.create_table(
            "purchase_order_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "purchase_order_id",
                sa.Integer(),
                sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "variant_id",
                sa.Integer(),
                sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("unit_cost", sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(inspector, "shipping_zones"):
        op.create_table(
            "shipping_zones",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if not _table_exists(inspector, "couriers"):
        op.create_table(
            "couriers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("api_key", sa.String(length=1024), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if not _table_exists(inspector, "stock_batches"):
        op.create_table(
            "stock_batches",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "variant_id",
                sa.Integer(),
                sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "purchase_order_item_id",
                sa.Integer(),
                sa.ForeignKey("purchase_order_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("quantity_remaining", sa.Integer(), nullable=False),
            sa.Column("unit_cost", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(inspector, "test_sessions"):
        op.create_table(
            "test_sessions",
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("viewed_ids", sa.Text(), server_default="", nullable=False),
            sa.Column("cart_ids", sa.Text(), server_default="", nullable=False),
            sa.Column("wishlist_ids", sa.Text(), server_default="", nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("session_id"),
        )


def downgrade() -> None:
    op.drop_table("test_sessions")
    op.drop_table("stock_batches")
    op.drop_table("couriers")
    op.drop_table("shipping_zones")
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("notifications")
    op.drop_table("inventory_movements")
    op.drop_table("coupons")
    op.drop_table("rejection_reasons")
    op.drop_table("suppliers")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("brand_id")