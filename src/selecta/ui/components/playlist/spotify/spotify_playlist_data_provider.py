# src/selecta/ui/components/playlist/spotify/spotify_playlist_data_provider.py
"""Spotify playlist data provider implementation."""

from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMessageBox, QWidget

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.types import SyncResult
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.spotify.spotify_playlist_item import SpotifyPlaylistItem
from selecta.ui.components.playlist.spotify.spotify_track_item import SpotifyTrackItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.dialogs import ImportExportPlaylistDialog


class SpotifyPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for Spotify playlists."""

    def __init__(self, client: SpotifyClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Spotify playlist data provider.

        Args:
            client: Optional SpotifyClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Spotify client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("spotify", settings_repo)
            if not isinstance(client_instance, SpotifyClient):
                raise ValueError("Could not create Spotify client")
            self.client = client_instance
        else:
            self.client = client

        # Import database utilities here to avoid circular imports

        # Initialize the abstract provider
        super().__init__(self.client, cache_timeout)

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from Spotify API.

        Returns:
            List of playlist items
        """
        if not self._ensure_authenticated():
            return []

        # Get all playlists from Spotify
        spotify_playlists = self.client.get_playlists()
        playlist_items = []

        # Create repository to check if playlists are imported
        playlist_repo = PlaylistRepository()

        # Get all imported Spotify playlists
        imported_spotify_ids = set()
        try:
            # Get all playlists linked to Spotify
            imported_playlists = playlist_repo.get_playlists_by_platform("spotify")

            # Extract the platform_ids
            for playlist in imported_playlists:
                # Get the platform ID (from new platform_info if available,
                # otherwise from legacy field)
                platform_id = playlist.get_platform_id("spotify")
                if platform_id:
                    imported_spotify_ids.add(platform_id)
        except Exception as e:
            logger.warning(f"Error fetching imported Spotify playlists: {e}")

        for sp_playlist in spotify_playlists:
            # Check if this playlist has been imported
            playlist_id = sp_playlist["id"]
            is_imported = playlist_id in imported_spotify_ids

            # Convert to PlaylistItem
            playlist_items.append(
                SpotifyPlaylistItem(
                    name=sp_playlist["name"],
                    item_id=playlist_id,
                    owner=sp_playlist["owner"]["display_name"],
                    description=sp_playlist.get("description", ""),
                    is_collaborative=sp_playlist.get("collaborative", False),
                    is_public=sp_playlist.get("public", True),
                    track_count=sp_playlist["tracks"]["total"],
                    images=sp_playlist.get("images", []),
                    is_imported=is_imported,
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from Spotify API.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self._ensure_authenticated():
            return []

        # Get the tracks from Spotify
        spotify_tracks = self.client.get_playlist_tracks(str(playlist_id))

        # Convert tracks to TrackItem objects
        track_items = []
        for sp_track in spotify_tracks:
            # Convert to TrackItem
            track_items.append(
                SpotifyTrackItem(
                    track_id=sp_track.id,
                    title=sp_track.name,
                    artist=", ".join(sp_track.artist_names),
                    album=sp_track.album_name,
                    duration_ms=sp_track.duration_ms,
                    added_at=sp_track.added_at,
                    uri=sp_track.uri,
                    popularity=sp_track.popularity,
                    explicit=sp_track.explicit,  # type: ignore
                    preview_url=sp_track.preview_url,
                )
            )

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Spotify"

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a Spotify playlist to the local library.

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
                "You must be authenticated with Spotify to import playlists.",
            )
            return False

        try:
            # Get basic playlist info for the dialog
            spotify_playlist = self.client.get_playlist(str(playlist_id))

            # Show the import dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="import", platform="spotify", default_name=spotify_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create a sync manager for handling the import
            sync_manager = PlatformSyncManager(self.client)

            # Check if playlist already exists
            playlist_repo = PlaylistRepository()
            existing_playlist = playlist_repo.get_by_platform_id("spotify", str(playlist_id))

            if existing_playlist:
                response = QMessageBox.question(
                    parent,
                    "Playlist Already Exists",
                    f"A playlist from Spotify with this ID already exists: "
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
                        local_playlist_id=existing_playlist.id, apply_all_changes=True
                    )

                    # Extract results
                    if isinstance(sync_result, SyncResult):
                        tracks_added = sync_result.library_additions_applied
                        # tracks_exported is not used in the message, so not extracting it
                    else:
                        tracks_added = 0

                    # Update name if changed
                    if playlist_name != existing_playlist.name:
                        playlist_repo.update(existing_playlist.id, {"name": playlist_name})

                    QMessageBox.information(
                        parent,
                        "Sync Successful",
                        f"Playlist '{playlist_name}' synced successfully.\n"
                        f"{tracks_added} new tracks added from Spotify.",
                    )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error syncing Spotify playlist: {e}")
                    QMessageBox.critical(parent, "Sync Error", f"Failed to sync playlist: {str(e)}")
                    return False
            else:
                # Import new playlist using the sync manager
                try:
                    # Create a progress dialog
                    from PyQt6.QtCore import Qt
                    from PyQt6.QtWidgets import QProgressDialog

                    progress = QProgressDialog("Importing playlist...", "Cancel", 0, 1, parent)
                    progress.setWindowTitle("Importing Playlist")
                    progress.setWindowModality(Qt.WindowModality.WindowModal)
                    progress.setValue(0)
                    progress.setLabelText("Preparing to import playlist...")
                    progress.show()

                    # Import the playlist using PlatformSyncManager
                    logger.info(f"Starting import of Spotify playlist: {playlist_name}")

                    # Get the sync manager
                    sync_manager = PlatformSyncManager(self.client)

                    # Import the playlist, passing the custom name
                    local_playlist, local_tracks = sync_manager.import_playlist(
                        platform_playlist_id=str(playlist_id), target_name=playlist_name
                    )

                    progress.setValue(1)
                    logger.info(f"Imported {len(local_tracks)} tracks from Spotify playlist")

                    # Update name if different from what was imported
                    if playlist_name != local_playlist.name:
                        playlist_repo.update(local_playlist.id, {"name": playlist_name})

                    QMessageBox.information(
                        parent,
                        "Import Successful",
                        f"Playlist '{playlist_name}' imported successfully.\n"
                        f"{len(local_tracks)} tracks imported.",
                    )

                    logger.info(
                        f"Successfully imported Spotify playlist '{playlist_name}' "
                        f"with {len(local_tracks)} tracks"
                    )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error importing Spotify playlist: {e}")
                    QMessageBox.critical(
                        parent, "Import Error", f"Failed to import playlist: {str(e)}"
                    )
                    return False

        except Exception as e:
            logger.exception(f"Error importing Spotify playlist: {e}")
            QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False

    def export_playlist(
        self, playlist_id: str, target_platform: str, parent: QWidget | None = None
    ) -> bool:
        """Export a local playlist to Spotify.

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
                "You must be authenticated with Spotify to export playlists.",
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
                parent, mode="export", platform="spotify", default_name=source_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.client)

            # Check if this playlist is already linked to Spotify
            platform_id = source_playlist.get_platform_id("spotify")

            # Show progress information
            QMessageBox.information(
                parent,
                "Exporting Playlist",
                "Exporting playlist to Spotify. This may take a moment...",
            )

            # Export the playlist
            _ = sync_manager.export_playlist(  # Ignoring returned ID since we don't use it
                local_playlist_id=int(playlist_id),
                platform_playlist_id=platform_id,
                platform_playlist_name=playlist_name,
            )

            # Show success message
            QMessageBox.information(
                parent,
                "Export Successful",
                f"Successfully exported playlist '{source_playlist.name}' "
                f"to Spotify as '{playlist_name}'.",
            )

            # Refresh playlists
            self.refresh()

            return True
        except Exception as e:
            logger.exception(f"Error exporting playlist to Spotify: {e}")
            QMessageBox.critical(parent, "Export Failed", f"Failed to export playlist: {str(e)}")
            return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a local playlist with its Spotify counterpart.

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
                "You must be authenticated with Spotify to sync playlists.",
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

            # Check if this playlist is linked to Spotify
            platform_id = source_playlist.get_platform_id("spotify")

            if not platform_id:
                QMessageBox.warning(
                    parent,
                    "Not Linked to Spotify",
                    f"Playlist '{source_playlist.name}' is not linked to Spotify. "
                    "Please export it first.",
                )
                return False

            # Show progress information
            QMessageBox.information(
                parent,
                "Syncing Playlist",
                "Syncing playlist with Spotify. This may take a moment...",
            )

            # Create a sync manager
            sync_manager = PlatformSyncManager(self.client)

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
            QMessageBox.information(
                parent,
                "Sync Successful",
                f"Successfully synced playlist '{source_playlist.name}' with Spotify.\n"
                f"Added {tracks_added_to_library} tracks to library, "
                f"added {tracks_added_to_platform} tracks to Spotify.",
            )

            # Refresh playlists
            self.notify_refresh_needed()

            return True
        except Exception as e:
            logger.exception(f"Error syncing playlist with Spotify: {e}")
            QMessageBox.critical(parent, "Sync Failed", f"Failed to sync playlist: {str(e)}")
            return False
