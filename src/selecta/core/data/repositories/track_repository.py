"""Track repository for database operations."""

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Track, TrackAttribute, TrackPlatformInfo
from selecta.core.data.types import BaseRepository


class TrackRepository(BaseRepository[Track]):
    """Repository for track-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()
        super().__init__(Track, self.session)

    def get_by_id(self, track_id: int) -> Track | None:
        """Get a track by its ID.

        Args:
            track_id: The track ID

        Returns:
            The track if found, None otherwise
        """
        if self.session is None:
            return None
        return self.session.query(Track).filter(Track.id == track_id).first()

    def get_by_platform_id(self, platform: str, platform_id: str) -> Track | None:
        """Get a track by its platform-specific ID.

        Args:
            platform: The platform name (e.g., 'spotify', 'rekordbox')
            platform_id: The ID in the platform's system

        Returns:
            The track if found, None otherwise
        """
        if self.session is None:
            return None
        return (
            self.session.query(Track)
            .join(TrackPlatformInfo)
            .filter(
                TrackPlatformInfo.platform == platform,
                TrackPlatformInfo.platform_id == platform_id,
            )
            .first()
        )

    def search(self, query: str, limit: int = 50, offset: int = 0) -> tuple[list[Track], int]:
        """Search for tracks by title or artist.

        Args:
            query: The search query
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of tracks, total count)
        """
        if self.session is None:
            return [], 0

        # Prepare search terms
        search_term = f"%{query}%"

        # Build the query
        base_query = self.session.query(Track).filter(
            or_(Track.title.ilike(search_term), Track.artist.ilike(search_term))
        )

        # Get total count
        total = base_query.count()

        # Get paginated results
        tracks = base_query.order_by(Track.artist, Track.title).limit(limit).offset(offset).all()

        return tracks, total

    def create(self, track_data: dict[str, Any]) -> Track:
        """Create a new track.

        Args:
            track_data: Dictionary with track data

        Returns:
            The created track
        """
        if self.session is None:
            raise ValueError("Session is required for creating a track")

        track = Track(**track_data)
        self.session.add(track)
        self.session.commit()
        return track

    def update(self, track_id: int, track_data: dict[str, Any]) -> Track | None:
        """Update an existing track.

        Args:
            track_id: The track ID
            track_data: Dictionary with updated track data

        Returns:
            The updated track if found, None otherwise
        """
        track = self.get_by_id(track_id)
        if not track:
            return None

        # Update track attributes
        for key, value in track_data.items():
            setattr(track, key, value)

        if self.session:
            self.session.commit()
        return track

    def delete(self, track_id: int) -> bool:
        """Delete a track by its ID.

        Args:
            track_id: The track ID

        Returns:
            True if deleted, False if not found
        """
        if self.session is None:
            return False

        track = self.get_by_id(track_id)
        if not track:
            return False

        self.session.delete(track)
        self.session.commit()
        return True

    def _create_platform_info(
        self,
        track_id: int,
        platform: str,
        platform_id: str,
        uri: str | None = None,
        metadata: str | None = None,
    ) -> TrackPlatformInfo:
        """Create a new TrackPlatformInfo object with proper typing."""
        # This bypasses the type checking issues with SQLAlchemy models
        info = TrackPlatformInfo()
        info.track_id = track_id
        info.platform = platform
        info.platform_id = platform_id
        info.uri = uri
        info.platform_data = metadata
        return info

    def add_platform_info(
        self,
        track_id: int,
        platform: str,
        platform_id: str,
        uri: str | None = None,
        metadata: str | None = None,
    ) -> TrackPlatformInfo:
        """Add platform-specific information to a track.

        Args:
            track_id: The track ID
            platform: The platform name (e.g., 'spotify', 'rekordbox', 'discogs')
            platform_id: The ID in the platform's system
            uri: Optional URI/URL to the track in the platform
            metadata: Optional JSON string with additional metadata

        Returns:
            The created platform info object
        """
        if self.session is None:
            raise ValueError("Session is required for adding platform info")

        # Check if this platform info already exists
        existing = (
            self.session.query(TrackPlatformInfo)
            .filter(
                TrackPlatformInfo.track_id == track_id,
                TrackPlatformInfo.platform == platform,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.platform_id = platform_id
            if uri is not None:
                existing.uri = uri
            if metadata is not None:
                # Use platform_data instead of metadata
                existing.platform_data = metadata
            self.session.commit()
            return existing

        # Create new using our factory method
        info = self._create_platform_info(
            track_id=track_id,
            platform=platform,
            platform_id=platform_id,
            uri=uri,
            metadata=metadata,
        )
        self.session.add(info)
        self.session.commit()
        return info

    def _create_track_attribute(
        self, track_id: int, name: str, value: float, source: str | None = None
    ) -> TrackAttribute:
        """Create a new TrackAttribute object with proper typing."""
        # This bypasses the type checking issues with SQLAlchemy models
        attribute = TrackAttribute()
        attribute.track_id = track_id
        attribute.name = name
        attribute.value = value
        attribute.source = source
        return attribute

    def add_attribute(
        self, track_id: int, name: str, value: float, source: str | None = None
    ) -> TrackAttribute:
        """Add or update a track attribute.

        Args:
            track_id: The track ID
            name: Attribute name (e.g., 'energy', 'danceability')
            value: Attribute value (0.0-1.0 scale)
            source: Source of the attribute (e.g., 'spotify', 'user')

        Returns:
            The created/updated attribute
        """
        if self.session is None:
            raise ValueError("Session is required for adding track attribute")

        # Check if this attribute already exists
        existing = (
            self.session.query(TrackAttribute)
            .filter(TrackAttribute.track_id == track_id, TrackAttribute.name == name)
            .first()
        )

        if existing:
            # Update existing
            existing.value = value
            if source is not None:
                existing.source = source
            self.session.commit()
            return existing

        # Create new using our factory method
        attribute = self._create_track_attribute(
            track_id=track_id, name=name, value=value, source=source
        )
        self.session.add(attribute)
        self.session.commit()
        return attribute

    def get_all_attributes(self, track_id: int) -> list[TrackAttribute]:
        """Get all attributes for a track.

        Args:
            track_id: The track ID

        Returns:
            List of track attributes
        """
        if self.session is None:
            return []

        return self.session.query(TrackAttribute).filter(TrackAttribute.track_id == track_id).all()

    def get_platform_info(self, track_id: int, platform: str) -> TrackPlatformInfo | None:
        """Get platform-specific information for a track.

        Args:
            track_id: The track ID
            platform: The platform name

        Returns:
            Platform info if found, None otherwise
        """
        if self.session is None:
            return None

        return (
            self.session.query(TrackPlatformInfo)
            .filter(
                TrackPlatformInfo.track_id == track_id,
                TrackPlatformInfo.platform == platform,
            )
            .first()
        )

    def get_all_platform_info(self, track_id: int) -> list[TrackPlatformInfo]:
        """Get all platform information for a track.

        Args:
            track_id: The track ID

        Returns:
            List of platform info objects
        """
        if self.session is None:
            return []

        return (
            self.session.query(TrackPlatformInfo)
            .filter(TrackPlatformInfo.track_id == track_id)
            .all()
        )
