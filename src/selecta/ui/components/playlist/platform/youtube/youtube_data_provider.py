"""Data provider for YouTube.

This module provides the implementation of the platform data provider for YouTube,
extending the base provider with YouTube-specific functionality.
"""

from typing import Any, cast

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.types import SyncResult
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.ui.components.playlist.base_platform_provider import BasePlatformDataProvider
from selecta.ui.components.playlist.interfaces import (
    IPlatformClient,
    PlatformCapability,
)
from selecta.ui.components.playlist.youtube.youtube_playlist_item import YouTubePlaylistItem
from selecta.ui.components.playlist.youtube.youtube_track_item import YouTubeTrackItem
from selecta.ui.dialogs import CreatePlaylistDialog, ImportExportPlaylistDialog


class YouTubeDataProvider(BasePlatformDataProvider):
    """Data provider for YouTube.

    This provider implements access to the YouTube platform, allowing
    users to browse, import, export, and sync playlists.
    """

    def __init__(self, client: IPlatformClient | None = None, cache_timeout: float = 300.0):
        """Initialize the YouTube data provider.

        Args:
            client: Optional YouTube client
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # If no client is provided, create one
        if client is None:
            settings_repo = SettingsRepository()
            platform_client = PlatformFactory.create("youtube", settings_repo)
            if not platform_client:
                raise ValueError("Could not create YouTube client")
            # Cast to the interface type for the provider
            client = cast(IPlatformClient, platform_client)

        # Initialize the base provider
        super().__init__(client=client, cache_timeout=cache_timeout)

        # Store a reference to the client with proper typing for direct access when needed
        self.youtube_client = cast(YouTubeClient, self.client)

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "YouTube"

    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform provider.

        Returns:
            List of supported capabilities
        """
        return [
            PlatformCapability.IMPORT_PLAYLISTS,
            PlatformCapability.EXPORT_PLAYLISTS,
            PlatformCapability.SYNC_PLAYLISTS,
            PlatformCapability.CREATE_PLAYLISTS,
            PlatformCapability.IMPORT_TRACKS,
            PlatformCapability.SEARCH,
            PlatformCapability.COVER_ART,
        ]

    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        Returns:
            True if connected, False otherwise
        """
        return self.client is not None and self.client.is_authenticated()

    def connect_platform(self, parent: QWidget | None = None) -> bool:
        """Connect to the platform.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successfully connected
        """
        if self.is_connected():
            return True

        # Attempt to authenticate
        if self.client and self.client.authenticate():
            return True

        # Failed to authenticate
        if parent:
            QMessageBox.warning(
                parent,
                "Authentication Failed",
                "Failed to authenticate with YouTube. Please check your credentials.",
            )
        return False

    def _fetch_playlists(self) -> list[YouTubePlaylistItem]:
        """Fetch playlists from YouTube.

        Returns:
            List of YouTube playlist items
        """
        if not self.is_connected():
            return []

        # Get all playlists from YouTube
        youtube_playlists = self.youtube_client.get_playlists()
        playlist_items = []

        # Create repository to check if playlists are imported
        playlist_repo = PlaylistRepository()

        # Get all imported YouTube playlists
        imported_youtube_ids = set()
        try:
            # Get all playlists linked to YouTube
            imported_playlists = playlist_repo.get_playlists_by_platform("youtube")

            # Extract the platform_ids
            for playlist in imported_playlists:
                # Get the platform ID
                platform_id = playlist.get_platform_id("youtube")
                if platform_id:
                    imported_youtube_ids.add(platform_id)
        except Exception as e:
            logger.warning(f"Error fetching imported YouTube playlists: {e}")

        # Convert each YouTube playlist to a YouTubePlaylistItem
        for yt_playlist in youtube_playlists:
            # Check if this playlist has been imported
            playlist_id = yt_playlist.id
            is_imported = playlist_id in imported_youtube_ids

            # Add the playlist
            playlist_items.append(
                YouTubePlaylistItem(
                    id=playlist_id,
                    title=yt_playlist.title,
                    description=yt_playlist.description or "",
                    track_count=yt_playlist.video_count,
                    thumbnail_url=yt_playlist.thumbnail_url,
                    is_imported=is_imported,
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[YouTubeTrackItem]:
        """Fetch tracks for a playlist from YouTube.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of YouTube track items
        """
        if not self.is_connected():
            return []

        # Get the tracks from YouTube
        youtube_tracks = self.youtube_client.get_playlist_tracks(str(playlist_id))

        # Convert tracks to TrackItem objects
        track_items = []
        for yt_track in youtube_tracks:
            # Extract artist from channel title
            artist = yt_track.channel_title if yt_track.channel_title else "Unknown Artist"

            # Convert to YouTubeTrackItem using the new BaseTrackItem base class
            track_items.append(
                YouTubeTrackItem(
                    id=yt_track.id,  # Use the id attribute instead of video_id
                    title=yt_track.title,
                    artist=artist,
                    duration=yt_track.duration_seconds or 0,  # Make sure duration is never None
                    thumbnail_url=yt_track.thumbnail_url,
                    added_at=None,  # YouTube API doesn't provide added date for playlist items
                    album_id=None,  # No album in database yet
                    has_image=False,  # No image in database yet
                )
            )

        return track_items

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a YouTube playlist to the local library.

        Args:
            playlist_id: ID of the playlist to import
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with YouTube to import playlists.",
                )
            return False

        try:
            # Get basic playlist info for the dialog
            youtube_playlist = self.youtube_client.get_playlist(str(playlist_id))

            # Check if playlist exists
            if youtube_playlist is None:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Import Error",
                        f"Cannot find playlist with ID {playlist_id}.",
                    )
                return False

            # Show the import dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="import", platform="youtube", default_name=youtube_playlist.title
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Cast to AbstractPlatform for sync manager
            platform_client = cast(AbstractPlatform, self.client)

            # Create a sync manager for handling the import
            sync_manager = PlatformSyncManager(platform_client)

            # Check if playlist already exists
            playlist_repo = PlaylistRepository()
            existing_playlist = playlist_repo.get_by_platform_id("youtube", str(playlist_id))

            if existing_playlist:
                response = QMessageBox.question(
                    parent,
                    "Playlist Already Exists",
                    f"A playlist from YouTube with this ID already exists: "
                    f"'{existing_playlist.name}'. "
                    "Do you want to update it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if response != QMessageBox.StandardButton.Yes:
                    return False

                # Use sync manager to update the existing playlist
                try:
                    # Sync the playlist with existing one
                    sync_result = sync_manager.sync_playlist(
                        local_playlist_id=existing_playlist.id,
                        apply_all_changes=True,
                    )

                    # Extract results
                    tracks_added = sync_result.library_additions_applied if isinstance(sync_result, SyncResult) else 0

                    # Update name if changed
                    if playlist_name != existing_playlist.name:
                        playlist_repo.update(existing_playlist.id, {"name": playlist_name})

                    if parent:
                        QMessageBox.information(
                            parent,
                            "Sync Successful",
                            f"Playlist '{playlist_name}' synced successfully.\n"
                            f"{tracks_added} new tracks added from YouTube.",
                        )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error syncing YouTube playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Sync Error", f"Failed to sync playlist: {str(e)}")
                    return False
            else:
                # Import new playlist using the sync manager
                try:
                    # Import the playlist using PlatformSyncManager
                    logger.info(f"Starting import of YouTube playlist: {playlist_name}")

                    # Import the playlist, passing the custom name
                    local_playlist, local_tracks = sync_manager.import_playlist(
                        platform_playlist_id=str(playlist_id), target_name=playlist_name
                    )

                    logger.info(f"Imported {len(local_tracks)} tracks from YouTube playlist")

                    # Update name if different from what was imported
                    if playlist_name != local_playlist.name:
                        playlist_repo.update(local_playlist.id, {"name": playlist_name})

                    if parent:
                        QMessageBox.information(
                            parent,
                            "Import Successful",
                            f"Playlist '{playlist_name}' imported successfully.\n{len(local_tracks)} tracks imported.",
                        )

                    logger.info(
                        f"Successfully imported YouTube playlist '{playlist_name}' with {len(local_tracks)} tracks"
                    )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error importing YouTube playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
                    return False

        except Exception as e:
            logger.exception(f"Error importing YouTube playlist: {e}")
            if parent:
                QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False

    def create_playlist(self, parent: QWidget | None = None) -> bool:
        """Create a new playlist on YouTube.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with YouTube to create playlists.",
                )
            return False

        try:
            # Show a dialog to get playlist details with YouTube-specific fields
            dialog = CreatePlaylistDialog(parent, platform_name="YouTube")
            if dialog.exec() != CreatePlaylistDialog.DialogCode.Accepted:
                return False

            # Get the entered playlist details
            playlist_name = dialog.get_playlist_name()
            playlist_description = dialog.get_playlist_description()
            is_public = dialog.is_public()

            # Create the playlist on YouTube
            new_playlist = self.youtube_client.create_playlist(
                name=playlist_name,
                description=playlist_description,
                privacy_status="public" if is_public else "private",
            )

            if not new_playlist:
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Creation Failed",
                        "Failed to create playlist on YouTube.",
                    )
                return False

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Creation Successful",
                    f"Successfully created playlist '{playlist_name}' on YouTube.",
                )

            # Refresh the UI to show the new playlist
            self.refresh()
            return True
        except Exception as e:
            logger.exception(f"Error creating YouTube playlist: {e}")
            if parent:
                QMessageBox.critical(parent, "Creation Failed", f"Failed to create playlist: {str(e)}")
            return False

    def export_playlist(self, playlist_id: str, target_platform: str, parent: QWidget | None = None) -> bool:
        """Export a local playlist to YouTube.

        Args:
            playlist_id: Local playlist ID
            target_platform: Target platform name
            parent: Parent widget for dialogs

        Returns:
            True if successfully exported
        """
        if target_platform.lower() != "youtube":
            logger.warning(f"Attempted to export to non-YouTube platform: {target_platform}")
            return False

        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with YouTube to export playlists.",
                )
            return False

        try:
            # Get the source playlist details
            playlist_repo = PlaylistRepository()
            source_playlist = playlist_repo.get_by_id(int(playlist_id))

            if not source_playlist:
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Playlist Not Found",
                        f"Could not find library playlist with ID {playlist_id}.",
                    )
                return False

            # Show the export dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="export", platform="youtube", default_name=source_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Cast to AbstractPlatform for sync manager
            platform_client = cast(AbstractPlatform, self.client)

            # Create a sync manager
            sync_manager = PlatformSyncManager(platform_client)

            # Check if this playlist is already linked to YouTube
            platform_id = source_playlist.get_platform_id("youtube")

            # Export the playlist
            sync_manager.export_playlist(
                local_playlist_id=int(playlist_id),
                platform_playlist_id=platform_id,
                platform_playlist_name=playlist_name,
            )

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Export Successful",
                    f"Successfully exported playlist '{source_playlist.name}' to YouTube as '{playlist_name}'.",
                )

            # Refresh playlists
            self.refresh()

            return True
        except Exception as e:
            logger.exception(f"Error exporting playlist to YouTube: {e}")
            if parent:
                QMessageBox.critical(parent, "Export Failed", f"Failed to export playlist: {str(e)}")
            return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a local playlist with its YouTube counterpart.

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
                    "Authentication Error",
                    "You must be authenticated with YouTube to sync playlists.",
                )
            return False

        try:
            # Get the playlist details
            playlist_repo = PlaylistRepository()
            source_playlist = playlist_repo.get_by_id(int(playlist_id))

            if not source_playlist:
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Playlist Not Found",
                        f"Could not find library playlist with ID {playlist_id}.",
                    )
                return False

            # Check if this playlist is linked to YouTube
            platform_id = source_playlist.get_platform_id("youtube")

            if not platform_id:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Not Linked to YouTube",
                        f"Playlist '{source_playlist.name}' is not linked to YouTube. Please export it first.",
                    )
                return False

            # Show progress information
            if parent:
                QMessageBox.information(
                    parent,
                    "Syncing Playlist",
                    "Syncing playlist with YouTube. This may take a moment...",
                )

            # Cast to AbstractPlatform for sync manager
            platform_client = cast(AbstractPlatform, self.client)

            # Create a sync manager
            sync_manager = PlatformSyncManager(platform_client)

            # Sync the playlist
            sync_result = sync_manager.sync_playlist(local_playlist_id=int(playlist_id), apply_all_changes=True)

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
                    f"Successfully synced playlist '{source_playlist.name}' with YouTube.\n"
                    f"Added {tracks_added_to_library} tracks to library, "
                    f"added {tracks_added_to_platform} tracks to YouTube.",
                )

            # Refresh playlists
            self.notify_refresh_needed()

            return True
        except Exception as e:
            logger.exception(f"Error syncing playlist with YouTube: {e}")
            if parent:
                QMessageBox.critical(parent, "Sync Failed", f"Failed to sync playlist: {str(e)}")
            return False

    def _get_parent_widget(self, default_widget: QWidget, parent: QWidget | None = None) -> QWidget:
        """Get the parent widget for dialog operations.

        Args:
            default_widget: Default widget to use if parent is None
            parent: Explicit parent widget if provided

        Returns:
            The appropriate parent widget
        """
        return parent if parent is not None else default_widget

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a YouTube playlist.

        Args:
            tree_view: The tree view
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        # Use the parent widget provided or fall back to tree_view
        dialog_parent = self._get_parent_widget(default_widget=tree_view, parent=parent)

        # Get the playlist item at this position
        index = tree_view.indexAt(position)
        if not index.isValid():
            # Right-click on empty space
            menu = QMenu(dialog_parent)

            # Add create playlist option
            create_action = menu.addAction("Create New Playlist")
            if create_action is not None:
                create_action.triggered.connect(lambda: self.create_playlist(dialog_parent))

            # Add separator
            menu.addSeparator()

            # Add refresh option
            refresh_action = menu.addAction("Refresh All")
            if refresh_action is not None:
                refresh_action.triggered.connect(self.refresh)

            # Show the menu
            viewport = tree_view.viewport()
            if viewport is not None:
                menu.exec(viewport.mapToGlobal(position))
            return

        # Get the playlist item
        playlist_item = index.internalPointer()
        if not isinstance(playlist_item, YouTubePlaylistItem):
            return

        # Create context menu based on playlist status
        menu = QMenu(dialog_parent)

        # Add import option if not already imported
        if not playlist_item.is_imported:
            import_action = menu.addAction("Import to Library")
            if import_action is not None:
                import_action.triggered.connect(lambda: self.import_playlist(playlist_item.item_id, dialog_parent))
        else:
            # If already imported, add sync option
            sync_action = menu.addAction("Sync with Library")
            if sync_action is not None:
                sync_action.triggered.connect(
                    lambda: self._sync_playlist_via_library(playlist_item.item_id, dialog_parent)
                )

        # Add refresh option
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        if refresh_action is not None:
            refresh_action.triggered.connect(self.refresh)

        # Show the menu
        viewport = tree_view.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(position))

    def _sync_playlist_via_library(self, youtube_playlist_id: str, parent: QWidget | None = None) -> bool:
        """Sync a YouTube playlist via the library provider.

        Args:
            youtube_playlist_id: YouTube playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully synced
        """
        try:
            # Find the local playlist ID for this YouTube playlist
            playlist_repo = PlaylistRepository()
            local_playlist = playlist_repo.get_by_platform_id("youtube", youtube_playlist_id)

            if not local_playlist:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Playlist Not Found",
                        "Cannot find this playlist in the library. Please import it first.",
                    )
                return False

            # Get the library provider from the registry
            from selecta.ui.components.playlist.platform_registry import get_platform_registry

            registry = get_platform_registry()
            library_provider = registry.get_provider("library")

            if not library_provider:
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Library Provider Not Available",
                        "Cannot access the library provider.",
                    )
                return False

            # Use the library provider to sync the playlist
            return library_provider.sync_playlist(str(local_playlist.id), parent)
        except Exception as e:
            logger.exception(f"Error syncing YouTube playlist via library: {e}")
            if parent:
                QMessageBox.critical(parent, "Sync Failed", f"Failed to sync playlist: {str(e)}")
            return False
