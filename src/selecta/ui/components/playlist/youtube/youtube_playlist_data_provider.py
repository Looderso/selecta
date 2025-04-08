"""YouTube playlist data provider for the UI."""

from typing import Any, cast

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.platform.youtube.models import YouTubePlaylist
from selecta.core.platform.youtube.sync import import_youtube_playlist
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.components.playlist.youtube.youtube_playlist_item import YouTubePlaylistItem
from selecta.ui.components.playlist.youtube.youtube_track_item import YouTubeTrackItem
from selecta.ui.create_playlist_dialog import CreatePlaylistDialog


class YouTubePlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for YouTube playlists."""

    def __init__(self, client: YouTubeClient | None = None, cache_timeout: float = 300.0) -> None:
        """Initialize the YouTube playlist data provider.

        Args:
            client: YouTube client instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Initialize with client first so that our self.client will be set
        super().__init__(client=client, cache_timeout=cache_timeout)
        
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
        
        try:
            # Fetch playlists from YouTube
            logger.debug("Calling get_playlists()")
            self._playlists = self.youtube_client.get_playlists()
            logger.info(f"Fetched {len(self._playlists)} playlists from YouTube")

            # Convert to UI playlist items
            for playlist in self._playlists:
                logger.debug(f"Processing playlist: {playlist.id} - {playlist.title}")
                playlist_item = YouTubePlaylistItem(
                    id=playlist.id,
                    title=playlist.title,
                    description=playlist.description,
                    track_count=playlist.video_count,
                    thumbnail_url=playlist.thumbnail_url,
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

    def show_playlist_context_menu(
        self, tree_view: QTreeView, position: Any, parent: QWidget | None = None
    ) -> None:
        """Show a context menu for a YouTube playlist.

        Args:
            tree_view: The tree view containing the playlist
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        index = tree_view.indexAt(position)
        if not index.isValid():
            return

        item = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item, YouTubePlaylistItem):
            return

        menu = QMenu()
        import_action = menu.addAction("Import to Library")
        refresh_action = menu.addAction("Refresh")

        # Show the menu and handle the selected action
        action = menu.exec(tree_view.viewport().mapToGlobal(position))

        if action == import_action:
            self.import_playlist(item.id, parent)
        elif action == refresh_action:
            self.refresh_playlist(item.id)

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

            # Import the playlist
            local_playlist, tracks = import_youtube_playlist(self.youtube_client, playlist_id)

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
        # This method is not directly used for YouTube - handled by sync manager
        return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a local playlist with its platform counterpart.

        Args:
            playlist_id: Local playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully synced
        """
        # This method is not directly used for YouTube - handled by sync manager
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
                name = dialog.get_name()
                description = dialog.get_description()

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
