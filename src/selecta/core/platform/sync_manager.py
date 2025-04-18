"""Link manager for platform integration operations."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from selecta.core.data.models.db import Playlist, Track
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.abstract_platform import AbstractPlatform


class PlatformLinkManager:
    """Manager for linking tracks and playlists between platforms and local database.

    This class provides standardized methods for linking operations that work with
    any platform implementation.
    """

    def __init__(
        self,
        platform_client: AbstractPlatform,
        track_repo: TrackRepository | None = None,
        playlist_repo: PlaylistRepository | None = None,
    ):
        """Initialize the link manager.

        Args:
            platform_client: The platform client to use for link operations
            track_repo: Optional track repository (will create one if not provided)
            playlist_repo: Optional playlist repository (will create one if not provided)
        """
        self.platform_client = platform_client
        self.track_repo = track_repo or TrackRepository()
        self.playlist_repo = playlist_repo or PlaylistRepository()
        self.platform_name = self._get_platform_name()

    def _get_platform_name(self) -> str:
        """Get the name of the platform from the client class.

        Returns:
            The platform name (e.g., 'spotify', 'rekordbox', 'discogs')
        """
        # Extract platform name from the client class name
        class_name = self.platform_client.__class__.__name__
        if class_name.endswith("Client"):
            return class_name[:-6].lower()
        return class_name.lower()

    def import_track(self, platform_track: Any) -> Track:
        """Import a track from platform to local database.

        Args:
            platform_track: The platform-specific track object

        Returns:
            The local Track object (either newly created or existing)

        Raises:
            ValueError: If track cannot be imported
        """
        # Extract common attributes based on the platform
        if self.platform_name == "spotify":
            # Handle Spotify track format
            track_data = {
                "title": getattr(platform_track, "name", platform_track.get("name", "")),
                "artist": ", ".join(
                    getattr(
                        platform_track,
                        "artist_names",
                        [a.get("name", "") for a in platform_track.get("artists", [])],
                    )
                ),
                "duration_ms": getattr(
                    platform_track, "duration_ms", platform_track.get("duration_ms", 0)
                ),
            }

            platform_id = getattr(platform_track, "id", platform_track.get("id", ""))
            uri = getattr(platform_track, "uri", platform_track.get("uri", ""))

            # Create additional platform metadata
            platform_metadata = {
                "popularity": getattr(
                    platform_track, "popularity", platform_track.get("popularity", 0)
                ),
                "explicit": getattr(
                    platform_track, "explicit", platform_track.get("explicit", False)
                ),
            }

            # Get album info if available
            album_info = getattr(platform_track, "album", platform_track.get("album", {}))
            if album_info:
                if isinstance(album_info, dict):
                    track_data["album"] = album_info.get("name", "")
                    # Try to extract year from release date
                    release_date = album_info.get("release_date", "")
                    if release_date and len(release_date) >= 4:
                        track_data["year"] = release_date[:4]
                else:
                    track_data["album"] = getattr(album_info, "name", "")
                    release_date = getattr(album_info, "release_date", "")
                    if release_date and len(release_date) >= 4:
                        track_data["year"] = release_date[:4]

        elif self.platform_name == "rekordbox":
            # Handle Rekordbox track format
            track_data = {
                "title": getattr(platform_track, "title", platform_track.get("title", "")),
                "artist": getattr(
                    platform_track, "artist_name", platform_track.get("artist_name", "")
                ),
                "duration_ms": getattr(
                    platform_track, "duration_ms", platform_track.get("duration_ms", 0)
                ),
                "bpm": getattr(platform_track, "bpm", platform_track.get("bpm", None)),
            }

            platform_id = str(getattr(platform_track, "id", platform_track.get("id", "")))
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "bpm": getattr(platform_track, "bpm", platform_track.get("bpm", 0)),
                "key": getattr(platform_track, "key", platform_track.get("key", "")),
                "rating": getattr(platform_track, "rating", platform_track.get("rating", 0)),
            }

        elif self.platform_name == "discogs":
            # Handle Discogs release format
            track_data = {
                "title": getattr(platform_track, "title", platform_track.get("title", "")),
                "artist": getattr(platform_track, "artist", platform_track.get("artist", "")),
                # Discogs doesn't typically include duration in ms
                "year": getattr(platform_track, "year", platform_track.get("year", None)),
            }

            platform_id = str(getattr(platform_track, "id", platform_track.get("id", "")))
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "genres": getattr(platform_track, "genres", platform_track.get("genres", [])),
                "styles": getattr(platform_track, "styles", platform_track.get("styles", [])),
                "format": getattr(platform_track, "format", platform_track.get("format", "")),
            }
        else:
            raise ValueError(f"Unsupported platform: {self.platform_name}")

        # Check if this track already exists in our database
        existing_track = None

        # First try to find by platform ID
        if platform_id:
            existing_track = self.track_repo.get_by_platform_id(self.platform_name, platform_id)

        # If not found by ID, try by title and artist
        if not existing_track and track_data.get("title") and track_data.get("artist"):
            # Find by title + artist
            query = f"{track_data['title']} {track_data['artist']}"
            matches, _ = self.track_repo.search(query, limit=1)
            if matches:
                existing_track = matches[0]

        if existing_track:
            # Update the existing track with any new information
            # Use preserve_existing=True to avoid overwriting existing fields
            self.track_repo.update(existing_track.id, track_data, preserve_existing=True)
            track = existing_track
        else:
            # Create a new track
            track = self.track_repo.create(track_data)

        # Add or update platform info
        if platform_id:
            # Convert platform metadata to JSON string
            import json

            metadata_json = json.dumps(platform_metadata)

            self.track_repo.add_platform_info(
                track_id=track.id,
                platform=self.platform_name,
                platform_id=platform_id,
                uri=uri,
                metadata=metadata_json,
            )

        return track

    def import_playlist(self, platform_playlist_id: str) -> tuple[Playlist, list[Track]]:
        """Import a playlist from platform to local database.

        Args:
            platform_playlist_id: The platform-specific playlist ID

        Returns:
            Tuple of (local playlist object, list of local track objects)

        Raises:
            ValueError: If playlist cannot be imported
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the playlist tracks and metadata from the platform
        try:
            platform_tracks, platform_playlist = self.platform_client.import_playlist_to_local(
                platform_playlist_id
            )
        except Exception as e:
            logger.exception(f"Error importing playlist from {self.platform_name}: {e}")
            raise ValueError(f"Failed to import playlist: {str(e)}")

        # Extract playlist metadata
        playlist_name = getattr(
            platform_playlist,
            "name",
            getattr(
                platform_playlist,
                "title",
                platform_playlist.get("name", platform_playlist.get("title", "Unknown")),
            ),
        )

        playlist_description = getattr(
            platform_playlist, "description", platform_playlist.get("description", "")
        )

        # Check if we already have this playlist imported
        existing_playlist = self.playlist_repo.get_by_platform_id(
            self.platform_name, platform_playlist_id
        )

        if existing_playlist:
            # Update the existing playlist
            self.playlist_repo.update(
                existing_playlist.id,
                {
                    "name": playlist_name,
                    "description": playlist_description,
                    "last_linked": datetime.now(UTC),  # Using last_linked in Playlist model
                },
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
                source_platform=self.platform_name,
                platform_id=platform_playlist_id,
                last_linked=datetime.now(UTC),
            )
            self.playlist_repo.session.add(local_playlist)
            self.playlist_repo.session.commit()

        # Import all tracks and add them to the playlist
        local_tracks = []
        for i, platform_track in enumerate(platform_tracks):
            try:
                # Import the track
                local_track = self.import_track(platform_track)
                local_tracks.append(local_track)

                # Add to playlist with correct position
                self.playlist_repo.add_track(local_playlist.id, local_track.id, position=i)
            except Exception as e:
                logger.error(f"Error importing track: {e}")
                # Continue with next track

        return local_playlist, local_tracks

    def export_playlist(
        self,
        local_playlist_id: int,
        platform_playlist_id: str | None = None,
    ) -> str:
        """Export a local playlist to the platform.

        Args:
            local_playlist_id: The local playlist ID
            platform_playlist_id: Optional existing platform playlist ID to update

        Returns:
            The platform playlist ID

        Raises:
            ValueError: If playlist cannot be exported
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the local playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Local playlist with ID {local_playlist_id} not found")

        # Get all tracks in the playlist
        local_tracks = self.playlist_repo.get_playlist_tracks(local_playlist_id)
        if not local_tracks:
            logger.warning(f"Playlist {local_playlist.name} has no tracks")

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
                playlist_name=local_playlist.name,
                track_ids=platform_track_ids,
                existing_playlist_id=platform_playlist_id,
            )

            # If this was a new export (not updating an existing playlist),
            # update the local playlist with the platform ID
            if not platform_playlist_id and not local_playlist.platform_id:
                self.playlist_repo.update(
                    local_playlist_id,
                    {
                        "source_platform": self.platform_name,
                        "platform_id": new_platform_id,
                        "last_linked": datetime.now(UTC),  # Using last_linked in Playlist model
                    },
                )

            return new_platform_id
        except Exception as e:
            logger.exception(f"Error exporting playlist to {self.platform_name}: {e}")
            raise ValueError(f"Failed to export playlist: {str(e)}")

    def link_playlist(self, local_playlist_id: int) -> tuple[int, int]:
        """Link a playlist bidirectionally between local database and platform.

        Args:
            local_playlist_id: The local playlist ID

        Returns:
            Tuple of (tracks_added, tracks_updated)

        Raises:
            ValueError: If playlist cannot be linked
        """
        if not self.platform_client.is_authenticated():
            raise ValueError(f"{self.platform_name.capitalize()} client not authenticated")

        # Get the local playlist
        local_playlist = self.playlist_repo.get_by_id(local_playlist_id)
        if not local_playlist:
            raise ValueError(f"Local playlist with ID {local_playlist_id} not found")

        # Verify this is a platform playlist
        if not local_playlist.platform_id or local_playlist.source_platform != self.platform_name:
            raise ValueError(
                f"Playlist {local_playlist.name} is not linked to {self.platform_name}"
            )

        # Get current tracks in local playlist
        local_tracks = self.playlist_repo.get_playlist_tracks(local_playlist_id)
        local_track_map = {track.id: track for track in local_tracks}

        # Get platform tracks
        platform_tracks, platform_playlist = self.platform_client.import_playlist_to_local(
            local_playlist.platform_id
        )

        # Map of platform tracks by ID for quick lookup
        platform_track_by_id = {}
        for track in platform_tracks:
            platform_id = getattr(track, "id", getattr(track, "platform_id", None))
            if platform_id:
                platform_track_by_id[platform_id] = track

        # Track local tracks that have platform metadata
        local_tracks_with_platform_info = []
        platform_ids_in_local = set()

        for track in local_tracks:
            for platform_info in track.platform_info:
                if platform_info.platform == self.platform_name and platform_info.platform_id:
                    platform_ids_in_local.add(platform_info.platform_id)
                    local_tracks_with_platform_info.append((track, platform_info))
                    break

        # Find platform tracks not in local playlist
        new_platform_tracks = []
        for platform_track in platform_tracks:
            platform_id = getattr(
                platform_track, "id", getattr(platform_track, "platform_id", None)
            )
            if platform_id and platform_id not in platform_ids_in_local:
                new_platform_tracks.append(platform_track)

        # Import new platform tracks
        tracks_added = 0
        for platform_track in new_platform_tracks:
            try:
                local_track = self.import_track(platform_track)
                # Add to playlist
                self.playlist_repo.add_track(local_playlist_id, local_track.id)
                tracks_added += 1
            except Exception as e:
                logger.error(f"Error importing track during sync: {e}")

        # Update the playlist metadata if needed
        playlist_name = getattr(
            platform_playlist,
            "name",
            getattr(
                platform_playlist,
                "title",
                platform_playlist.get("name", platform_playlist.get("title", None)),
            ),
        )

        if playlist_name and playlist_name != local_playlist.name:
            self.playlist_repo.update(
                local_playlist_id,
                {
                    "name": playlist_name,
                    "last_linked": datetime.now(UTC),
                },  # Using last_linked in Playlist model
            )
        else:
            # Just update the link timestamp
            self.playlist_repo.update(
                local_playlist_id, {"last_linked": datetime.now(UTC)}
            )  # Using last_linked in Playlist model

        # Find local tracks not in platform playlist and try to export them
        platform_track_ids = []
        for track, platform_info in local_tracks_with_platform_info:
            # Check if this track is in the platform playlist
            if platform_info.platform_id in platform_track_by_id:
                continue

            # This track has platform metadata but is not in the platform playlist
            if self.platform_name == "spotify" and platform_info.uri:
                # Spotify uses URIs
                platform_track_ids.append(platform_info.uri)
            else:
                platform_track_ids.append(platform_info.platform_id)

        # Export missing tracks to platform if any
        tracks_exported = 0
        if platform_track_ids:
            try:
                self.platform_client.add_tracks_to_playlist(
                    playlist_id=local_playlist.platform_id,
                    track_ids=platform_track_ids,
                )
                tracks_exported = len(platform_track_ids)
            except Exception as e:
                logger.error(f"Error exporting tracks during sync: {e}")

        return tracks_added, tracks_exported

    def link_tracks(self, local_track_id: int, platform_track: Any) -> bool:
        """Link a local track with platform-specific metadata.

        Args:
            local_track_id: The local track ID
            platform_track: The platform-specific track object

        Returns:
            True if successful

        Raises:
            ValueError: If track cannot be linked
        """
        # Get the local track
        local_track = self.track_repo.get_by_id(local_track_id)
        if not local_track:
            raise ValueError(f"Local track with ID {local_track_id} not found")

        # Extract platform metadata
        if self.platform_name == "spotify":
            # Handle Spotify track format
            platform_id = getattr(platform_track, "id", platform_track.get("id", ""))
            uri = getattr(platform_track, "uri", platform_track.get("uri", ""))

            # Create additional platform metadata
            platform_metadata = {
                "popularity": getattr(
                    platform_track, "popularity", platform_track.get("popularity", 0)
                ),
                "explicit": getattr(
                    platform_track, "explicit", platform_track.get("explicit", False)
                ),
            }

            # Get album info if available
            album_info = getattr(platform_track, "album", platform_track.get("album", {}))
            if album_info:
                if isinstance(album_info, dict) and "images" in album_info:
                    images = album_info["images"]
                    if images:
                        # Find largest image for best quality when resizing
                        sorted_images = sorted(
                            images, key=lambda x: x.get("width", 0), reverse=True
                        )
                        if sorted_images:
                            platform_metadata["artwork_url"] = sorted_images[0].get("url")

        elif self.platform_name == "rekordbox":
            # Handle Rekordbox track format
            platform_id = str(getattr(platform_track, "id", platform_track.get("id", "")))
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "bpm": getattr(platform_track, "bpm", platform_track.get("bpm", 0)),
                "key": getattr(platform_track, "key", platform_track.get("key", "")),
                "rating": getattr(platform_track, "rating", platform_track.get("rating", 0)),
            }

        elif self.platform_name == "discogs":
            # Handle Discogs release format
            platform_id = str(getattr(platform_track, "id", platform_track.get("id", "")))
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "genres": getattr(platform_track, "genres", platform_track.get("genres", [])),
                "styles": getattr(platform_track, "styles", platform_track.get("styles", [])),
                "format": getattr(platform_track, "format", platform_track.get("format", "")),
            }
        else:
            raise ValueError(f"Unsupported platform: {self.platform_name}")

        if not platform_id:
            raise ValueError(f"No valid platform ID found for {self.platform_name} track")

        # Convert platform metadata to JSON string
        import json

        metadata_json = json.dumps(platform_metadata)

        # Add or update platform info
        self.track_repo.add_platform_info(
            track_id=local_track_id,
            platform=self.platform_name,
            platform_id=platform_id,
            uri=uri,
            metadata=metadata_json,
        )

        return True
