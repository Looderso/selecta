"""Platform synchronization operations for playlist management.

This module provides the PlatformSyncManager class for playlist-level operations
between platforms and the local library database.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from selecta.core.data.models.db import (
    Playlist,
    PlaylistPlatformInfo,
    PlaylistSyncState,
    Track,
    TrackPlatformInfo,
)
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.data.types import ChangeType, SyncChanges, SyncPreview, SyncResult, TrackChange
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.link_manager import PlatformLinkManager

# Make sure we export PlatformSyncManager for importing
__all__ = ["PlatformSyncManager"]


class PlatformSyncManager:
    """Manager for synchronizing playlists between platforms and the library.

    This class focuses exclusively on playlist-level operations, using the
    PlatformLinkManager for track-level operations. It provides a clean
    separation between track linking and playlist synchronization.
    """

    # Constants for Collection playlist
    COLLECTION_NAME = "Collection"

    def __init__(
        self,
        platform_client: AbstractPlatform,
        track_repo: TrackRepository | None = None,
        playlist_repo: PlaylistRepository | None = None,
        link_manager: PlatformLinkManager | None = None,
    ):
        """Initialize the sync manager.

        Args:
            platform_client: The platform client to use for sync operations
            track_repo: Optional track repository (will create one if not provided)
            playlist_repo: Optional playlist repository (will create one if not provided)
            link_manager: Optional PlatformLinkManager (will create one if not provided)
        """
        # Create or use provided link manager for track-level operations
        self.link_manager = link_manager or PlatformLinkManager(platform_client, track_repo)
        self.platform_client = platform_client
        self.track_repo = track_repo or TrackRepository()
        self.playlist_repo = playlist_repo or PlaylistRepository()
        self.platform_name = self.link_manager._get_platform_name()

    def _find_collection_playlist_id(self) -> int | None:
        """Find the ID of the Collection playlist.

        Returns:
            The ID of the Collection playlist, or None if not found
        """
        playlists = self.playlist_repo.get_all()
        for playlist in playlists:
            if playlist.name == self.COLLECTION_NAME:
                return playlist.id
        return None

    def _track_in_playlist(self, track_id: int, playlist_id: int) -> bool:
        """Check if a track is already in a playlist.

        Args:
            track_id: The track ID to check
            playlist_id: The playlist ID to check

        Returns:
            True if the track is in the playlist, False otherwise
        """
        try:
            tracks = self.playlist_repo.get_playlist_tracks(playlist_id)
            return any(track.id == track_id for track in tracks)
        except Exception as e:
            logger.exception(f"Error checking if track is in playlist: {e}")
            return False

    def get_sync_changes(self, local_playlist_id: int) -> SyncChanges:
        """Analyze changes between library and platform playlist since last sync.

        This method compares the current state of both playlists against the
        last sync snapshot to detect additions and removals on both sides.

        Args:
            local_playlist_id: Library playlist ID

        Returns:
            SyncChanges object with all detected changes

        Raises:
            ValueError: If the playlist doesn't exist or isn't linked to this platform
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the library playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Library playlist with ID {local_playlist_id} not found")

        # Get platform info for this playlist
        platform_info = self.playlist_repo.get_platform_info(local_playlist_id, self.platform_name)
        if not platform_info:
            # Check for legacy format
            if local_playlist.source_platform == self.platform_name and local_playlist.platform_id:
                platform_id = local_playlist.platform_id
                is_personal = True  # Default for legacy records
            else:
                raise ValueError(f"Playlist {local_playlist.name} is not linked to {self.platform_name}")
        else:
            platform_id = platform_info.platform_id
            is_personal = platform_info.is_personal_playlist

        # Initialize changes object
        changes = SyncChanges(
            library_playlist_id=local_playlist_id,
            platform=self.platform_name,
            platform_playlist_id=platform_id,
            is_personal_playlist=is_personal,
        )

        # Get current tracks from both library and platform
        library_tracks = self.playlist_repo.get_playlist_tracks(local_playlist_id)

        try:
            platform_tracks, _ = self.platform_client.import_playlist_to_local(platform_id)
        except Exception as e:
            logger.exception(f"Failed to fetch platform tracks: {e}")
            changes.errors.append(f"Failed to fetch platform tracks: {str(e)}")
            return changes

        # Get sync state if it exists
        sync_state = self._get_sync_state(platform_info)

        if not sync_state:
            # No previous sync - consider all tracks as new additions in both directions
            logger.info(f"No sync state found for playlist {local_playlist.name} - " "creating initial snapshot")

            # Create initial sync state
            self._create_initial_sync_state(platform_info, library_tracks, platform_tracks)

            # Add warning about first sync
            changes.warnings.append(
                "This is the first sync for this playlist. " "All tracks will be considered as additions."
            )

            # Mark all platform tracks as additions (to be imported to library)
            for platform_track in platform_tracks:
                # Extract platform ID
                platform_track_id = self._extract_platform_track_id(platform_track)
                if not platform_track_id:
                    logger.warning(f"Failed to extract platform ID from track: {platform_track}")
                    continue

                # Check if this track already exists in library with platform link
                existing_track = self._find_library_track_by_platform_id(platform_track_id)
                if existing_track and existing_track.id in [t.id for t in library_tracks]:
                    # Track exists in both platforms and is already in the playlist
                    continue

                # Extract title and artist for display
                title, artist = self._extract_track_metadata(platform_track)

                changes.platform_additions.append(
                    TrackChange(
                        change_id=str(uuid.uuid4()),
                        change_type=ChangeType.PLATFORM_ADDITION,
                        library_track_id=existing_track.id if existing_track else None,
                        platform_track_id=platform_track_id,
                        track_title=title,
                        track_artist=artist,
                        selected=True,
                    )
                )

            # For personal playlists, mark library tracks as additions to platform
            # Skip this for shared/public playlists
            if is_personal:
                for library_track in library_tracks:
                    # Check if track has platform metadata
                    platform_id = self._get_track_platform_id(library_track)
                    if not platform_id:
                        # Track doesn't have platform metadata, can't be exported
                        continue

                    # Check if track is already in platform playlist
                    if platform_id in [self._extract_platform_track_id(t) for t in platform_tracks]:
                        # Track exists in both library and platform
                        continue

                    changes.library_additions.append(
                        TrackChange(
                            change_id=str(uuid.uuid4()),
                            change_type=ChangeType.LIBRARY_ADDITION,
                            library_track_id=library_track.id,
                            platform_track_id=platform_id,
                            track_title=library_track.title,
                            track_artist=library_track.artist,
                            selected=True,
                        )
                    )

            return changes

        # We have a previous sync state - compare current state with snapshot
        snapshot = sync_state.get_snapshot()

        # 1. Process platform tracks - find additions and removals
        current_platform_track_ids = set()
        for platform_track in platform_tracks:
            platform_track_id = self._extract_platform_track_id(platform_track)
            if not platform_track_id:
                continue

            current_platform_track_ids.add(platform_track_id)

            # Check if this platform track is in the snapshot
            if platform_track_id not in snapshot.get("platform_tracks", {}):
                # New track added on the platform
                title, artist = self._extract_track_metadata(platform_track)

                # Check if track already exists in library
                existing_track = self._find_library_track_by_platform_id(platform_track_id)

                changes.platform_additions.append(
                    TrackChange(
                        change_id=str(uuid.uuid4()),
                        change_type=ChangeType.PLATFORM_ADDITION,
                        library_track_id=existing_track.id if existing_track else None,
                        platform_track_id=platform_track_id,
                        track_title=title,
                        track_artist=artist,
                        selected=True,
                    )
                )

        # Find removals from platform
        snapshot_platform_tracks = snapshot.get("platform_tracks", {})
        for platform_track_id in snapshot_platform_tracks:
            if platform_track_id not in current_platform_track_ids:
                # Track was in snapshot but is no longer on platform
                library_track_id = snapshot_platform_tracks[platform_track_id].get("library_id")

                # Get track details
                track_title = "Unknown"
                track_artist = "Unknown"

                if library_track_id:
                    library_track = self.track_repo.get_by_id(library_track_id)
                    if library_track:
                        track_title = library_track.title
                        track_artist = library_track.artist

                changes.platform_removals.append(
                    TrackChange(
                        change_id=str(uuid.uuid4()),
                        change_type=ChangeType.PLATFORM_REMOVAL,
                        library_track_id=library_track_id,
                        platform_track_id=platform_track_id,
                        track_title=track_title,
                        track_artist=track_artist,
                        selected=True,
                    )
                )

        # 2. Process library tracks - find additions and removals (only for personal playlists)
        if is_personal:
            current_library_track_ids = set()
            for library_track in library_tracks:
                current_library_track_ids.add(library_track.id)

                # Get platform ID if available
                platform_track_id = self._get_track_platform_id(library_track)
                if not platform_track_id:
                    # Can't sync without platform ID
                    continue

                # Check if in snapshot
                if str(library_track.id) not in snapshot.get("library_tracks", {}):
                    # New track in library
                    changes.library_additions.append(
                        TrackChange(
                            change_id=str(uuid.uuid4()),
                            change_type=ChangeType.LIBRARY_ADDITION,
                            library_track_id=library_track.id,
                            platform_track_id=platform_track_id,
                            track_title=library_track.title,
                            track_artist=library_track.artist,
                            selected=True,
                        )
                    )

            # Find removals from library
            snapshot_library_tracks = snapshot.get("library_tracks", {})
            for library_track_id_str in snapshot_library_tracks:
                library_track_id = int(library_track_id_str)
                if library_track_id not in current_library_track_ids:
                    # Track was in snapshot but is no longer in library
                    track_data = snapshot_library_tracks[library_track_id_str]
                    platform_track_id = track_data.get("platform_id")

                    if not platform_track_id:
                        # Can't sync without platform ID
                        continue

                    # Try to get track details from track repo
                    track_title = "Unknown"
                    track_artist = "Unknown"

                    library_track = self.track_repo.get_by_id(library_track_id)
                    if library_track:
                        track_title = library_track.title
                        track_artist = library_track.artist

                    changes.library_removals.append(
                        TrackChange(
                            change_id=str(uuid.uuid4()),
                            change_type=ChangeType.LIBRARY_REMOVAL,
                            library_track_id=library_track_id,
                            platform_track_id=platform_track_id,
                            track_title=track_title,
                            track_artist=track_artist,
                            selected=True,
                        )
                    )

        return changes

    def preview_sync(self, local_playlist_id: int) -> SyncPreview:
        """Generate a preview of sync changes for UI display.

        Args:
            local_playlist_id: Library playlist ID

        Returns:
            SyncPreview object with human-readable changes

        Raises:
            ValueError: If the playlist doesn't exist or isn't linked to this platform
        """
        # Get all changes
        changes = self.get_sync_changes(local_playlist_id)

        # Get playlist details
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Library playlist with ID {local_playlist_id} not found")

        # Get platform info
        platform_info = self.playlist_repo.get_platform_info(local_playlist_id, self.platform_name)

        # Get platform playlist details
        platform_playlist_name = "Unknown"
        try:
            _, platform_playlist = self.platform_client.import_playlist_to_local(changes.platform_playlist_id)

            # Try to extract name from different object types
            if hasattr(platform_playlist, "name"):
                platform_playlist_name = platform_playlist.name
            elif hasattr(platform_playlist, "title"):
                platform_playlist_name = platform_playlist.title
            elif isinstance(platform_playlist, dict):
                platform_playlist_name = platform_playlist.get("name", platform_playlist.get("title", "Unknown"))

        except Exception as e:
            logger.warning(f"Failed to get platform playlist details: {e}")

        # Get last sync time
        last_synced = None
        if platform_info and hasattr(platform_info, "sync_state") and platform_info.sync_state:
            last_synced = platform_info.sync_state.last_synced

        # Create preview object
        preview = SyncPreview(
            library_playlist_id=local_playlist_id,
            library_playlist_name=local_playlist.name,
            platform=self.platform_name,
            platform_playlist_id=changes.platform_playlist_id,
            platform_playlist_name=platform_playlist_name,
            is_personal_playlist=changes.is_personal_playlist,
            last_synced=last_synced,
            platform_additions=changes.platform_additions,
            platform_removals=changes.platform_removals,
            library_additions=changes.library_additions,
            library_removals=changes.library_removals,
            errors=changes.errors,
            warnings=changes.warnings,
        )

        return preview

    def apply_sync_changes(self, local_playlist_id: int, selected_changes: dict[str, bool]) -> SyncResult:
        """Apply selected sync changes based on user selection.

        Args:
            local_playlist_id: Library playlist ID
            selected_changes: Dictionary mapping change IDs to selection status

        Returns:
            SyncResult with details of applied changes

        Raises:
            ValueError: If the playlist doesn't exist or isn't linked to this platform
        """
        # Get all possible changes
        changes = self.get_sync_changes(local_playlist_id)

        # Create result object
        result = SyncResult(
            library_playlist_id=local_playlist_id,
            platform=self.platform_name,
            platform_playlist_id=changes.platform_playlist_id,
        )

        # Filter changes to only those selected by user
        if not selected_changes:
            result.warnings.append("No changes selected for application")
            return result

        # Get the Collection playlist ID
        collection_playlist_id = self._find_collection_playlist_id()
        if not collection_playlist_id:
            logger.warning("Collection playlist not found, tracks will not be added to Collection")

        # 1. Apply platform additions (import platform tracks to library)
        for change in changes.platform_additions:
            if not selected_changes.get(change.change_id, False):
                continue

            try:
                # Fetch platform track
                platform_track = self._get_platform_track_by_id(change.platform_track_id)

                if not platform_track:
                    logger.warning(f"Could not fetch platform track {change.platform_track_id}")
                    result.warnings.append(f"Could not fetch track: {change.track_artist} - {change.track_title}")
                    continue

                # Import track to library with proper error handling
                try:
                    library_track = self.link_manager.import_track(platform_track)

                    if not library_track:
                        logger.warning(f"Failed to import platform track {change.platform_track_id}")
                        result.warnings.append(f"Failed to import: {change.track_artist} - {change.track_title}")
                        continue
                except ValueError as e:
                    # Handle validation errors (missing title/artist)
                    logger.warning(f"Import validation error for {change.platform_track_id}: {str(e)}")
                    result.warnings.append(f"Failed to import: {change.track_artist} - {change.track_title} - {str(e)}")
                    continue
                except Exception as e:
                    # Handle other unexpected errors
                    logger.exception(f"Unexpected error importing {change.platform_track_id}: {str(e)}")
                    result.warnings.append(f"Failed to import: {change.track_artist} - {change.track_title} - {str(e)}")
                    continue

                # Add track to playlist
                self.playlist_repo.add_track(local_playlist_id, library_track.id)

                # Also add to Collection playlist
                if collection_playlist_id and not self._track_in_playlist(library_track.id, collection_playlist_id):
                    self.playlist_repo.add_track(collection_playlist_id, library_track.id)
                    logger.debug(f"Added track {library_track.id} to Collection during sync")

                # Increment counter
                result.platform_additions_applied += 1

            except Exception as e:
                logger.exception(f"Error applying platform addition: {e}")
                result.errors.append(f"Error adding {change.track_artist} - {change.track_title}: {str(e)}")

        # 2. Apply platform removals (remove tracks from library playlist)
        for change in changes.platform_removals:
            if not selected_changes.get(change.change_id, False):
                continue

            try:
                if not change.library_track_id:
                    logger.warning("Cannot remove track without library ID")
                    continue

                # Remove track from playlist
                self.playlist_repo.remove_track(local_playlist_id, change.library_track_id)

                # Increment counter
                result.platform_removals_applied += 1

            except Exception as e:
                logger.exception(f"Error applying platform removal: {e}")
                result.errors.append(f"Error removing {change.track_artist} - {change.track_title}: {str(e)}")

        # 3. Apply library additions (export library tracks to platform)
        if changes.is_personal_playlist:  # Only for personal playlists
            platform_track_ids_to_add = []

            for change in changes.library_additions:
                if not selected_changes.get(change.change_id, False):
                    continue

                if not change.platform_track_id:
                    logger.warning("Cannot add track without platform ID")
                    continue

                # Add to list for batch operation
                platform_id = change.platform_track_id

                # For Spotify, use URI if available
                if self.platform_name == "spotify" and change.library_track_id:
                    library_track = self.track_repo.get_by_id(change.library_track_id)
                    if library_track:
                        for platform_info in library_track.platform_info:
                            if platform_info.platform == "spotify" and platform_info.uri:
                                platform_id = platform_info.uri
                                break

                platform_track_ids_to_add.append(platform_id)

            # Batch add tracks to platform playlist
            if platform_track_ids_to_add:
                try:
                    self.platform_client.add_tracks_to_playlist(
                        playlist_id=changes.platform_playlist_id,
                        track_ids=platform_track_ids_to_add,
                    )
                    result.library_additions_applied = len(platform_track_ids_to_add)
                except Exception as e:
                    logger.exception(f"Error adding tracks to platform playlist: {e}")
                    result.errors.append(f"Error adding tracks to platform: {str(e)}")

        # 4. Apply library removals (remove tracks from platform playlist)
        if changes.is_personal_playlist:  # Only for personal playlists
            platform_track_ids_to_remove = []

            for change in changes.library_removals:
                if not selected_changes.get(change.change_id, False):
                    continue

                if not change.platform_track_id:
                    logger.warning("Cannot remove track without platform ID")
                    continue

                # Add to list for batch operation
                platform_track_ids_to_remove.append(change.platform_track_id)

            # Batch remove tracks from platform playlist
            if platform_track_ids_to_remove:
                try:
                    self.platform_client.remove_tracks_from_playlist(
                        playlist_id=changes.platform_playlist_id,
                        track_ids=platform_track_ids_to_remove,
                    )
                    result.library_removals_applied = len(platform_track_ids_to_remove)
                except Exception as e:
                    logger.exception(f"Error removing tracks from platform playlist: {e}")
                    result.errors.append(f"Error removing tracks from platform: {str(e)}")

        # 5. Update sync snapshot
        if result.total_changes_applied > 0:
            try:
                self.save_sync_snapshot(local_playlist_id)
            except Exception as e:
                logger.exception(f"Error saving sync snapshot: {e}")
                result.warnings.append(f"Could not save sync state: {str(e)}")

        return result

    def save_sync_snapshot(self, local_playlist_id: int) -> None:
        """Save current state of both playlists for future change detection.

        Args:
            local_playlist_id: Library playlist ID

        Raises:
            ValueError: If the playlist doesn't exist or isn't linked to this platform
        """
        # Get library playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Library playlist with ID {local_playlist_id} not found")

        # Get platform info
        platform_info = self.playlist_repo.get_platform_info(local_playlist_id, self.platform_name)
        if not platform_info:
            if local_playlist.source_platform == self.platform_name and local_playlist.platform_id:
                # For legacy format, create new platform info
                platform_info = self.playlist_repo.add_platform_info(
                    playlist_id=local_playlist_id,
                    platform=self.platform_name,
                    platform_id=local_playlist.platform_id,
                )
            else:
                raise ValueError(f"Playlist {local_playlist.name} is not linked to {self.platform_name}")

        # Get current library and platform tracks
        library_tracks = self.playlist_repo.get_playlist_tracks(local_playlist_id)

        try:
            platform_tracks, _ = self.platform_client.import_playlist_to_local(platform_info.platform_id)
        except Exception as e:
            logger.exception(f"Failed to fetch platform tracks for snapshot: {e}")
            raise ValueError(f"Failed to fetch platform tracks: {str(e)}") from e

        # Create snapshot data structure
        snapshot = {"library_tracks": {}, "platform_tracks": {}}

        # Add library tracks to snapshot
        for track in library_tracks:
            platform_id = self._get_track_platform_id(track)
            if platform_id:
                # Find the track in the playlist
                playlist_track = None
                for pt in local_playlist.tracks:
                    if pt.track_id == track.id:
                        playlist_track = pt
                        break

                added_at = playlist_track.added_at if playlist_track else datetime.now(UTC)

                snapshot["library_tracks"][str(track.id)] = {
                    "platform_id": platform_id,
                    "added_at": added_at.isoformat() if added_at else None,
                }

        # Add platform tracks to snapshot
        for platform_track in platform_tracks:
            platform_id = self._extract_platform_track_id(platform_track)
            if platform_id:
                # Try to find matching library track
                library_id = None
                for track in library_tracks:
                    if self._get_track_platform_id(track) == platform_id:
                        library_id = track.id
                        break

                # Extract added_at if available
                added_at = None
                if hasattr(platform_track, "added_at"):
                    added_at = platform_track.added_at
                elif isinstance(platform_track, dict) and "added_at" in platform_track:
                    added_at = platform_track["added_at"]

                snapshot["platform_tracks"][platform_id] = {
                    "library_id": library_id,
                    "added_at": added_at.isoformat() if isinstance(added_at, datetime) else added_at,
                }

        # Get or create sync state
        sync_state = self._get_sync_state(platform_info)
        if not sync_state:
            # Create new sync state
            sync_state = PlaylistSyncState(
                platform_info_id=platform_info.id,
                last_synced=datetime.now(UTC),
                track_snapshot=json.dumps(snapshot),
            )
            self.playlist_repo.session.add(sync_state)
        else:
            # Update existing sync state
            sync_state.set_snapshot(snapshot)
            sync_state.last_synced = datetime.now(UTC)

        # Update last_linked timestamp
        platform_info.last_linked = datetime.now(UTC)

        # Commit changes
        self.playlist_repo.session.commit()

    def _get_sync_state(self, platform_info: PlaylistPlatformInfo) -> PlaylistSyncState | None:
        """Get sync state for a platform info record.

        Args:
            platform_info: The PlaylistPlatformInfo object

        Returns:
            The PlaylistSyncState object or None if not found
        """
        if not platform_info:
            return None

        # Check if sync_state relationship is available
        if hasattr(platform_info, "sync_state") and platform_info.sync_state:
            return platform_info.sync_state

        # If not, query directly
        return self.playlist_repo.session.query(PlaylistSyncState).filter_by(platform_info_id=platform_info.id).first()

    def _create_initial_sync_state(
        self,
        platform_info: PlaylistPlatformInfo,
        library_tracks: list[Track],
        platform_tracks: list[Any],
    ) -> PlaylistSyncState:
        """Create initial sync state for a playlist.

        Args:
            platform_info: The PlaylistPlatformInfo object
            library_tracks: Current library tracks
            platform_tracks: Current platform tracks

        Returns:
            The created PlaylistSyncState object
        """
        # Create snapshot data structure
        snapshot = {"library_tracks": {}, "platform_tracks": {}}

        # Add library tracks to snapshot
        for track in library_tracks:
            platform_id = self._get_track_platform_id(track)
            if platform_id:
                snapshot["library_tracks"][str(track.id)] = {
                    "platform_id": platform_id,
                    "added_at": datetime.now(UTC).isoformat(),
                }

        # Add platform tracks to snapshot
        for platform_track in platform_tracks:
            platform_id = self._extract_platform_track_id(platform_track)
            if platform_id:
                # Try to find matching library track
                library_id = None
                for track in library_tracks:
                    if self._get_track_platform_id(track) == platform_id:
                        library_id = track.id
                        break

                snapshot["platform_tracks"][platform_id] = {
                    "library_id": library_id,
                    "added_at": datetime.now(UTC).isoformat(),
                }

        # Create new sync state
        sync_state = PlaylistSyncState(
            platform_info_id=platform_info.id,
            last_synced=datetime.now(UTC),
            track_snapshot=json.dumps(snapshot),
        )
        self.playlist_repo.session.add(sync_state)
        self.playlist_repo.session.commit()

        return sync_state

    def _extract_platform_track_id(self, platform_track: Any) -> str | None:
        """Extract platform ID from a platform track object.

        Args:
            platform_track: The platform track object

        Returns:
            Platform-specific ID or None if not found
        """
        # Handle different object types
        if hasattr(platform_track, "id"):
            return platform_track.id
        elif hasattr(platform_track, "platform_id"):
            return platform_track.platform_id
        elif isinstance(platform_track, dict):
            return platform_track.get("id", platform_track.get("platform_id"))

        return None

    def _extract_track_metadata(self, platform_track: Any) -> tuple[str, str]:
        """Extract title and artist from a platform track object.

        Args:
            platform_track: The platform track object

        Returns:
            Tuple of (title, artist)
        """
        title = "Unknown"
        artist = "Unknown"

        # Handle different object types
        if hasattr(platform_track, "title"):
            title = platform_track.title
        elif hasattr(platform_track, "name"):
            title = platform_track.name
        elif isinstance(platform_track, dict):
            title = platform_track.get("title", platform_track.get("name", "Unknown"))

        if hasattr(platform_track, "artist"):
            artist = platform_track.artist
        elif hasattr(platform_track, "artists") and isinstance(platform_track.artists, list):
            if len(platform_track.artists) > 0:
                if hasattr(platform_track.artists[0], "name"):
                    artist = platform_track.artists[0].name
                elif isinstance(platform_track.artists[0], dict):
                    artist = platform_track.artists[0].get("name", "Unknown")
        elif isinstance(platform_track, dict):
            if "artist" in platform_track:
                artist = platform_track["artist"]
            elif (
                "artists" in platform_track
                and isinstance(platform_track["artists"], list)
                and len(platform_track["artists"]) > 0
            ):
                artist = platform_track["artists"][0].get("name", "Unknown")

        return title, artist

    def _get_track_platform_id(self, track: Track) -> str | None:
        """Get platform ID for a track.

        Args:
            track: The library track

        Returns:
            Platform-specific ID or None if not found
        """
        for platform_info in track.platform_info:
            if platform_info.platform == self.platform_name:
                return platform_info.platform_id

        return None

    def _find_library_track_by_platform_id(self, platform_id: str) -> Track | None:
        """Find a library track by its platform ID.

        Args:
            platform_id: The platform-specific ID

        Returns:
            Track object or None if not found
        """
        # This would normally use the track repository's specific method
        # For simplicity, we'll use a simple query
        return (
            self.track_repo.session.query(Track)
            .join(Track.platform_info)
            .filter(
                TrackPlatformInfo.platform == self.platform_name,
                TrackPlatformInfo.platform_id == platform_id,
            )
            .first()
        )

    def _get_platform_track_by_id(self, platform_id: str) -> Any | None:
        """Fetch a track from the platform by ID.

        Args:
            platform_id: The platform-specific ID

        Returns:
            Platform track object or None if not found
        """
        # Implementation depends on platform client capabilities
        # This is a placeholder - actual implementation would use platform-specific methods
        try:
            # Different platforms have different methods for fetching tracks
            if hasattr(self.platform_client, "get_track"):
                return self.platform_client.get_track(platform_id)
            elif hasattr(self.platform_client, "get_track_by_id"):
                return self.platform_client.get_track_by_id(platform_id)

            # Fallback: try to find track in platform playlist
            # This is inefficient but might work
            platform_info = self.playlist_repo.get_platform_info_by_platform(self.platform_name, platform_id)
            if platform_info:
                platform_tracks, _ = self.platform_client.import_playlist_to_local(platform_info.platform_id)
                for track in platform_tracks:
                    if self._extract_platform_track_id(track) == platform_id:
                        return track

        except Exception as e:
            logger.exception(f"Error fetching platform track {platform_id}: {e}")

        return None

    def import_playlist(
        self,
        platform_playlist_id: str,
        target_name: str | None = None,
        target_playlist_id: int | None = None,
    ) -> tuple[Playlist, list[Track]]:
        """Import a playlist from platform to the library.

        This can either create a new library playlist or import tracks
        to an existing playlist in the library.

        Args:
            platform_playlist_id: The platform-specific playlist ID
            target_name: Optional name override for the new playlist
            target_playlist_id: Optional existing library playlist ID to import into

        Returns:
            Tuple of (library playlist object, list of imported track objects)
        """
        # Check if importing to existing playlist
        if target_playlist_id is not None:
            return self._import_to_existing_playlist(platform_playlist_id, target_playlist_id)

        # Get the playlist tracks and metadata from the platform
        try:
            platform_tracks, platform_playlist = self.platform_client.import_playlist_to_local(platform_playlist_id)
        except Exception as e:
            logger.exception(f"Error importing playlist from {self.platform_name}: {e}")
            raise ValueError(f"Failed to import playlist: {str(e)}") from e

        # Extract playlist metadata - safely handling different object types
        playlist_name = "Unknown"

        # Try methods for different object types
        if hasattr(platform_playlist, "name") and platform_playlist.name:
            # For objects with a name attribute (like SpotifyPlaylist)
            playlist_name = platform_playlist.name
        elif hasattr(platform_playlist, "title") and platform_playlist.title:
            # For objects with a title attribute
            playlist_name = platform_playlist.title
        elif isinstance(platform_playlist, dict):
            # For dictionary objects
            playlist_name = platform_playlist.get("name", platform_playlist.get("title", "Unknown"))

        # Override name if provided
        if target_name:
            playlist_name = target_name

        # Extract description - safely handling different object types
        playlist_description = ""

        # Try methods for different object types
        if hasattr(platform_playlist, "description") and platform_playlist.description:
            # For objects with a description attribute
            playlist_description = platform_playlist.description
        elif isinstance(platform_playlist, dict):
            # For dictionary objects
            playlist_description = platform_playlist.get("description", "")

        # Check if we already have this playlist imported
        existing_playlist = self.playlist_repo.get_by_platform_id(self.platform_name, platform_playlist_id)

        if existing_playlist:
            # Update the existing playlist
            self.playlist_repo.update(
                existing_playlist.id,
                {
                    "name": playlist_name,
                    "description": playlist_description,
                    "last_linked": datetime.now(UTC),
                },
            )

            # Store platform info in the PlaylistPlatformInfo table
            self.playlist_repo.add_platform_info(
                playlist_id=existing_playlist.id,
                platform=self.platform_name,
                platform_id=platform_playlist_id,
            )

            local_playlist = existing_playlist

            # Clear existing tracks
            self.playlist_repo.clear_tracks(existing_playlist.id)
        else:
            # Create a new playlist
            local_playlist = Playlist(
                name=playlist_name,
                description=playlist_description,
                is_local=False,
                is_folder=False,
                last_linked=datetime.now(UTC),
                # Still set legacy fields for backward compatibility
                source_platform=self.platform_name,
                platform_id=platform_playlist_id,
            )
            self.playlist_repo.session.add(local_playlist)
            self.playlist_repo.session.commit()

            # Add platform info to the new table
            self.playlist_repo.add_platform_info(
                playlist_id=local_playlist.id,
                platform=self.platform_name,
                platform_id=platform_playlist_id,
            )

        # Import all tracks and add them to the playlist
        local_tracks = []
        logger.info(f"Starting import of {len(platform_tracks)} tracks from {self.platform_name} playlist")

        # Debug track info
        if platform_tracks and len(platform_tracks) > 0:
            sample_track = platform_tracks[0]
            track_type = type(sample_track).__name__
            logger.info(f"Platform track type: {track_type}")

        # Get the Collection playlist ID to ensure all tracks are added to Collection
        collection_playlist_id = self._find_collection_playlist_id()
        if not collection_playlist_id:
            logger.warning("Collection playlist not found, tracks will not be added to Collection")

        for i, platform_track in enumerate(platform_tracks):
            try:
                track_type = type(platform_track).__name__
                logger.info(f"Processing track {i + 1}/{len(platform_tracks)} of type {track_type}")

                # Import the track using link manager with error handling
                try:
                    local_track = self.link_manager.import_track(platform_track)

                    if not local_track:
                        logger.error(f"Failed to import track {i + 1}: link_manager.import_track returned None")
                        continue
                except ValueError as e:
                    # Log the error but don't crash the entire import process
                    logger.error(f"Failed to import track {i + 1}: {str(e)}")
                    continue
                except Exception as e:
                    # Log unexpected errors
                    logger.exception(f"Unexpected error importing track {i + 1}: {str(e)}")
                    continue

                local_tracks.append(local_track)

                # Add to playlist with correct position
                self.playlist_repo.add_track(local_playlist.id, local_track.id, position=i)

                # Also add to Collection playlist
                if collection_playlist_id and not self._track_in_playlist(local_track.id, collection_playlist_id):
                    self.playlist_repo.add_track(collection_playlist_id, local_track.id)
                    logger.debug(f"Added track {local_track.id} to Collection")

                logger.info(
                    f"Successfully imported and added track {i + 1}/{len(platform_tracks)}: "
                    f"{local_track.title} by {local_track.artist}"
                )
            except Exception:
                logger.exception(f"Error importing track {i + 1}:")
                # Continue with next track

        logger.info(
            f"Completed import of {len(local_tracks)}/{len(platform_tracks)} "
            f"tracks from {self.platform_name} playlist"
        )

        return local_playlist, local_tracks

    def _import_to_existing_playlist(
        self, platform_playlist_id: str, target_playlist_id: int
    ) -> tuple[Playlist, list[Track]]:
        """Import a platform playlist to an existing library playlist.

        Args:
            platform_playlist_id: The platform-specific playlist ID
            target_playlist_id: Existing library playlist ID to import into

        Returns:
            Tuple of (library playlist object, list of imported track objects)
        """
        # Get target library playlist
        target_playlist = self.playlist_repo.get_by_id(target_playlist_id)
        if not target_playlist:
            raise ValueError(f"Target playlist with ID {target_playlist_id} not found")

        # Get existing tracks in target playlist
        existing_tracks = self.playlist_repo.get_playlist_tracks(target_playlist_id)
        existing_track_ids = {track.id for track in existing_tracks}

        # Get positions for new tracks
        max_position = 0
        if existing_tracks and hasattr(target_playlist, "tracks") and target_playlist.tracks:
            max_position = max(pt.position for pt in target_playlist.tracks) + 1

        # Get platform tracks
        platform_tracks, _ = self.platform_client.import_playlist_to_local(platform_playlist_id)

        # Get the Collection playlist ID to ensure all tracks are added to Collection
        collection_playlist_id = self._find_collection_playlist_id()
        if not collection_playlist_id:
            logger.warning("Collection playlist not found, tracks will not be added to Collection")

        # Import platform tracks and add to target playlist
        new_tracks = []
        for i, platform_track in enumerate(platform_tracks):
            try:
                track_type = type(platform_track).__name__
                logger.info(
                    f"Processing track {i + 1}/{len(platform_tracks)} " f"for existing playlist - type {track_type}"
                )

                # Import track
                local_track = self.link_manager.import_track(platform_track)

                if not local_track:
                    logger.error(f"Failed to import track {i + 1}: link_manager.import_track returned None")
                    continue

                # Skip if already in playlist
                if local_track.id in existing_track_ids:
                    logger.debug(f"Track already in playlist: {local_track.title}")
                    continue

                # Add to playlist
                position = max_position + i
                self.playlist_repo.add_track(target_playlist_id, local_track.id, position=position)

                # Also add to Collection playlist
                if collection_playlist_id and not self._track_in_playlist(local_track.id, collection_playlist_id):
                    self.playlist_repo.add_track(collection_playlist_id, local_track.id)
                    logger.debug(f"Added track {local_track.id} to Collection")

                new_tracks.append(local_track)
                logger.info(f"Added track to existing playlist: {local_track.title} by {local_track.artist}")
            except Exception:
                logger.exception(f"Error importing track {i + 1} to existing playlist:")

        # Update last linked timestamp
        self.playlist_repo.update(target_playlist_id, {"last_linked": datetime.now(UTC)})

        return target_playlist, new_tracks

    def export_playlist(
        self,
        local_playlist_id: int,
        platform_playlist_id: str | None = None,
        platform_playlist_name: str | None = None,
        parent_folder_id: str | None = None,
        force: bool = False,
    ) -> str:
        """Export a library playlist to the platform.

        Args:
            local_playlist_id: The library playlist ID
            platform_playlist_id: Optional existing platform playlist ID to update
            platform_playlist_name: Optional name override for the platform playlist
            parent_folder_id: Optional parent folder ID (for platforms that support folders)
            force: Whether to force the export even if there are conflicts

        Returns:
            The platform playlist ID
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the library playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Library playlist with ID {local_playlist_id} not found")

        # Get all tracks in the playlist
        local_tracks = self.playlist_repo.get_playlist_tracks(local_playlist_id)
        if not local_tracks:
            logger.warning(f"Playlist {local_playlist.name} has no tracks")

        # Use provided name or default to local playlist name
        playlist_name = platform_playlist_name or local_playlist.name

        # Find tracks that have platform metadata for this platform
        platform_track_ids = []
        for track in local_tracks:
            for platform_info in track.platform_info:
                if platform_info.platform == self.platform_name and platform_info.platform_id:
                    if self.platform_name == "spotify" and platform_info.uri:
                        # Spotify uses URIs for playlist operations
                        platform_track_ids.append(platform_info.uri)
                    else:
                        platform_track_ids.append(platform_info.platform_id)
                    break

        if not platform_track_ids:
            logger.warning(f"No tracks with {self.platform_name} metadata found in playlist")

        # Export to platform
        try:
            new_platform_id = self.platform_client.export_tracks_to_playlist(
                playlist_name=playlist_name,
                track_ids=platform_track_ids,
                existing_playlist_id=platform_playlist_id,
            )

            # If this was a new export (not updating an existing playlist),
            # store platform info in the PlaylistPlatformInfo table
            if not platform_playlist_id:
                # Update last_linked time
                self.playlist_repo.update(
                    local_playlist_id,
                    {"last_linked": datetime.now(UTC)},
                )

                # Add or update platform info
                self.playlist_repo.add_platform_info(
                    playlist_id=local_playlist_id,
                    platform=self.platform_name,
                    platform_id=new_platform_id,
                )

            return new_platform_id
        except Exception as e:
            logger.exception(f"Error exporting playlist to {self.platform_name}: {e}")
            raise ValueError(f"Failed to export playlist: {str(e)}") from e

    def sync_playlist(
        self, local_playlist_id: int, apply_all_changes: bool = False, **kwargs
    ) -> SyncPreview | SyncResult:
        """Sync a library playlist with its platform source.

        This provides bidirectional synchronization, updating both
        the library playlist and the platform playlist.

        Args:
            local_playlist_id: The library playlist ID
            apply_all_changes: If True, apply all changes without preview
                             If False, return preview only
            **kwargs: Additional platform-specific arguments

        Returns:
            If apply_all_changes is True: SyncResult with applied changes
            If apply_all_changes is False: SyncPreview with potential changes

        Raises:
            ValueError: If the playlist doesn't exist or isn't linked to this platform
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the library playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Library playlist with ID {local_playlist_id} not found")

        # Verify this is a platform playlist
        platform_info = self.playlist_repo.get_platform_info(local_playlist_id, self.platform_name)
        old_style_linked = local_playlist.source_platform == self.platform_name and local_playlist.platform_id

        if not platform_info and not old_style_linked:
            raise ValueError(f"Playlist {local_playlist.name} is not linked to {self.platform_name}")

        # If preview mode, return the sync preview
        if not apply_all_changes:
            return self.preview_sync(local_playlist_id)

        # Get all changes
        changes = self.get_sync_changes(local_playlist_id)

        # Create a dictionary of all change IDs with selected=True
        selected_changes = {}

        # Add all platform additions
        for change in changes.platform_additions:
            selected_changes[change.change_id] = True

        # Add all platform removals
        for change in changes.platform_removals:
            selected_changes[change.change_id] = True

        # Add all library additions (for personal playlists only)
        for change in changes.library_additions:
            selected_changes[change.change_id] = True

        # Add all library removals (for personal playlists only)
        for change in changes.library_removals:
            selected_changes[change.change_id] = True

        # Apply all changes
        result = self.apply_sync_changes(local_playlist_id, selected_changes)

        # For backward compatibility with the old return type
        if kwargs.get("legacy_return", False):
            return result.platform_additions_applied, result.library_additions_applied

        return result
