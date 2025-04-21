"""Add PlaylistPlatformInfo model.

Revision ID: 005
Revises: 004_add_track_quality
Create Date: 2023-04-19

This migration adds the PlaylistPlatformInfo model which allows playlists to be associated with
multiple platforms simultaneously, enabling better cross-platform synchronization.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004_add_track_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create playlist_platform_info table."""
    # Create the playlist_platform_info table
    op.create_table(
        "playlist_platform_info",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("playlist_id", sa.Integer(), sa.ForeignKey("playlists.id"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("platform_id", sa.String(255), nullable=False),
        sa.Column("uri", sa.String(512), nullable=True),
        sa.Column("platform_data", sa.Text(), nullable=True),
        sa.Column("last_linked", sa.DateTime(), default=lambda: datetime.now(UTC)),
        sa.Column("needs_update", sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint("id"),
        sqlite_autoincrement=True,
    )

    # Create an index on playlist_id and platform to speed up lookups
    op.create_index(
        "idx_playlist_platform_info_playlist_platform",
        "playlist_platform_info",
        ["playlist_id", "platform"],
        unique=False,
    )

    # Migrate existing data: Copy platform information from playlists to playlist_platform_info
    # This SQL will copy data from existing playlists with source_platform and platform_id
    # to the new playlist_platform_info table

    op.execute("""
        INSERT INTO playlist_platform_info
        (playlist_id, platform, platform_id, last_linked)
        SELECT
            id,
            source_platform,
            platform_id,
            last_synced
        FROM
            playlists
        WHERE
            source_platform IS NOT NULL
            AND platform_id IS NOT NULL
    """)


def downgrade() -> None:
    """Remove the playlist_platform_info table."""
    op.drop_index("idx_playlist_platform_info_playlist_platform")
    op.drop_table("playlist_platform_info")
