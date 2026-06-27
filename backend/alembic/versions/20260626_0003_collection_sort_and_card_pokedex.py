"""collection sort and card pokedex fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0003"
down_revision = "20260625_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("supertype", sa.String(length=100), nullable=True))
    op.add_column("cards", sa.Column("pokedex_number", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_cards_pokedex_number"), "cards", ["pokedex_number"], unique=False)

    op.add_column(
        "collections",
        sa.Column("sort_by_pokedex", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("collections", "sort_by_pokedex", server_default=None)


def downgrade() -> None:
    op.drop_column("collections", "sort_by_pokedex")
    op.drop_index(op.f("ix_cards_pokedex_number"), table_name="cards")
    op.drop_column("cards", "pokedex_number")
    op.drop_column("cards", "supertype")
