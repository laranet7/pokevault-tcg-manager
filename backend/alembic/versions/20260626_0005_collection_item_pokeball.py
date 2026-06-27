"""collection item pokeball toggle"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0005"
down_revision = "20260626_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collection_items",
        sa.Column("is_pokeball", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "card_price_snapshots",
        sa.Column("is_pokeball", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("collection_items", "is_pokeball", server_default=None)
    op.alter_column("card_price_snapshots", "is_pokeball", server_default=None)


def downgrade() -> None:
    op.drop_column("card_price_snapshots", "is_pokeball")
    op.drop_column("collection_items", "is_pokeball")
