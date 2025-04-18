# src/selecta/ui/components/playlist/spotify/spotify_playlist_data_provider.py
"""Spotify playlist data provider implementation."""

from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
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

        for sp_playlist in spotify_playlists:
            # Convert to PlaylistItem
            playlist_items.append(
                SpotifyPlaylistItem(
                    name=sp_playlist["name"],
                    item_id=sp_playlist["id"],
                    owner=sp_playlist["owner"]["display_name"],
                    description=sp_playlist.get("description", ""),
                    is_collaborative=sp_playlist.get("collaborative", False),
                    is_public=sp_playlist.get("public", True),
                    track_count=sp_playlist["tracks"]["total"],
                    images=sp_playlist.get("images", []),
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

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any) -> None:
        """Show a context menu for a Spotify playlist.

        Args:
            tree_view: The tree view
            position: Position where the context menu was requested
        """
        # Get the playlist item at this position
        index = tree_view.indexAt(position)
        if not index.isValid():
            return

        # Get the playlist item
        playlist_item = index.internalPointer()
        if not playlist_item or playlist_item.is_folder():
            return

        # Create context menu
        menu = QMenu(tree_view)

        # Add import action
        import_action = menu.addAction("Import to Local Library")
        import_action.triggered.connect(
            lambda: self.import_playlist(playlist_item.item_id, tree_view)
        )  # type: ignore

        # Show the menu at the cursor position
        menu.exec(tree_view.viewport().mapToGlobal(position))  # type: ignore

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
            from selecta.core.platform.sync_manager import PlatformSyncManager

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
                    tracks_added, tracks_exported = sync_manager.sync_playlist(existing_playlist.id)

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
                    # Import the playlist
                    local_playlist, local_tracks = sync_manager.import_playlist(str(playlist_id))

                    # Update name if different from what was imported
                    if playlist_name != local_playlist.name:
                        playlist_repo.update(local_playlist.id, {"name": playlist_name})

                    QMessageBox.information(
                        parent,
                        "Import Successful",
                        f"Playlist '{playlist_name}' imported successfully.\n"
                        f"{len(local_tracks)} tracks imported.",
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
