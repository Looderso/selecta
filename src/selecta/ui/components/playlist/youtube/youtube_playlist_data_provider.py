"""YouTube playlist data provider for the UI."""

from typing import Any, cast

from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

from selecta.core.data.types import SyncResult
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.platform.youtube.models import YouTubePlaylist
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.components.playlist.youtube.youtube_playlist_item import YouTubePlaylistItem
from selecta.ui.components.playlist.youtube.youtube_track_item import YouTubeTrackItem
from selecta.ui.dialogs import CreatePlaylistDialog


class YouTubePlaylistDataProvider(QObject, AbstractPlaylistDataProvider):
    """Data provider for YouTube playlists."""

    # Signals for notifying view updates
    playlists_updated = pyqtSignal()  # Signal for when all playlists are updated
    playlist_updated = pyqtSignal(str)  # Signal for when a specific playlist is updated

    def __init__(self, client: YouTubeClient | None = None, cache_timeout: float = 300.0) -> None:
        """Initialize the YouTube playlist data provider.

        Args:
            client: YouTube client instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Initialize base classes properly
        # Note: Using super() isn't straightforward with multiple inheritance,
        # so we explicitly initialize each parent class
        QObject.__init__(self)
        AbstractPlaylistDataProvider.__init__(self, client=client, cache_timeout=cache_timeout)

        # Store as youtube_client as well for convenience
        if client is None:
            youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube"))
            self.youtube_client = youtube_client
            # Ensure our base client is also set
            self.client = youtube_client
        else:
            self.youtube_client = client

        self._playlists: list[YouTubePlaylist] = []
        self._playlist_tracks: dict[str, list[dict[str, Any]]] = {}

        # Log initialization state
        logger.debug(f"YouTube provider initialized with client: {self.youtube_client}")
        logger.debug(f"Authentication status: {self.is_connected()}")

    def get_platform_name(self) -> str:
        """Get the name of this platform.

        Returns:
            Platform name
        """
        return "YouTube"

    def is_connected(self) -> bool:
        """Check if connected to the platform.

        Returns:
            True if connected to the platform
        """
        return self.youtube_client is not None and self.youtube_client.is_authenticated()

    def connect_platform(self, parent: QWidget | None = None) -> bool:
        """Connect to the platform.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successfully connected
        """
        if not self.youtube_client:
            self.youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube"))

        if not self.youtube_client:
            logger.error("Failed to create YouTube client")
            return False

        if not self.youtube_client.is_authenticated():
            if parent:
                QMessageBox.information(
                    parent,
                    "YouTube Authentication",
                    "You will be redirected to YouTube to authorize Selecta.",
                )

            # Attempt authentication
            auth_success = self.youtube_client.authenticate()
            if not auth_success:
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Authentication Failed",
                        "Could not authenticate with YouTube. Please try again.",
                    )
                return False

            if parent:
                QMessageBox.information(
                    parent,
                    "Authentication Success",
                    "Successfully authenticated with YouTube!",
                )

        return True

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from the YouTube API.

        Returns:
            List of playlist items
        """
        playlist_items = []

        logger.debug("Fetching YouTube playlists...")

        # If not connected, try to connect
        if not self.is_connected():
            logger.info("Not connected to YouTube, attempting connection...")
            if not self.connect_platform():
                logger.warning("Failed to connect to YouTube")
                return []
            logger.info("Successfully connected to YouTube")

        # Import repositories here to avoid circular imports
        from selecta.core.data.repositories.playlist_repository import PlaylistRepository

        # Get all imported YouTube playlists
        imported_youtube_ids = set()
        try:
            # Create repository to check if playlists are imported
            playlist_repo = PlaylistRepository()

            # Get all playlists linked to YouTube
            imported_playlists = playlist_repo.get_playlists_by_platform("youtube")

            # Extract the platform_ids
            for playlist in imported_playlists:
                # Get the platform ID
                # (from new platform_info if available, otherwise from legacy field)
                platform_id = playlist.get_platform_id("youtube")
                if platform_id:
                    imported_youtube_ids.add(platform_id)

            logger.debug(f"Found {len(imported_youtube_ids)} imported YouTube playlists")
        except Exception as e:
            logger.warning(f"Error fetching imported YouTube playlists: {e}")

        try:
            # Fetch playlists from YouTube
            logger.debug("Calling get_playlists()")
            self._playlists = self.youtube_client.get_playlists()
            logger.info(f"Fetched {len(self._playlists)} playlists from YouTube")

            # Convert to UI playlist items
            for playlist in self._playlists:
                logger.debug(f"Processing playlist: {playlist.id} - {playlist.title}")
                # Check if this playlist has been imported
                is_imported = playlist.id in imported_youtube_ids

                playlist_item = YouTubePlaylistItem(
                    id=playlist.id,
                    title=playlist.title,
                    description=playlist.description,
                    track_count=playlist.video_count,
                    thumbnail_url=playlist.thumbnail_url,
                    is_imported=is_imported,
                )
                playlist_items.append(playlist_item)

            logger.debug(f"Returning {len(playlist_items)} playlist items")
            return playlist_items
        except Exception as e:
            logger.exception(f"Error fetching YouTube playlists: {e}")
            return []

    def _fetch_playlist_tracks(self, playlist_id: str) -> list[TrackItem]:
        """Fetch tracks for a playlist from the YouTube API.

        Args:
            playlist_id: Platform-specific playlist ID

        Returns:
            List of track items
        """
        track_items = []
        logger.debug(f"Fetching tracks for YouTube playlist: {playlist_id}")

        # If not connected, try to connect
        if not self.is_connected():
            logger.info("Not connected to YouTube, attempting connection...")
            if not self.connect_platform():
                logger.warning("Failed to connect to YouTube")
                return []
            logger.info("Successfully connected to YouTube")

        try:
            # Fetch tracks from YouTube
            logger.debug(f"Calling get_playlist_tracks() for {playlist_id}")
            videos = self.youtube_client.get_playlist_tracks(playlist_id)
            logger.info(f"Fetched {len(videos)} videos from YouTube playlist")

            # Convert to raw data for caching
            self._playlist_tracks[playlist_id] = [video.__dict__ for video in videos]
            logger.debug(f"Cached data for {len(videos)} videos")

            # Convert to UI track items
            for video_data in self._playlist_tracks[playlist_id]:
                video_id = video_data.get("id", "")
                video_title = video_data.get("title", "")
                logger.debug(f"Processing video: {video_id} - {video_title}")

                track_item = YouTubeTrackItem(
                    id=video_id,
                    title=video_title,
                    artist=video_data.get("channel_title", ""),
                    duration=video_data.get("duration_seconds", 0),
                    thumbnail_url=video_data.get("thumbnail_url"),
                )
                track_items.append(track_item)

            logger.debug(f"Returning {len(track_items)} track items")
            return track_items
        except Exception as e:
            logger.exception(f"Error fetching YouTube playlist tracks: {e}")
            return []

    # Use the default implementations from AbstractPlaylistDataProvider for:
    # - show_playlist_context_menu
    # - show_track_context_menu

    def refresh(self) -> None:
        """Refresh all playlists."""
        self._playlists = []
        self._playlist_tracks.clear()
        self.playlists_updated.emit()

    def refresh_playlist(self, playlist_id: str) -> None:
        """Refresh a specific playlist.

        Args:
            playlist_id: Platform-specific playlist ID
        """
        if playlist_id in self._playlist_tracks:
            del self._playlist_tracks[playlist_id]
        self.playlist_updated.emit(playlist_id)

    def import_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Import a platform playlist to the local library.

        Args:
            playlist_id: Platform-specific playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully imported
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    "Not connected to YouTube. Please connect first.",
                )
            return False

        try:
            # Show a progress dialog
            if parent:
                QMessageBox.information(
                    parent,
                    "Importing Playlist",
                    "Importing YouTube playlist. This may take a moment...",
                )

            # Create a sync manager to import the playlist
            sync_manager = PlatformSyncManager(self.youtube_client)

            # Import the playlist
            local_playlist, tracks = sync_manager.import_playlist(playlist_id)

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Import Successful",
                    f"Imported {len(tracks)} tracks to '{local_playlist.name}'.",
                )

            # Signal that local playlists have changed
            self.local_playlists_changed.emit()
            return True
        except Exception as e:
            logger.exception(f"Error importing YouTube playlist: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Import Failed",
                    f"Failed to import playlist: {str(e)}",
                )
            return False

    def export_playlist(
        self, playlist_id: str, target_platform: str, parent: QWidget | None = None
    ) -> bool:
        """Export a local playlist to this platform.

        Args:
            playlist_id: Local playlist ID
            target_platform: Target platform name
            parent: Parent widget for dialogs

        Returns:
            True if successfully exported
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    "Not connected to YouTube. Please connect first.",
                )
            return False

        try:
            # Show a progress dialog
            if parent:
                QMessageBox.information(
                    parent,
                    "Exporting Playlist",
                    "Exporting playlist to YouTube. This may take a moment...",
                )

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.youtube_client)

            # Export the playlist - ignoring returned ID since we don't use it
            _ = sync_manager.export_playlist(int(playlist_id))

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Export Successful",
                    "Successfully exported playlist to YouTube.",
                )

            # Signal that playlists have changed
            self.playlists_updated.emit()
            return True
        except Exception as e:
            logger.exception(f"Error exporting playlist to YouTube: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Export Failed",
                    f"Failed to export playlist: {str(e)}",
                )
            return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a local playlist with its platform counterpart.

        Args:
            playlist_id: Local playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully synced
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    "Not connected to YouTube. Please connect first.",
                )
            return False

        try:
            # Show a progress dialog
            if parent:
                QMessageBox.information(
                    parent,
                    "Syncing Playlist",
                    "Syncing playlist with YouTube. This may take a moment...",
                )

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.youtube_client)

            # Sync the playlist
            sync_result = sync_manager.sync_playlist(
                local_playlist_id=int(playlist_id), apply_all_changes=True
            )

            # Extract results from SyncResult
            if isinstance(sync_result, SyncResult):
                tracks_added_to_library = sync_result.library_additions_applied
                tracks_added_to_platform = sync_result.platform_additions_applied
            else:
                # This should not happen when apply_all_changes=True, but just in case
                tracks_added_to_library = 0
                tracks_added_to_platform = 0

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Sync Successful",
                    f"Successfully synced playlist with YouTube.\n"
                    f"Added {tracks_added_to_library} tracks to library, "
                    f"added {tracks_added_to_platform} tracks to YouTube.",
                )

            # Signal that playlists have changed
            self.local_playlists_changed.emit()
            return True
        except Exception as e:
            logger.exception(f"Error syncing playlist with YouTube: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Sync Failed",
                    f"Failed to sync playlist: {str(e)}",
                )
            return False

    def create_new_playlist(self, parent: QWidget | None = None) -> bool:
        """Create a new playlist on the platform.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successfully created
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    "Not connected to YouTube. Please connect first.",
                )
            return False

        try:
            # Show create playlist dialog
            dialog = CreatePlaylistDialog(parent)
            if dialog.exec():
                # Get the values from the dialog
                values = dialog.get_values()
                name = values["name"]
                description = ""  # Description is not collected in the standard dialog

                # Create the playlist
                self.youtube_client.create_playlist(
                    name=name,
                    description=description,
                    privacy_status="private",  # Default to private for safety
                )

                # Refresh playlists
                self.refresh()
                return True
            return False
        except Exception as e:
            logger.exception(f"Error creating YouTube playlist: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Create Failed",
                    f"Failed to create playlist: {str(e)}",
                )
            return False
