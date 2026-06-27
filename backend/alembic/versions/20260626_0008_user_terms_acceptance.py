"""user terms acceptance fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0008"
down_revision = "20260625_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_ip", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_user_agent", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_user_agent")
    op.drop_column("users", "terms_accepted_ip")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
