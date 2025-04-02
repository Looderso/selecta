"""Core database models for Selecta."""

from datetime import datetime
from typing import Any, ClassVar, Optional, cast

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Path to local file if available
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    album_id: Mapped[int | None] = mapped_column(ForeignKey("albums.id"), nullable=True)
    album: Mapped[Optional["Album"]] = relationship("Album", back_populates="tracks")

    platform_info: Mapped[list["TrackPlatformInfo"]] = relationship(
        "TrackPlatformInfo", back_populates="track", cascade="all, delete-orphan"
    )

    # Many-to-many relationship with playlists through PlaylistTrack
    playlists: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="track", cascade="all, delete-orphan"
    )

    # Many-to-many relationship with genres (through association)
    genres: Mapped[list["Genre"]] = relationship(
        "Genre", secondary="track_genres", back_populates="tracks"
    )

    # Track attributes (dynamic properties like energy, danceability)
    attributes: Mapped[list["TrackAttribute"]] = relationship(
        "TrackAttribute", back_populates="track", cascade="all, delete-orphan"
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of Track.

        Returns:
            str: String representation
        """
        return f"<Track {self.id}: {self.artist} - {self.title}>"


class TrackPlatformInfo(Base):
    """Platform-specific information for a track."""

    __tablename__ = "track_platform_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    # 'spotify', 'rekordbox', 'discogs'
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    # ID in the platform's system
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # URI/URL to the track in the platform
    uri: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Platform-specific metadata (JSON might be better, but using text for SQLite compatibility)
    # Renamed from 'metadata' to 'platform_data' to avoid conflicts with SQLAlchemy
    platform_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    track: Mapped["Track"] = relationship("Track", back_populates="platform_info")

    # For SQLAlchemy 2.0, help typechecking with __init__ key mapping for constructor
    __init_key_mapping__: ClassVar[dict[str, str]] = {
        "track_id": "track_id",
        "platform": "platform",
        "platform_id": "platform_id",
        "uri": "uri",
        "platform_data": "platform_data",
    }

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

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    # e.g., 'spotify', 'user', 'analysis'
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    track: Mapped["Track"] = relationship("Track", back_populates="attributes")

    # For SQLAlchemy 2.0, help typechecking with __init__ key mapping for constructor
    __init_key_mapping__: ClassVar[dict[str, str]] = {
        "track_id": "track_id",
        "name": "name",
        "value": "value",
        "source": "source",
    }

    def __repr__(self) -> str:
        """String representation of TrackAttribute.

        Returns:
            str: String representation
        """
        return f"<TrackAttribute {self.name}: {self.value}>"


class Album(Base):
    """Album model representing music albums."""

    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Album art URL or path
    artwork_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Additional album information
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    catalog_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Related vinyl record (if any)
    vinyl_id: Mapped[int | None] = mapped_column(ForeignKey("vinyl_records.id"), nullable=True)
    vinyl: Mapped[Optional["Vinyl"]] = relationship("Vinyl", back_populates="album")

    # Tracks in the album
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="album")

    def __repr__(self) -> str:
        """String representation of Album."""
        return f"<Album {self.id}: {self.artist} - {self.title}>"


class Vinyl(Base):
    """Vinyl record model representing physical records in collection."""

    __tablename__ = "vinyl_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Discogs specific fields
    discogs_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discogs_release_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Vinyl status
    is_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_wanted: Mapped[bool] = mapped_column(Boolean, default=False)
    for_sale: Mapped[bool] = mapped_column(Boolean, default=False)

    # Purchase details
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchase_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    purchase_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Condition
    # e.g., 'Mint', 'Very Good Plus'
    media_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sleeve_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Related album
    album: Mapped[Optional["Album"]] = relationship("Album", back_populates="vinyl", uselist=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of Vinyl."""
        album_title = self.album.title if self.album else "Unknown"
        return f"<Vinyl {self.id}: {album_title} (Discogs ID: {self.discogs_id})>"


class Genre(Base):
    """Genre model representing music genres."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # e.g., 'spotify', 'discogs', 'user'
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Tracks with this genre
    tracks: Mapped[list["Track"]] = relationship(
        "Track", secondary=track_genres, back_populates="genres"
    )

    def __repr__(self) -> str:
        """String representation of Genre."""
        return f"<Genre {self.id}: {self.name} ({self.source})>"


class Playlist(Base):
    """Universal playlist model representing playlists across platforms."""

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Whether this is a user-created playlist in Selecta or imported from a platform
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)

    # If not local, store platform information
    # 'spotify', 'rekordbox', null for local
    source_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # ID in the platform's system
    platform_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # For folder structure support
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("playlists.id"), nullable=True)
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)  # Position within parent

    # Synchronization settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    children: Mapped[list["Playlist"]] = relationship(
        "Playlist",
        backref="parent",
        remote_side=[id],
        cascade="all, delete-orphan",
        single_parent=True,  # Add this line to fix the cascade issue
    )

    # Tracks in the playlist
    tracks: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistTrack.position",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of Playlist."""
        folder_str = " (Folder)" if self.is_folder else ""
        return f"<Playlist {self.id}: {self.name}{folder_str}>"


class PlaylistTrack(Base):
    """Association table between playlists and tracks with ordering."""

    __tablename__ = "playlist_tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), nullable=False)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)  # Track position in playlist

    # When the track was added to the playlist
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    playlist: Mapped["Playlist"] = relationship("Playlist", back_populates="tracks")
    track: Mapped["Track"] = relationship("Track", back_populates="playlists")

    def __repr__(self) -> str:
        """String representation of PlaylistTrack."""
        return f"<PlaylistTrack #{self.position} in playlist {self.playlist_id}>"


class PlatformCredentials(Base):
    """Credentials for external platforms like Spotify, Discogs."""

    __tablename__ = "platform_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 'spotify', 'discogs', 'rekordbox'
    platform: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # OAuth2 credentials
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rekordbox database path (for rekordbox platform)
    db_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Token expiration
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # When credentials were last updated
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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

        if self.token_expiry is None:
            return True

        return datetime.utcnow() > self.token_expiry


class UserSettings(Base):
    """User preferences and application settings."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'string', 'boolean', 'integer', 'json'
    data_type: Mapped[str] = mapped_column(String(20), nullable=False, default="string")

    # Optional description of what this setting controls
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Whether this setting can be modified via the UI
    user_editable: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        """String representation of UserSettings.

        Returns:
            str: String representation
        """
        return f"<Setting {self.key}: {self.value}>"

    @property
    def typed_value(self) -> bool | int | dict[str, Any] | str | None:
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

            # Cast the result to avoid the "Any" return type
            return cast(dict[str, Any], json.loads(self.value))
        else:  # default to string
            return self.value
