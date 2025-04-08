# src/selecta/ui/components/playlist/rekordbox/rekordbox_playlist_data_provider.py
"""Rekordbox playlist data provider implementation."""

import datetime
import json
import os
from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.models.db import Playlist, PlaylistTrack, Track, TrackPlatformInfo
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_playlist_item import RekordboxPlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_track_item import RekordboxTrackItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.import_export_playlist_dialog import ImportExportPlaylistDialog


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

            for rb_playlist in rekordbox_playlists:
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

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any) -> None:
        """Show a context menu for a Rekordbox playlist.

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
            # First, get the playlist details from Rekordbox
            rekordbox_tracks, rekordbox_playlist = self.client.import_playlist_to_local(
                str(playlist_id)
            )

            # Show the import dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="import", platform="rekordbox", default_name=rekordbox_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create repositories
            track_repo = TrackRepository()
            playlist_repo = PlaylistRepository()

            # First check if a playlist with the same Rekordbox ID already exists
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

                # Use the existing playlist
                local_playlist = existing_playlist
                # But update the name if it changed
                if playlist_name != local_playlist.name:
                    local_playlist.name = playlist_name
                    playlist_repo.session.commit()
            else:
                # Create a new local playlist linked to Rekordbox
                local_playlist = Playlist(
                    name=playlist_name,
                    description="Imported from Rekordbox",
                    is_local=False,
                    source_platform="rekordbox",
                    platform_id=str(playlist_id),
                )
                playlist_repo.session.add(local_playlist)
                playlist_repo.session.commit()

            # Counter for tracks added/updated
            tracks_added = 0
            tracks_updated = 0
            tracks_with_local_files = 0

            # Process each track
            for rb_track in rekordbox_tracks:
                # Check if this track already exists in our database
                existing_track = track_repo.get_by_platform_id("rekordbox", str(rb_track.id))

                if existing_track:
                    # Track exists, make sure it's in the playlist
                    tracks_updated += 1
                    track = existing_track

                    # Check if it has a local file
                    if track.local_path and os.path.exists(track.local_path):
                        tracks_with_local_files += 1
                else:
                    # Create a new track
                    track = Track(
                        title=rb_track.title,
                        artist=rb_track.artist_name,
                        duration_ms=rb_track.duration_ms,
                        bpm=rb_track.bpm,
                        year=None,  # Rekordbox doesn't provide year directly
                        is_available_locally=False,  # Will update if file exists
                    )

                    # Check if the file exists (if path is provided)
                    if rb_track.folder_path and os.path.exists(rb_track.folder_path):
                        track.local_path = rb_track.folder_path
                        track.is_available_locally = True
                        tracks_with_local_files += 1

                    track_repo.session.add(track)
                    track_repo.session.flush()  # Get the ID

                    # Add Rekordbox platform info
                    platform_data = json.dumps(rb_track.to_dict())
                    track_info = TrackPlatformInfo(
                        track_id=track.id,
                        platform="rekordbox",
                        platform_id=str(rb_track.id),
                        uri=None,
                        platform_data=platform_data,
                        last_synced=datetime.datetime.now(datetime.UTC),
                        needs_update=False,
                    )
                    track_repo.session.add(track_info)
                    track_repo.session.flush()

                    tracks_added += 1

                # Check if the track is already in the playlist
                existing_playlist_track = (
                    playlist_repo.session.query(PlaylistTrack)
                    .filter(
                        PlaylistTrack.playlist_id == local_playlist.id,
                        PlaylistTrack.track_id == track.id,
                    )
                    .first()
                )

                if not existing_playlist_track:
                    # Add to playlist
                    playlist_repo.add_track(local_playlist.id, track.id)

            # Commit all changes
            playlist_repo.session.commit()

            # Show success message
            QMessageBox.information(
                parent,
                "Import Successful",
                f"Playlist '{playlist_name}' imported successfully.\n"
                f"{tracks_added} new tracks added, {tracks_updated} existing tracks found.\n"
                f"{tracks_with_local_files} tracks have local audio files available.",
            )

            # Refresh the UI to show the imported playlist
            self.notify_refresh_needed()

            return True

        except Exception as e:
            logger.exception(f"Error importing Rekordbox playlist: {e}")
            QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False
