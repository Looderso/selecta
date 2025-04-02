"""Add quality field to tracks.

Revision ID: 004
Revises: 003
Create Date: 2024-04-02

"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add quality field to tracks table."""
    # Add quality column with default NOT_RATED (-1)
    # Quality values will be:
    # -1: NOT_RATED
    # 1-5: Rating from 1 to 5 stars
    op.add_column("tracks", sa.Column("quality", sa.Integer(), nullable=False, server_default="-1"))

    # Create index for faster filtering by quality
    op.create_index("ix_tracks_quality", "tracks", ["quality"])


def downgrade() -> None:
    """Revert database changes."""
    # Drop index
    op.drop_index("ix_tracks_quality", "tracks")

    # Drop quality column
    op.drop_column("tracks", "quality")
