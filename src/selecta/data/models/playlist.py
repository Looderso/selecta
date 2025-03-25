"""Playlist model definitions."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from selecta.data.database import Base


class Playlist(Base):
    """Universal playlist model representing playlists across platforms."""

    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Whether this is a user-created playlist in Selecta or imported from a platform
    is_local = Column(Boolean, default=False)

    # If not local, store platform information
    source_platform = Column(String(50), nullable=True)  # 'spotify', 'rekordbox', null for local
    platform_id = Column(String(255), nullable=True)  # ID in the platform's system

    # Synchronization settings
    sync_enabled = Column(Boolean, default=True)
    last_synced = Column(DateTime, nullable=True)

    # Relationships - tracks in the playlist
    tracks = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )

    # Relationships - tags
    tags = relationship("PlaylistTag", back_populates="playlist", cascade="all, delete-orphan")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of Playlist.

        Returns:
            str: String representation
        """
        return f"<Playlist {self.id}: {self.name}>"


class PlaylistTrack(Base):
    """Association table between playlists and tracks with ordering."""

    __tablename__ = "playlist_tracks"

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, nullable=False)  # Track position in playlist

    # When the track was added to the playlist
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    playlist = relationship("Playlist", back_populates="tracks")
    track = relationship("Track", back_populates="playlists")

    def __repr__(self) -> str:
        """String representation of PlaylistTrack.

        Returns:
            str: String representation
        """
        return f"<PlaylistTrack #{self.position} in playlist {self.playlist_id}>"
