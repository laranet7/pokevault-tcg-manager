"""collection owners and collaborators"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0009"
down_revision = "20260626_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collections", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_collections_owner_user_id"), "collections", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_collections_owner_user_id_users",
        "collections",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "collection_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "user_id", name="uq_collection_members_collection_user"),
    )
    op.create_index(op.f("ix_collection_members_id"), "collection_members", ["id"], unique=False)
    op.create_index(op.f("ix_collection_members_collection_id"), "collection_members", ["collection_id"], unique=False)
    op.create_index(op.f("ix_collection_members_user_id"), "collection_members", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_collection_members_user_id"), table_name="collection_members")
    op.drop_index(op.f("ix_collection_members_collection_id"), table_name="collection_members")
    op.drop_index(op.f("ix_collection_members_id"), table_name="collection_members")
    op.drop_table("collection_members")

    op.drop_constraint("fk_collections_owner_user_id_users", "collections", type_="foreignkey")
    op.drop_index(op.f("ix_collections_owner_user_id"), table_name="collections")
    op.drop_column("collections", "owner_user_id")
