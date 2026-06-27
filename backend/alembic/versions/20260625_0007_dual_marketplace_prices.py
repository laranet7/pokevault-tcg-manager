"""dual marketplace prices on items and snapshots"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0007"
down_revision = "20260625_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collection_items", sa.Column("tcgplayer_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("collection_items", sa.Column("tcgplayer_currency", sa.String(length=10), nullable=True))
    op.add_column("collection_items", sa.Column("tcgplayer_price_label", sa.String(length=50), nullable=True))
    op.add_column("collection_items", sa.Column("cardmarket_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("collection_items", sa.Column("cardmarket_currency", sa.String(length=10), nullable=True))
    op.add_column("collection_items", sa.Column("cardmarket_price_label", sa.String(length=50), nullable=True))

    op.add_column("card_price_snapshots", sa.Column("tcgplayer_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("tcgplayer_currency", sa.String(length=10), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("tcgplayer_price_label", sa.String(length=50), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("cardmarket_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("cardmarket_currency", sa.String(length=10), nullable=True))
    op.add_column("card_price_snapshots", sa.Column("cardmarket_price_label", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("card_price_snapshots", "cardmarket_price_label")
    op.drop_column("card_price_snapshots", "cardmarket_currency")
    op.drop_column("card_price_snapshots", "cardmarket_price")
    op.drop_column("card_price_snapshots", "tcgplayer_price_label")
    op.drop_column("card_price_snapshots", "tcgplayer_currency")
    op.drop_column("card_price_snapshots", "tcgplayer_price")

    op.drop_column("collection_items", "cardmarket_price_label")
    op.drop_column("collection_items", "cardmarket_currency")
    op.drop_column("collection_items", "cardmarket_price")
    op.drop_column("collection_items", "tcgplayer_price_label")
    op.drop_column("collection_items", "tcgplayer_currency")
    op.drop_column("collection_items", "tcgplayer_price")
