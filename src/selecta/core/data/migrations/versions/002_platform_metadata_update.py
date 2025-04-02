"""Add platform metadata and tag support.

Revision ID: 002
Revises: 001
Create Date: 2024-04-02

"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update database for improved platform metadata handling."""
    # Add new fields to Track table
    op.add_column("tracks", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("tracks", sa.Column("bpm", sa.Float(), nullable=True))
    op.add_column("tracks", sa.Column("artwork_url", sa.String(1024), nullable=True))
    op.add_column(
        "tracks",
        sa.Column("is_available_locally", sa.Boolean(), server_default="0", nullable=False),
    )

    # Add new fields to TrackPlatformInfo
    op.add_column("track_platform_info", sa.Column("last_synced", sa.DateTime(), nullable=True))
    op.add_column(
        "track_platform_info",
        sa.Column("needs_update", sa.Boolean(), server_default="0", nullable=False),
    )

    # Create Tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create association table for Track-Tag relationship
    op.create_table(
        "track_tags",
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("track_id", "tag_id"),
    )


def downgrade() -> None:
    """Revert database changes."""
    # Drop association table
    op.drop_table("track_tags")

    # Drop tags table
    op.drop_table("tags")

    # Remove added columns from TrackPlatformInfo
    op.drop_column("track_platform_info", "needs_update")
    op.drop_column("track_platform_info", "last_synced")

    # Remove added columns from Track
    op.drop_column("tracks", "is_available_locally")
    op.drop_column("tracks", "artwork_url")
    op.drop_column("tracks", "bpm")
    op.drop_column("tracks", "year")
