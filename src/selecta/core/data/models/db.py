"""Core database models for Selecta."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from selecta.core.data.database import Base
from selecta.core.utils.type_helpers import is_column_truthy

# Association table for track-genre relationship
track_genres = Table(
    "track_genres",
    Base.metadata,
    Column("track_id", Integer, ForeignKey("tracks.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id"), primary_key=True),
)


"""Track model definitions."""


from sqlalchemy import Column, ForeignKey, Integer

from selecta.core.data.database import Base


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


class Album(Base):
    """Album model representing music albums."""

    __tablename__ = "albums"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    release_year = Column(Integer, nullable=True)

    # Album art URL or path
    artwork_url = Column(String(1024), nullable=True)

    # Additional album information
    label = Column(String(255), nullable=True)
    catalog_number = Column(String(100), nullable=True)

    # Related vinyl record (if any)
    vinyl_id = Column(Integer, ForeignKey("vinyl_records.id"), nullable=True)
    vinyl = relationship("Vinyl", back_populates="album")

    # Tracks in the album
    tracks = relationship("Track", back_populates="album")

    def __repr__(self) -> str:
        """String representation of Album."""
        return f"<Album {self.id}: {self.artist} - {self.title}>"


class Vinyl(Base):
    """Vinyl record model representing physical records in collection."""

    __tablename__ = "vinyl_records"

    id = Column(Integer, primary_key=True)

    # Discogs specific fields
    discogs_id = Column(Integer, nullable=True)
    discogs_release_id = Column(Integer, nullable=True)

    # Vinyl status
    is_owned = Column(Boolean, default=False)
    is_wanted = Column(Boolean, default=False)
    for_sale = Column(Boolean, default=False)

    # Purchase details
    purchase_date = Column(DateTime, nullable=True)
    purchase_price = Column(Float, nullable=True)
    purchase_currency = Column(String(3), nullable=True)
    purchase_notes = Column(Text, nullable=True)

    # Condition
    media_condition = Column(String(50), nullable=True)  # e.g., 'Mint', 'Very Good Plus'
    sleeve_condition = Column(String(50), nullable=True)

    # Related album
    album = relationship("Album", back_populates="vinyl", uselist=False)

    # Notes
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of Vinyl."""
        album_title = self.album.title if self.album else "Unknown"
        return f"<Vinyl {self.id}: {album_title} (Discogs ID: {self.discogs_id})>"


class Genre(Base):
    """Genre model representing music genres."""

    __tablename__ = "genres"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    source = Column(String(50), nullable=True)  # e.g., 'spotify', 'discogs', 'user'

    # Tracks with this genre
    tracks = relationship("Track", secondary=track_genres, back_populates="genres")

    def __repr__(self) -> str:
        """String representation of Genre."""
        return f"<Genre {self.id}: {self.name} ({self.source})>"


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

    # For folder structure support
    parent_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    is_folder = Column(Boolean, default=False)
    position = Column(Integer, default=0)  # Position within parent

    # Synchronization settings
    sync_enabled = Column(Boolean, default=True)
    last_synced = Column(DateTime, nullable=True)

    # Relationships
    children = relationship(
        "Playlist", backref="parent", remote_side=[id], cascade="all, delete-orphan"
    )

    # Tracks in the playlist
    tracks = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of Playlist."""
        folder_str = " (Folder)" if self.is_folder else ""  # type: ignore
        return f"<Playlist {self.id}: {self.name}{folder_str}>"


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
        """String representation of PlaylistTrack."""
        return f"<PlaylistTrack #{self.position} in playlist {self.playlist_id}>"


class PlatformCredentials(Base):
    """Credentials for external platforms like Spotify, Discogs."""

    __tablename__ = "platform_credentials"

    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False, unique=True)  # 'spotify', 'discogs', 'rekordbox'

    # OAuth2 credentials
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)

    # Rekordbox database path (for rekordbox platform)
    db_path = Column(String(1024), nullable=True)

    # Token expiration
    token_expiry = Column(DateTime, nullable=True)

    # When credentials were last updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of PlatformCredentials."""
        return f"<Credentials for {self.platform}>"

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token is expired.

        Returns:
            bool: True if token is expired or missing
        """
        if not is_column_truthy(self.access_token) or not is_column_truthy(self.token_expiry):
            return True

        return datetime.utcnow() > self.token_expiry  # type: ignore


class UserSettings(Base):
    """User preferences and application settings."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    data_type = Column(
        String(20), nullable=False, default="string"
    )  # 'string', 'boolean', 'integer', 'json'

    # Optional description of what this setting controls
    description = Column(String(255), nullable=True)

    # Whether this setting can be modified via the UI
    user_editable = Column(Boolean, default=True)

    def __repr__(self) -> str:
        """String representation of UserSettings.

        Returns:
            str: String representation
        """
        return f"<Setting {self.key}: {self.value}>"

    @property
    def typed_value(self) -> bool | int | dict | str | None:
        """Return the setting value converted to its appropriate type.

        Returns:
            The value in its native Python type
        """
        if self.value is None:
            return None

        if self.data_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.data_type == "integer":
            return int(self.value)
        elif self.data_type == "json":
            import json

            return json.loads(self.value)
        else:  # default to string
            return self.value
