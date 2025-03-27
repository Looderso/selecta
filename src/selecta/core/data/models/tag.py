"""Tag model definitions for custom user tags."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from selecta.core.data.database import Base


class Tag(Base):
    """User-defined tag model for organizing music."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    color = Column(String(20), nullable=True)  # Could store a hex color code

    # Tracks with this tag (through TrackTag)
    track_tags = relationship("TrackTag", back_populates="tag", cascade="all, delete-orphan")

    # Playlists with this tag (through PlaylistTag)
    playlist_tags = relationship("PlaylistTag", back_populates="tag", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of Tag.

        Returns:
            str: String representation
        """
        return f"<Tag {self.id}: {self.name}>"


class TrackTag(Base):
    """Association table for track-tag relationship."""

    __tablename__ = "track_tags"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    # When the tag was applied to the track
    tagged_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    track = relationship("Track", back_populates="tags")
    tag = relationship("Tag", back_populates="track_tags")

    def __repr__(self) -> str:
        """String representation of TrackTag.

        Returns:
            str: String representation
        """
        return f"<TrackTag: {self.track_id} - {self.tag_id}>"


class PlaylistTag(Base):
    """Association table for playlist-tag relationship."""

    __tablename__ = "playlist_tags"

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    # When the tag was applied to the playlist
    tagged_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    playlist = relationship("Playlist", back_populates="tags")
    tag = relationship("Tag", back_populates="playlist_tags")

    def __repr__(self) -> str:
        """String representation of PlaylistTag.

        Returns:
            str: String representation
        """
        return f"<PlaylistTag: {self.playlist_id} - {self.tag_id}>"
