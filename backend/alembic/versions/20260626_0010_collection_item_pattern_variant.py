"""replace pokeball toggle with pattern variant

Revision ID: 20260626_0010
Revises: 20260626_0009
Create Date: 2026-06-26 23:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0010"
down_revision = "20260626_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collection_items", sa.Column("pattern_variant", sa.String(length=50), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("pattern_variant", sa.String(length=50), nullable=True))

    op.execute("UPDATE collection_items SET pattern_variant = 'poke_ball' WHERE is_pokeball = true")
    op.execute("UPDATE card_price_snapshots SET pattern_variant = 'poke_ball' WHERE is_pokeball = true")

    op.drop_column("collection_items", "is_pokeball")
    op.drop_column("card_price_snapshots", "is_pokeball")


def downgrade() -> None:
    op.add_column("collection_items", sa.Column("is_pokeball", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("card_price_snapshots", sa.Column("is_pokeball", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute("UPDATE collection_items SET is_pokeball = true WHERE pattern_variant = 'poke_ball'")
    op.execute("UPDATE card_price_snapshots SET is_pokeball = true WHERE pattern_variant = 'poke_ball'")

    op.alter_column("collection_items", "is_pokeball", server_default=None)
    op.alter_column("card_price_snapshots", "is_pokeball", server_default=None)

    op.drop_column("collection_items", "pattern_variant")
    op.drop_column("card_price_snapshots", "pattern_variant")
