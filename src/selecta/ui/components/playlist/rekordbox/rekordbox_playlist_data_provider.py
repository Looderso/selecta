# src/selecta/ui/components/playlist/rekordbox/rekordbox_playlist_data_provider.py
"""Rekordbox playlist data provider implementation."""

import os
from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMessageBox, QWidget

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.types import SyncResult
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_playlist_item import RekordboxPlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_track_item import RekordboxTrackItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.dialogs import ImportExportPlaylistDialog


class RekordboxPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for Rekordbox playlists."""

    def __init__(self, client: RekordboxClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Rekordbox playlist data provider.

        Args:
            client: Optional RekordboxClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Rekordbox client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("rekordbox", settings_repo)
            if not isinstance(client_instance, RekordboxClient):
                raise ValueError("Could not create Rekordbox client")
            self.client = client_instance
        else:
            self.client = client

        # Initialize the abstract provider
        super().__init__(self.client, cache_timeout)

        # Additional cache keys specific to Rekordbox
        self._all_playlists_cache_key = "rekordbox_all_playlists"

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from Rekordbox.

        Returns:
            List of playlist items
        """
        if not self._ensure_authenticated():
            return []

        try:
            # Get all playlists from Rekordbox
            rekordbox_playlists = self.client.get_all_playlists()
            playlist_items = []

            # Create repository to check if playlists are imported
            playlist_repo = PlaylistRepository()

            # Get all imported Rekordbox playlists
            imported_rekordbox_ids = set()
            try:
                # Get all playlists linked to Rekordbox
                imported_playlists = playlist_repo.get_playlists_by_platform("rekordbox")

                # Extract the platform_ids
                for playlist in imported_playlists:
                    # Get the platform ID (from new platform_info if available,
                    # otherwise from legacy field)
                    platform_id = playlist.get_platform_id("rekordbox")
                    if platform_id:
                        imported_rekordbox_ids.add(platform_id)
            except Exception as e:
                logger.warning(f"Error fetching imported Rekordbox playlists: {e}")

            for rb_playlist in rekordbox_playlists:
                # Check if this playlist has been imported
                playlist_id = rb_playlist.id
                is_imported = str(playlist_id) in imported_rekordbox_ids

                # Convert to PlaylistItem
                playlist_items.append(
                    RekordboxPlaylistItem(
                        name=rb_playlist.name,
                        item_id=rb_playlist.id,
                        parent_id=rb_playlist.parent_id
                        if rb_playlist.parent_id != "root"
                        else None,
                        is_folder_flag=rb_playlist.is_folder,
                        track_count=len(rb_playlist.tracks),
                        is_imported=is_imported,
                    )
                )

            return playlist_items

        except Exception as e:
            logger.exception(f"Error getting Rekordbox playlists: {e}")
            return []

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from Rekordbox.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self._ensure_authenticated():
            return []

        try:
            # Get the playlist from Rekordbox
            playlist = self.client.get_playlist_by_id(str(playlist_id))
            if not playlist:
                logger.error(f"Playlist not found: {playlist_id}")
                return []

            # Convert tracks to TrackItem objects
            track_items = []
            for rb_track in playlist.tracks:
                # Convert to TrackItem
                track_items.append(
                    RekordboxTrackItem(
                        track_id=rb_track.id,
                        title=rb_track.title,
                        artist=rb_track.artist_name,
                        album=rb_track.album_name,
                        duration_ms=rb_track.duration_ms,
                        bpm=rb_track.bpm,
                        key=rb_track.key,
                        path=rb_track.folder_path,
                        rating=rb_track.rating,
                        created_at=rb_track.created_at,
                    )
                )

            return track_items

        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Rekordbox"

    # Use the default implementation
    # from AbstractPlaylistDataProvider for show_playlist_context_menu

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a Rekordbox playlist to the local library.

        Args:
            playlist_id: ID of the playlist to import
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Error",
                "You must be authenticated with Rekordbox to import playlists.",
            )
            return False

        try:
            # Get the playlist details first to get the name for the dialog
            rekordbox_playlist = self.client.get_playlist_by_id(str(playlist_id))
            if not rekordbox_playlist:
                QMessageBox.critical(
                    parent,
                    "Playlist Not Found",
                    f"Could not find Rekordbox playlist with ID {playlist_id}.",
                )
                return False

            # Show the import dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="import", platform="rekordbox", default_name=rekordbox_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.client)

            # First check if a playlist with the same Rekordbox ID already exists
            playlist_repo = PlaylistRepository()
            existing_playlist = playlist_repo.get_by_platform_id("rekordbox", str(playlist_id))

            if existing_playlist:
                response = QMessageBox.question(
                    parent,
                    "Playlist Already Exists",
                    f"A playlist from Rekordbox with this ID already exists: "
                    f"'{existing_playlist.name}'. "
                    "Do you want to update it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if response != QMessageBox.StandardButton.Yes:
                    return False

            # Import the playlist using the sync manager
            local_playlist, imported_tracks = sync_manager.import_playlist(
                platform_playlist_id=str(playlist_id), target_name=playlist_name
            )

            # Count tracks with local files
            tracks_with_local_files = 0
            for track in imported_tracks:
                if track.local_path and os.path.exists(track.local_path):
                    tracks_with_local_files += 1

            # Show success message
            QMessageBox.information(
                parent,
                "Import Successful",
                f"Playlist '{playlist_name}' imported successfully.\n"
                f"{len(imported_tracks)} tracks imported.\n"
                f"{tracks_with_local_files} tracks have local audio files available.",
            )

            # Refresh the UI to show the imported playlist
            self.notify_refresh_needed()

            return True

        except Exception as e:
            logger.exception(f"Error importing Rekordbox playlist: {e}")
            QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False

    def export_playlist(
        self, playlist_id: str, target_platform: str, parent: QWidget | None = None
    ) -> bool:
        """Export a local playlist to Rekordbox.

        Args:
            playlist_id: Local playlist ID
            target_platform: Target platform name
            parent: Parent widget for dialogs

        Returns:
            True if successfully exported
        """
        if not self._ensure_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Error",
                "You must be connected to Rekordbox to export playlists.",
            )
            return False

        try:
            # Get the source playlist details
            playlist_repo = PlaylistRepository()
            source_playlist = playlist_repo.get_by_id(int(playlist_id))

            if not source_playlist:
                QMessageBox.critical(
                    parent,
                    "Playlist Not Found",
                    f"Could not find library playlist with ID {playlist_id}.",
                )
                return False

            # Show the export dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="export", platform="rekordbox", default_name=source_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.client)

            # Check if this playlist is already linked to Rekordbox
            platform_id = source_playlist.get_platform_id("rekordbox")

            # Show progress information
            QMessageBox.information(
                parent,
                "Exporting Playlist",
                "Exporting playlist to Rekordbox. This may take a moment...",
            )

            # Export the playlist
            _ = sync_manager.export_playlist(  # Ignoring the returned ID since we don't use it
                local_playlist_id=int(playlist_id),
                platform_playlist_id=platform_id,
                platform_playlist_name=playlist_name,
            )

            # Show success message
            QMessageBox.information(
                parent,
                "Export Successful",
                f"Successfully exported playlist '{source_playlist.name}' "
                f"to Rekordbox as '{playlist_name}'.",
            )

            # Refresh playlists
            self.refresh()

            return True
        except Exception as e:
            logger.exception(f"Error exporting playlist to Rekordbox: {e}")
            QMessageBox.critical(parent, "Export Failed", f"Failed to export playlist: {str(e)}")
            return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a local playlist with its Rekordbox counterpart.

        Args:
            playlist_id: Local playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully synced
        """
        if not self._ensure_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Error",
                "You must be connected to Rekordbox to sync playlists.",
            )
            return False

        try:
            # Get the playlist details
            playlist_repo = PlaylistRepository()
            source_playlist = playlist_repo.get_by_id(int(playlist_id))

            if not source_playlist:
                QMessageBox.critical(
                    parent,
                    "Playlist Not Found",
                    f"Could not find library playlist with ID {playlist_id}.",
                )
                return False

            # Check if this playlist is linked to Rekordbox
            platform_id = source_playlist.get_platform_id("rekordbox")

            if not platform_id:
                QMessageBox.warning(
                    parent,
                    "Not Linked to Rekordbox",
                    f"Playlist '{source_playlist.name}' is not linked to Rekordbox. "
                    "Please export it first.",
                )
                return False

            # Show progress information
            QMessageBox.information(
                parent,
                "Syncing Playlist",
                "Syncing playlist with Rekordbox. This may take a moment...",
            )

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.client)

            # Sync the playlist
            sync_result = sync_manager.sync_playlist(
                local_playlist_id=int(playlist_id),
                apply_all_changes=True,  # Apply changes directly
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
            QMessageBox.information(
                parent,
                "Sync Successful",
                f"Successfully synced playlist '{source_playlist.name}' with Rekordbox.\n"
                f"Added {tracks_added_to_library} tracks to library, "
                f"added {tracks_added_to_platform} tracks to Rekordbox.",
            )

            # Refresh playlists
            self.notify_refresh_needed()

            return True
        except Exception as e:
            logger.exception(f"Error syncing playlist with Rekordbox: {e}")
            QMessageBox.critical(parent, "Sync Failed", f"Failed to sync playlist: {str(e)}")
            return False
