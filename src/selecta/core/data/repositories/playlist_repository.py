"""Playlist repository for database operations."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Playlist, PlaylistPlatformInfo, PlaylistTrack, Track


class PlaylistRepository:
    """Repository for playlist-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()
        self.model = Playlist

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Get a playlist by its ID.

        Args:
            playlist_id: The playlist ID

        Returns:
            The playlist if found, None otherwise
        """
        return (
            self.session.query(Playlist)
            .options(joinedload(Playlist.tracks))
            .filter(Playlist.id == playlist_id)
            .first()
        )

    def get_by_platform_id(self, platform: str, platform_id: str) -> Playlist | None:
        """Get a playlist by its platform-specific ID.

        Args:
            platform: The platform name (e.g., 'spotify', 'rekordbox')
            platform_id: The ID in the platform's system

        Returns:
            The playlist if found, None otherwise
        """
        # First check in new PlaylistPlatformInfo model
        playlist_platform_info = (
            self.session.query(PlaylistPlatformInfo)
            .filter(
                PlaylistPlatformInfo.platform == platform,
                PlaylistPlatformInfo.platform_id == platform_id,
            )
            .first()
        )

        if playlist_platform_info:
            return self.get_by_id(playlist_platform_info.playlist_id)

        # Fall back to old style where platform info is in the playlist table directly
        return (
            self.session.query(Playlist)
            .filter(
                Playlist.source_platform == platform,
                Playlist.platform_id == platform_id,
            )
            .first()
        )

    def get_all(self, include_tracks: bool = False) -> list[Playlist]:
        """Get all playlists.

        Args:
            include_tracks: Whether to load tracks with the playlists

        Returns:
            List of playlists
        """
        query = self.session.query(Playlist)

        if include_tracks:
            query = query.options(joinedload(Playlist.tracks).joinedload(PlaylistTrack.track))

        return query.order_by(Playlist.name).all()

    def get_playlists_by_platform(self, platform: str) -> list[Playlist]:
        """Get all playlists linked to a specific platform.

        Args:
            platform: Platform name (e.g., 'spotify', 'rekordbox')

        Returns:
            List of playlists linked to the platform
        """
        # First get playlists from new PlaylistPlatformInfo model
        playlist_ids_from_info = [
            info.playlist_id
            for info in self.session.query(PlaylistPlatformInfo.playlist_id)
            .filter(PlaylistPlatformInfo.platform == platform)
            .all()
        ]

        # Get playlists from old source_platform/platform_id
        old_style_playlists = (
            self.session.query(Playlist)
            .filter(Playlist.source_platform == platform)
            .filter(Playlist.platform_id != None)  # noqa: E711
            .all()
        )

        # Include playlists from old style that aren't in new style
        old_style_ids = {playlist.id for playlist in old_style_playlists}
        combined_ids = set(playlist_ids_from_info).union(old_style_ids)

        if not combined_ids:
            return []

        # Return all playlists by the combined IDs
        return (
            self.session.query(Playlist)
            .filter(Playlist.id.in_(combined_ids))
            .order_by(Playlist.name)
            .all()
        )

    def search(self, query: str, limit: int = 20, offset: int = 0) -> tuple[list[Playlist], int]:
        """Search for playlists by name or description.

        Args:
            query: The search query
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of playlists, total count)
        """
        # Prepare search terms
        search_term = f"%{query}%"

        # Build the query
        base_query = self.session.query(Playlist).filter(
            or_(
                Playlist.name.ilike(search_term),
                Playlist.description.ilike(search_term),
            )
        )

        # Get total count
        total = base_query.count()

        # Get paginated results
        playlists = base_query.order_by(Playlist.name).limit(limit).offset(offset).all()

        return playlists, total

    def create(self, playlist_data: dict) -> Playlist:
        """Create a new playlist.

        Args:
            playlist_data: Dictionary with playlist data

        Returns:
            The created playlist
        """
        playlist = Playlist(**playlist_data)
        self.session.add(playlist)
        self.session.commit()
        return playlist

    def update(self, playlist_id: int, playlist_data: dict) -> Playlist | None:
        """Update an existing playlist.

        Args:
            playlist_id: The playlist ID
            playlist_data: Dictionary with updated playlist data

        Returns:
            The updated playlist if found, None otherwise
        """
        playlist = self.get_by_id(playlist_id)
        if not playlist:
            return None

        # Update playlist attributes
        for key, value in playlist_data.items():
            if key != "tracks":  # Handle tracks separately
                setattr(playlist, key, value)

        self.session.commit()
        return playlist

    def delete(self, playlist_id: int) -> bool:
        """Delete a playlist by its ID.

        Args:
            playlist_id: The playlist ID

        Returns:
            True if deleted, False if not found
        """
        playlist = self.get_by_id(playlist_id)
        if not playlist:
            return False

        self.session.delete(playlist)
        self.session.commit()
        return True

    def add_track(
        self, playlist_id: int, track_id: int, position: int | None = None
    ) -> PlaylistTrack:
        """Add a track to a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID
            position: The position in the playlist (default: append to end)

        Returns:
            The created playlist track association
        """
        # If position not specified, place at end of playlist
        if position is None:
            # Get highest current position
            last_position = (
                self.session.query(PlaylistTrack.position)
                .filter(PlaylistTrack.playlist_id == playlist_id)
                .order_by(PlaylistTrack.position.desc())
                .first()
            )
            position = (last_position[0] + 1) if last_position else 0

        # Create the association
        playlist_track = PlaylistTrack(
            playlist_id=playlist_id,
            track_id=track_id,
            position=position,
            added_at=datetime.now(UTC),
        )

        self.session.add(playlist_track)
        self.session.commit()
        return playlist_track

    def remove_track(self, playlist_id: int, track_id: int) -> bool:
        """Remove a track from a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID

        Returns:
            True if removed, False if not found
        """
        playlist_track = (
            self.session.query(PlaylistTrack)
            .filter(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id == track_id,
            )
            .first()
        )

        if not playlist_track:
            return False

        # Get the position of the removed track
        removed_position = playlist_track.position

        # Remove the association
        self.session.delete(playlist_track)

        # Update positions of subsequent tracks
        self.session.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.position > removed_position,
        ).update(
            {PlaylistTrack.position: PlaylistTrack.position - 1},
            synchronize_session=False,
        )

        self.session.commit()
        return True

    def reorder_track(self, playlist_id: int, track_id: int, new_position: int) -> bool:
        """Change a track's position in a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID
            new_position: The new position

        Returns:
            True if reordered, False if not found
        """
        playlist_track = (
            self.session.query(PlaylistTrack)
            .filter(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id == track_id,
            )
            .first()
        )

        if not playlist_track:
            return False

        # Get the current position value
        old_position = playlist_track.position

        # The following comparison is a SQLAlchemy expression, not a Python comparison
        # We need to evaluate it explicitly to get a boolean result
        if old_position == new_position:  # type: ignore
            return True

        # For the conditional, use IS comparison for clarity
        if old_position < new_position:  # type: ignore
            # Moving down - shift tracks in between up
            self.session.query(PlaylistTrack).filter(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.position > old_position,
                PlaylistTrack.position <= new_position,
            ).update(
                {PlaylistTrack.position: PlaylistTrack.position - 1},
                synchronize_session=False,
            )
        else:
            # Moving up - shift tracks in between down
            self.session.query(PlaylistTrack).filter(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.position >= new_position,
                PlaylistTrack.position < old_position,
            ).update(
                {PlaylistTrack.position: PlaylistTrack.position + 1},
                synchronize_session=False,
            )

        # Update the track's position using setattr
        playlist_track.position = new_position  # type: ignore

        self.session.commit()
        return True

    def get_playlist_tracks(self, playlist_id: int) -> list[Track]:
        """Get all tracks in a playlist in order.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of tracks in the playlist
        """
        playlist_tracks = (
            self.session.query(PlaylistTrack)
            .filter(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
            .all()
        )

        track_ids = [pt.track_id for pt in playlist_tracks]

        # Get the actual tracks if there are any
        if not track_ids:
            return []

        # Load tracks with minimal relationships to avoid database schema issues
        # We'll let SQLAlchemy lazy-load other relationships as needed
        tracks = self.session.query(Track).filter(Track.id.in_(track_ids)).all()

        # Order tracks by their position in the playlist
        track_dict = {t.id: t for t in tracks}
        ordered_tracks = [track_dict[track_id] for track_id in track_ids if track_id in track_dict]

        return ordered_tracks

    def get_track_count(self, playlist_id: int) -> int:
        """Get the number of tracks in a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            Number of tracks in the playlist
        """
        return (
            self.session.query(PlaylistTrack)
            .filter(PlaylistTrack.playlist_id == playlist_id)
            .count()
        )

    def clear_tracks(self, playlist_id: int) -> None:
        """Remove all tracks from a playlist.

        Args:
            playlist_id: The playlist ID
        """
        self.session.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete(
            synchronize_session=False
        )
        self.session.commit()

    def add_platform_info(
        self,
        playlist_id: int,
        platform: str,
        platform_id: str,
        uri: str | None = None,
        platform_data: dict[str, Any] | None = None,
    ) -> PlaylistPlatformInfo:
        """Add platform-specific information to a playlist.

        Args:
            playlist_id: The playlist ID
            platform: Platform name (e.g., 'spotify', 'rekordbox')
            platform_id: Platform-specific ID
            uri: Optional URI/URL for the playlist on the platform
            platform_data: Optional platform-specific metadata as dictionary

        Returns:
            The created playlist platform info object
        """
        # Check if platform info already exists
        existing_info = (
            self.session.query(PlaylistPlatformInfo)
            .filter(
                PlaylistPlatformInfo.playlist_id == playlist_id,
                PlaylistPlatformInfo.platform == platform,
            )
            .first()
        )

        if existing_info:
            # Update existing info
            existing_info.platform_id = platform_id
            if uri is not None:
                existing_info.uri = uri
            if platform_data is not None:
                existing_info.platform_data = json.dumps(platform_data)
            existing_info.last_linked = datetime.now(UTC)

            self.session.commit()
            return existing_info
        else:
            # Create new platform info
            platform_info = PlaylistPlatformInfo(
                playlist_id=playlist_id,
                platform=platform,
                platform_id=platform_id,
                uri=uri,
                platform_data=json.dumps(platform_data) if platform_data else None,
                last_linked=datetime.now(UTC),
            )

            self.session.add(platform_info)
            self.session.commit()
            return platform_info

    def remove_platform_info(self, playlist_id: int, platform: str) -> bool:
        """Remove platform-specific information from a playlist.

        Args:
            playlist_id: The playlist ID
            platform: Platform name (e.g., 'spotify', 'rekordbox')

        Returns:
            True if removed, False if not found
        """
        deleted = (
            self.session.query(PlaylistPlatformInfo)
            .filter(
                PlaylistPlatformInfo.playlist_id == playlist_id,
                PlaylistPlatformInfo.platform == platform,
            )
            .delete(synchronize_session=False)
        )

        self.session.commit()
        return deleted > 0

    def get_platform_info(self, playlist_id: int, platform: str) -> PlaylistPlatformInfo | None:
        """Get platform-specific information for a playlist.

        Args:
            playlist_id: The playlist ID
            platform: Platform name (e.g., 'spotify', 'rekordbox')

        Returns:
            The playlist platform info if found, None otherwise
        """
        return (
            self.session.query(PlaylistPlatformInfo)
            .filter(
                PlaylistPlatformInfo.playlist_id == playlist_id,
                PlaylistPlatformInfo.platform == platform,
            )
            .first()
        )

    def migrate_legacy_platform_info(self) -> int:
        """Migrate legacy platform info from Playlist to PlaylistPlatformInfo.

        This is a utility method to help with the transition.

        Returns:
            Number of playlists migrated
        """
        # Get all playlists with legacy platform info
        legacy_playlists = (
            self.session.query(Playlist)
            .filter(Playlist.source_platform != None)  # noqa: E711
            .filter(Playlist.platform_id != None)  # noqa: E711
            .all()
        )

        migrated_count = 0

        for playlist in legacy_playlists:
            # Check if playlist already has new-style platform info
            existing_info = self.get_platform_info(playlist.id, playlist.source_platform)

            if not existing_info:
                # Create new platform info
                self.add_platform_info(
                    playlist_id=playlist.id,
                    platform=playlist.source_platform,
                    platform_id=playlist.platform_id,
                )
                migrated_count += 1

        return migrated_count
