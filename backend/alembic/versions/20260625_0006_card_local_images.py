"""card local image paths"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0006"
down_revision = "20260626_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("local_image_small_path", sa.String(length=500), nullable=True))
    op.add_column("cards", sa.Column("local_image_large_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "local_image_large_path")
    op.drop_column("cards", "local_image_small_path")
