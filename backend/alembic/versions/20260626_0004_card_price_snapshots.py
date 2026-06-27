"""card price snapshots"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0004"
down_revision = "20260626_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "card_price_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("collection_item_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("marketplace", sa.String(length=100), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("finish", sa.String(length=100), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("base_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("sale_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_item_id"], ["collection_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_card_price_snapshots_id"), "card_price_snapshots", ["id"], unique=False)
    op.create_index(
        op.f("ix_card_price_snapshots_collection_id"),
        "card_price_snapshots",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_card_price_snapshots_collection_item_id"),
        "card_price_snapshots",
        ["collection_item_id"],
        unique=False,
    )
    op.create_index(op.f("ix_card_price_snapshots_card_id"), "card_price_snapshots", ["card_id"], unique=False)
    op.create_index(
        op.f("ix_card_price_snapshots_captured_at"),
        "card_price_snapshots",
        ["captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_card_price_snapshots_captured_at"), table_name="card_price_snapshots")
    op.drop_index(op.f("ix_card_price_snapshots_card_id"), table_name="card_price_snapshots")
    op.drop_index(op.f("ix_card_price_snapshots_collection_item_id"), table_name="card_price_snapshots")
    op.drop_index(op.f("ix_card_price_snapshots_collection_id"), table_name="card_price_snapshots")
    op.drop_index(op.f("ix_card_price_snapshots_id"), table_name="card_price_snapshots")
    op.drop_table("card_price_snapshots")
