"""Track repository for database operations."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Genre, Tag, Track, TrackAttribute, TrackPlatformInfo
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
        return (
            self.session.query(Track)
            .options(
                joinedload(Track.platform_info),
                joinedload(Track.genres),
                joinedload(Track.tags),
            )
            .filter(Track.id == track_id)
            .first()
        )

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
            .options(
                joinedload(Track.platform_info),
                joinedload(Track.genres),
                joinedload(Track.tags),
            )
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
        tracks = (
            base_query.options(joinedload(Track.platform_info))
            .order_by(Track.artist, Track.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

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

    def update(self, track_id: int, track_data: dict[str, Any], preserve_existing: bool = True) -> Track | None:
        """Update an existing track.

        Args:
            track_id: The track ID
            track_data: Dictionary with updated track data
            preserve_existing: If True, only update fields that are empty or None in the existing track

        Returns:
            The updated track if found, None otherwise
        """
        track = self.get_by_id(track_id)
        if not track:
            return None

        # Update track attributes
        for key, value in track_data.items():
            # Skip None values always
            if value is None:
                continue
                
            # If preserving existing values, only update if the current value is None/empty
            if preserve_existing:
                current_value = getattr(track, key, None)
                # Skip if current value exists and:
                # - It's a string with content
                # - It's a number greater than zero
                # - It's any other non-None value
                if current_value is not None:
                    if isinstance(current_value, str) and current_value.strip():
                        continue
                    if isinstance(current_value, (int, float)) and current_value > 0:
                        continue
                    if not isinstance(current_value, (str, int, float)) and current_value:
                        continue
            
            # Set the value if we didn't skip it
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
        info.last_linked = datetime.now(UTC)
        info.needs_update = False
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
            # Update link timestamp
            existing.last_linked = datetime.now(UTC)
            existing.needs_update = False

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

    def mark_platform_info_for_update(self, track_id: int, platform: str) -> bool:
        """Mark platform info as needing an update.

        Args:
            track_id: The track ID
            platform: The platform name

        Returns:
            True if marked, False if not found
        """
        if self.session is None:
            return False

        info = self.get_platform_info(track_id, platform)
        if not info:
            return False

        info.needs_update = True
        self.session.commit()
        return True

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

    def get_platform_metadata(self, track_id: int, platform: str) -> dict[str, Any] | None:
        """Get parsed metadata for a specific platform.

        Args:
            track_id: The track ID
            platform: The platform name

        Returns:
            Dictionary of metadata or None if not available
        """
        info = self.get_platform_info(track_id, platform)
        if not info or not info.platform_data:
            return None

        try:
            return json.loads(info.platform_data)
        except json.JSONDecodeError:
            return None

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

    def get_tracks_needing_update(self, platform: str, limit: int = 100) -> list[Track]:
        """Get tracks that need platform metadata updates.

        Args:
            platform: The platform name
            limit: Maximum number of tracks to return

        Returns:
            List of tracks needing updates
        """
        if self.session is None:
            return []

        return (
            self.session.query(Track)
            .join(TrackPlatformInfo)
            .options(
                joinedload(Track.platform_info),
                joinedload(Track.genres),
            )
            .filter(
                TrackPlatformInfo.platform == platform,
                TrackPlatformInfo.needs_update == True,  # noqa: E712
            )
            .limit(limit)
            .all()
        )

    def update_track_from_platform(self, track_id: int, platform: str, fields: list[str]) -> bool:
        """Update track fields using data from a specific platform.

        Args:
            track_id: The track ID
            platform: The platform to use as source
            fields: List of fields to update

        Returns:
            True if successful, False otherwise
        """
        track = self.get_by_id(track_id)
        if not track:
            return False

        # Use the track's method to update from platform
        updated = track.update_from_platform(platform, fields)

        if updated and self.session:
            self.session.commit()

        return updated

    def get_or_create_tag(self, name: str, description: str | None = None) -> Tag:
        """Get an existing tag or create a new one.

        Args:
            name: Tag name
            description: Optional tag description

        Returns:
            The tag instance
        """
        if self.session is None:
            raise ValueError("Session is required for tag operations")

        tag = self.session.query(Tag).filter(Tag.name == name).first()

        if not tag:
            tag = Tag(name=name, description=description)
            self.session.add(tag)
            self.session.commit()

        return tag

    def add_tag_to_track(self, track_id: int, tag_name: str) -> bool:
        """Add a tag to a track.

        Args:
            track_id: The track ID
            tag_name: Name of the tag to add

        Returns:
            True if successful, False otherwise
        """
        if self.session is None:
            return False

        track = self.get_by_id(track_id)
        if not track:
            return False

        # Get or create the tag
        tag = self.get_or_create_tag(tag_name)

        # Check if the track already has this tag
        if tag in track.tags:
            return True

        # Add the tag to the track
        track.tags.append(tag)
        self.session.commit()
        return True

    def remove_tag_from_track(self, track_id: int, tag_name: str) -> bool:
        """Remove a tag from a track.

        Args:
            track_id: The track ID
            tag_name: Name of the tag to remove

        Returns:
            True if successful, False otherwise
        """
        if self.session is None:
            return False

        track = self.get_by_id(track_id)
        if not track:
            return False

        # Find the tag
        tag = self.session.query(Tag).filter(Tag.name == tag_name).first()
        if not tag or tag not in track.tags:
            return False

        # Remove the tag from the track
        track.tags.remove(tag)
        self.session.commit()
        return True

    def get_or_create_genre(self, name: str, source: str | None = None) -> Genre:
        """Get an existing genre or create a new one.

        Args:
            name: Genre name
            source: Optional source (e.g., 'spotify', 'discogs')

        Returns:
            The genre instance
        """
        if self.session is None:
            raise ValueError("Session is required for genre operations")

        genre = self.session.query(Genre).filter(Genre.name == name).first()

        if not genre:
            genre = Genre(name=name, source=source)
            self.session.add(genre)
            self.session.commit()

        return genre

    def set_track_genres(
        self, track_id: int, genre_names: list[str], source: str | None = None
    ) -> bool:
        """Set the genres for a track (replacing existing ones with the same source).

        Args:
            track_id: The track ID
            genre_names: List of genre names
            source: Optional source of the genres

        Returns:
            True if successful, False otherwise
        """
        if self.session is None:
            return False

        track = self.get_by_id(track_id)
        if not track:
            return False

        # If a source is provided, remove all genres from that source
        if source:
            # Get the current genres
            current_genres = [g for g in track.genres if g.source == source]
            for genre in current_genres:
                track.genres.remove(genre)

        # Add the new genres
        for name in genre_names:
            genre = self.get_or_create_genre(name, source)
            if genre not in track.genres:
                track.genres.append(genre)

        self.session.commit()
        return True

    def get_tracks_by_tag(
        self, tag_name: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[Track], int]:
        """Get tracks with a specific tag.

        Args:
            tag_name: The tag name
            limit: Maximum number of tracks to return
            offset: Number of tracks to skip

        Returns:
            Tuple of (list of tracks, total count)
        """
        if self.session is None:
            return [], 0

        base_query = self.session.query(Track).join(Track.tags).filter(Tag.name == tag_name)

        total = base_query.count()

        tracks = (
            base_query.options(joinedload(Track.platform_info))
            .order_by(Track.artist, Track.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return tracks, total

    def get_tracks_by_genre(
        self, genre_name: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[Track], int]:
        """Get tracks with a specific genre.

        Args:
            genre_name: The genre name
            limit: Maximum number of tracks to return
            offset: Number of tracks to skip

        Returns:
            Tuple of (list of tracks, total count)
        """
        if self.session is None:
            return [], 0

        base_query = self.session.query(Track).join(Track.genres).filter(Genre.name == genre_name)

        total = base_query.count()

        tracks = (
            base_query.options(joinedload(Track.platform_info))
            .order_by(Track.artist, Track.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return tracks, total

    def get_tracks_by_platform(
        self, platform: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[Track], int]:
        """Get tracks that have info from a specific platform.

        Args:
            platform: The platform name
            limit: Maximum number of tracks to return
            offset: Number of tracks to skip

        Returns:
            Tuple of (list of tracks, total count)
        """
        if self.session is None:
            return [], 0

        base_query = (
            self.session.query(Track)
            .join(TrackPlatformInfo)
            .filter(TrackPlatformInfo.platform == platform)
        )

        total = base_query.count()

        tracks = (
            base_query.options(joinedload(Track.platform_info))
            .order_by(Track.artist, Track.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return tracks, total

    def set_track_quality(self, track_id: int, quality: int) -> bool:
        """Set the quality rating for a track.

        Args:
            track_id: The track ID
            quality: Rating value (-1=not rated, 1-5=star rating)

        Returns:
            True if successful, False otherwise
        """
        from loguru import logger

        if self.session is None:
            logger.warning("Cannot set track quality: No database session available")
            return False

        track = self.get_by_id(track_id)
        if not track:
            logger.warning(f"Cannot set track quality: Track with ID {track_id} not found")
            return False

        # Validate quality value
        if quality not in [Track.NOT_RATED, 1, 2, 3, 4, 5]:
            logger.warning(f"Invalid quality value {quality}, must be -1 or 1-5")
            return False

        logger.debug(
            f"Setting quality for track {track_id} ({track.artist} - {track.title}) to {quality}"
        )
        track.quality = quality
        self.session.commit()
        logger.info(f"Track quality updated: Track ID {track_id} quality={quality}")
        return True

    def get_tracks_by_quality(
        self, quality: int, limit: int = 50, offset: int = 0
    ) -> tuple[list[Track], int]:
        """Get tracks with a specific quality rating.

        Args:
            quality: The quality rating to filter by (-1=not rated, 1-5=star rating)
            limit: Maximum number of tracks to return
            offset: Number of tracks to skip

        Returns:
            Tuple of (list of tracks, total count)
        """
        if self.session is None:
            return [], 0

        base_query = self.session.query(Track).filter(Track.quality == quality)

        total = base_query.count()

        tracks = (
            base_query.options(joinedload(Track.platform_info))
            .order_by(Track.artist, Track.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return tracks, total

    def get_all_with_local_path(self) -> list[Track]:
        """Get all tracks that have a local file path.

        Returns:
            List of tracks with local paths
        """
        if self.session is None:
            return []

        return (
            self.session.query(Track)
            .filter(Track.local_path.isnot(None))
            .filter(Track.local_path != "")
            .order_by(Track.artist, Track.title)
            .all()
        )
