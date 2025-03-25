"""Track model definitions."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from selecta.data.database import Base


class Track(Base):
    """Universal track model that serves as the central entity across platforms."""

    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    duration_ms = Column(Integer, nullable=True)

    # Path to local file if available
    local_path = Column(String(1024), nullable=True)

    # Relationships
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)
    album = relationship("Album", back_populates="tracks")

    platform_info = relationship(
        "TrackPlatformInfo", back_populates="track", cascade="all, delete-orphan"
    )

    # Many-to-many relationship with playlists through PlaylistTrack
    playlists = relationship("PlaylistTrack", back_populates="track", cascade="all, delete-orphan")

    # Many-to-many relationship with genres (through association)
    genres = relationship("Genre", secondary="track_genres", back_populates="tracks")

    # Many-to-many relationship with tags (through TrackTag)
    tags = relationship("TrackTag", back_populates="track", cascade="all, delete-orphan")

    # Track attributes (dynamic properties like energy, danceability)
    attributes = relationship(
        "TrackAttribute", back_populates="track", cascade="all, delete-orphan"
    )

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of Track.

        Returns:
            str: String representation
        """
        return f"<Track {self.id}: {self.artist} - {self.title}>"


class TrackPlatformInfo(Base):
    """Platform-specific information for a track."""

    __tablename__ = "track_platform_info"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # 'spotify', 'rekordbox', 'discogs'
    platform_id = Column(String(255), nullable=False)  # ID in the platform's system
    uri = Column(String(512), nullable=True)  # URI/URL to the track in the platform

    # Platform-specific metadata (JSON might be better, but using text for SQLite compatibility)
    # Renamed from 'metadata' to 'platform_data' to avoid conflicts with SQLAlchemy
    platform_data = Column(Text, nullable=True)

    # Relationships
    track = relationship("Track", back_populates="platform_info")

    # Ensure we don't have duplicates for the same track/platform combination
    __table_args__ = ({"sqlite_autoincrement": True},)

    def __repr__(self) -> str:
        """String representation of TrackPlatformInfo.

        Returns:
            str: String representation
        """
        return f"<TrackPlatformInfo {self.platform}:{self.platform_id}>"


class TrackAttribute(Base):
    """Dynamic attributes for tracks like energy, danceability, etc."""

    __tablename__ = "track_attributes"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    source = Column(String(50), nullable=True)  # e.g., 'spotify', 'user', 'analysis'

    # Relationships
    track = relationship("Track", back_populates="attributes")

    def __repr__(self) -> str:
        """String representation of TrackAttribute.

        Returns:
            str: String representation
        """
        return f"<TrackAttribute {self.name}: {self.value}>"
