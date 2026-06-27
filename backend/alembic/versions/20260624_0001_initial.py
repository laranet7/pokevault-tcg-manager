"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column("set_id", sa.String(length=100), nullable=True),
        sa.Column("set_name", sa.String(length=255), nullable=True),
        sa.Column("printed_total", sa.Integer(), nullable=True),
        sa.Column("rarity", sa.String(length=100), nullable=True),
        sa.Column("image_small", sa.String(length=500), nullable=True),
        sa.Column("image_large", sa.String(length=500), nullable=True),
        sa.Column("api_source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cards_external_id"), "cards", ["external_id"], unique=True)
    op.create_index(op.f("ix_cards_id"), "cards", ["id"], unique=False)
    op.create_index(op.f("ix_cards_name"), "cards", ["name"], unique=False)
    op.create_index(op.f("ix_cards_number"), "cards", ["number"], unique=False)

    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=100), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collections_id"), "collections", ["id"], unique=False)
    op.create_index(op.f("ix_collections_name"), "collections", ["name"], unique=True)

    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=100), nullable=True),
        sa.Column("condition", sa.String(length=100), nullable=True),
        sa.Column("finish", sa.String(length=100), nullable=True),
        sa.Column("is_for_sale", sa.Boolean(), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("base_price_currency", sa.String(length=10), nullable=False),
        sa.Column("sale_margin_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("sale_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sale_status", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_items_card_id"), "collection_items", ["card_id"], unique=False)
    op.create_index(op.f("ix_collection_items_collection_id"), "collection_items", ["collection_id"], unique=False)
    op.create_index(op.f("ix_collection_items_id"), "collection_items", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_collection_items_id"), table_name="collection_items")
    op.drop_index(op.f("ix_collection_items_collection_id"), table_name="collection_items")
    op.drop_index(op.f("ix_collection_items_card_id"), table_name="collection_items")
    op.drop_table("collection_items")
    op.drop_index(op.f("ix_collections_name"), table_name="collections")
    op.drop_index(op.f("ix_collections_id"), table_name="collections")
    op.drop_table("collections")
    op.drop_index(op.f("ix_cards_number"), table_name="cards")
    op.drop_index(op.f("ix_cards_name"), table_name="cards")
    op.drop_index(op.f("ix_cards_id"), table_name="cards")
    op.drop_index(op.f("ix_cards_external_id"), table_name="cards")
    op.drop_table("cards")
