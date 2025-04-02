"""Add image storage model.

Revision ID: 003
Revises: 002
Create Date: 2024-04-02

"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add image storage model to database."""
    # Create enum type for image sizes
    image_size_enum = sa.Enum("THUMBNAIL", "SMALL", "MEDIUM", "LARGE", name="imagesize")
    image_size_enum.create(op.get_bind())

    # Create images table
    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="image/jpeg"),
        sa.Column("size", image_size_enum, nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("album_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for faster lookups
    op.create_index("ix_images_track_id", "images", ["track_id"])
    op.create_index("ix_images_album_id", "images", ["album_id"])
    op.create_index("ix_images_size", "images", ["size"])


def downgrade() -> None:
    """Revert database changes."""
    # Drop indexes
    op.drop_index("ix_images_size", "images")
    op.drop_index("ix_images_album_id", "images")
    op.drop_index("ix_images_track_id", "images")

    # Drop images table
    op.drop_table("images")

    # Drop enum type
    op.execute("DROP TYPE imagesize")
