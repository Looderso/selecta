# src/selecta/ui/components/playlist/spotify/spotify_playlist_data_provider.py
"""Spotify playlist data provider implementation."""

import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.models.db import Playlist, PlaylistTrack, Track, TrackPlatformInfo
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.spotify.spotify_playlist_item import SpotifyPlaylistItem
from selecta.ui.components.playlist.spotify.spotify_track_item import SpotifyTrackItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.import_export_playlist_dialog import ImportExportPlaylistDialog


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
            # First, get the playlist details from Spotify
            spotify_tracks, spotify_playlist = self.client.import_playlist_to_local(
                str(playlist_id)
            )

            # Show the import dialog to let the user set the playlist name
            dialog = ImportExportPlaylistDialog(
                parent, mode="import", platform="spotify", default_name=spotify_playlist.name
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create repositories
            track_repo = TrackRepository()
            playlist_repo = PlaylistRepository()

            # First check if a playlist with the same Spotify ID already exists
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

                # Use the existing playlist
                local_playlist = existing_playlist
                # But update the name if it changed
                if playlist_name != local_playlist.name:
                    local_playlist.name = playlist_name
                    playlist_repo.session.commit()
            else:
                # Create a new local playlist linked to Spotify
                local_playlist = Playlist(
                    name=playlist_name,
                    description=spotify_playlist.description,
                    is_local=False,
                    source_platform="spotify",
                    platform_id=str(playlist_id),
                )
                playlist_repo.session.add(local_playlist)
                playlist_repo.session.commit()

            # Counter for tracks added/updated
            tracks_added = 0
            tracks_updated = 0

            # First fetch all existing Spotify tracks in one query to avoid repeated DB lookups
            # Get all Spotify IDs for the tracks we're importing
            spotify_ids = [track.id for track in spotify_tracks]

            # Get all tracks that already exist in the database in a single query
            existing_tracks_info = {}
            with track_repo.session.no_autoflush:
                # Only select id, track_id and platform_id to avoid querying missing columns
                track_infos = (
                    track_repo.session.query(
                        TrackPlatformInfo.id,
                        TrackPlatformInfo.track_id,
                        TrackPlatformInfo.platform_id,
                    )
                    .filter(
                        TrackPlatformInfo.platform == "spotify",
                        TrackPlatformInfo.platform_id.in_(spotify_ids),
                    )
                    .all()
                )

                for info in track_infos:
                    # Result is now a tuple with (id, track_id, platform_id)
                    existing_tracks_info[info[2]] = info[1]

            # Also get all tracks already in the playlist to avoid duplication checks
            existing_playlist_tracks = set()
            with playlist_repo.session.no_autoflush:
                if existing_tracks_info:
                    # Only get existing tracks if we have any
                    track_ids = list(existing_tracks_info.values())
                    playlist_tracks = (
                        playlist_repo.session.query(PlaylistTrack)
                        .filter(
                            PlaylistTrack.playlist_id == local_playlist.id,
                            PlaylistTrack.track_id.in_(track_ids),
                        )
                        .all()
                    )

                    for pt in playlist_tracks:
                        existing_playlist_tracks.add(pt.track_id)

            # Find next position in playlist once instead of for each track
            next_position = 0
            with playlist_repo.session.no_autoflush:
                position = (
                    playlist_repo.session.query(PlaylistTrack.position)
                    .filter(PlaylistTrack.playlist_id == local_playlist.id)
                    .order_by(PlaylistTrack.position.desc())
                    .first()
                )
                next_position = (position[0] + 1) if position else 0

            # Batch process all tracks
            now = datetime.now(UTC)
            new_tracks_to_add = []
            new_platform_infos = []
            new_playlist_tracks = []

            # Process each track
            for sp_track in spotify_tracks:
                if sp_track.id in existing_tracks_info:
                    # Track exists, make sure it's in the playlist
                    track_id = existing_tracks_info[sp_track.id]

                    # Check if it's already in the playlist
                    if track_id in existing_playlist_tracks:
                        # Already in the playlist, nothing to do
                        tracks_updated += 1
                        continue

                    # Need to add existing track to playlist
                    new_playlist_tracks.append(
                        PlaylistTrack(
                            playlist_id=local_playlist.id,
                            track_id=track_id,
                            position=next_position,
                            added_at=now,
                        )
                    )
                    next_position += 1
                    tracks_updated += 1
                else:
                    # Create a new track
                    track = Track(
                        title=sp_track.name,
                        artist=", ".join(sp_track.artist_names),
                        duration_ms=sp_track.duration_ms,
                        year=sp_track.album_release_date[:4]
                        if sp_track.album_release_date
                        else None,
                        is_available_locally=False,  # Spotify tracks aren't local files
                    )
                    new_tracks_to_add.append(track)

                    # Add to batch for adding platform info once we have track IDs
                    new_platform_infos.append((track, sp_track))
                    tracks_added += 1

            # Add all new tracks in a batch
            if new_tracks_to_add:
                track_repo.session.add_all(new_tracks_to_add)
                track_repo.session.flush()  # Get the IDs

                # Now create platform infos
                platform_infos_to_add = []
                for track, sp_track in new_platform_infos:
                    platform_data = json.dumps(sp_track.to_dict())
                    platform_infos_to_add.append(
                        TrackPlatformInfo(
                            track_id=track.id,
                            platform="spotify",
                            platform_id=sp_track.id,
                            uri=sp_track.uri,
                            platform_data=platform_data,
                        )
                    )

                track_repo.session.add_all(platform_infos_to_add)

                # Create playlist tracks for new tracks
                for track in new_tracks_to_add:
                    new_playlist_tracks.append(
                        PlaylistTrack(
                            playlist_id=local_playlist.id,
                            track_id=track.id,
                            position=next_position,
                            added_at=now,
                        )
                    )
                    next_position += 1

            # Add all playlist tracks in a batch
            if new_playlist_tracks:
                playlist_repo.session.add_all(new_playlist_tracks)

            # Perform a single commit for all changes using the centralized session handling
            try:
                # Just commit with our improved session handling
                playlist_repo.session.commit()
                logger.debug("Playlist import committed successfully")
            except Exception as e:
                logger.error(f"Failed to commit playlist import: {e}")
                playlist_repo.session.rollback()
                raise

            # Show success message
            QMessageBox.information(
                parent,
                "Import Successful",
                f"Playlist '{playlist_name}' imported successfully.\n"
                f"{tracks_added} new tracks added, {tracks_updated} existing tracks found.",
            )

            # Refresh the UI to show the imported playlist
            self.notify_refresh_needed()

            return True

        except Exception as e:
            logger.exception(f"Error importing Spotify playlist: {e}")
            QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False
