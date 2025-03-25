"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2024-03-25

"""

from alembic import op

# Revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    # This is handled by SQLAlchemy's create_all()
    pass


def downgrade() -> None:
    """Revert to empty database."""
    # Drop all tables in reverse dependency order
    op.drop_table("playlist_tags")
    op.drop_table("track_tags")
    op.drop_table("track_genres")
    op.drop_table("track_attributes")
    op.drop_table("track_platform_info")
    op.drop_table("playlist_tracks")
    op.drop_table("tags")
    op.drop_table("genres")
    op.drop_table("tracks")
    op.drop_table("playlists")
    op.drop_table("vinyl_records")
    op.drop_table("albums")
    op.drop_table("platform_credentials")
    op.drop_table("user_settings")
