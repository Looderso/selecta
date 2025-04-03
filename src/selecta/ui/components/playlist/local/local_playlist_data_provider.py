# src/selecta/ui/components/playlist/local/local_playlist_data_provider.py
"""Local database playlist data provider implementation."""

import os
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget
from sqlalchemy.orm import Session

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Track, TrackPlatformInfo
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.utils.type_helpers import column_to_bool, column_to_int, column_to_str
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.local.local_playlist_item import LocalPlaylistItem
from selecta.ui.components.playlist.local.local_track_item import LocalTrackItem
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.import_export_playlist_dialog import ImportExportPlaylistDialog


class LocalPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for local database playlists."""

    def __init__(self, session: Session | None = None, cache_timeout: float = 300.0):
        """Initialize the local playlist data provider.

        Args:
            session: Database session (optional)
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Use the global session from get_session() - this ensures we're using the singleton engine
        self.session = get_session()
        self.playlist_repo = PlaylistRepository(self.session)
        self.track_repo = TrackRepository(self.session)

        # Platform clients (will be initialized on-demand)
        self._spotify_client = None
        self._rekordbox_client = None

        # Initialize the abstract provider with None as client (not needed for local)
        super().__init__(None, cache_timeout)

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from the local database.

        Returns:
            List of playlist items
        """
        db_playlists = self.playlist_repo.get_all()
        playlist_items = []

        for pl in db_playlists:
            # Get the track count
            track_count = len(pl.tracks) if pl.tracks is not None else 0

            playlist_items.append(
                LocalPlaylistItem(
                    name=column_to_str(pl.name),
                    item_id=pl.id,
                    parent_id=pl.parent_id,
                    is_folder_flag=column_to_bool(pl.is_folder),
                    description=column_to_str(pl.description),
                    track_count=track_count,
                    source_platform=column_to_str(pl.source_platform),
                    platform_id=column_to_str(pl.platform_id),
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from the local database.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        # Get the playlist with its associated track relationships
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            return []

        # Create a mapping of track_id -> PlaylistTrack for quick access to added_at dates
        playlist_track_map = {pt.track_id: pt for pt in playlist.tracks}

        # Get the actual tracks
        tracks = self.playlist_repo.get_playlist_tracks(playlist_id)
        logger.debug(f"Loaded {len(tracks)} tracks from database for playlist {playlist_id}")
        track_items = []

        # Also log how many playlist_tracks we found in the playlist object
        logger.debug(f"Playlist has {len(playlist.tracks)} playlist_track associations")

        for track in tracks:
            # Find the corresponding playlist track to get added_at date
            added_at = None
            if track.id in playlist_track_map:
                added_at = playlist_track_map[track.id].added_at

            # Extract album name if available
            album_name = track.album.title if track.album else None

            # Get first genre if available
            genre = None
            if track.genres and len(track.genres) > 0:
                genre = track.genres[0].name

            # Get attribute for BPM if available
            bpm = None
            tags = []
            if track.attributes:
                for attr in track.attributes:
                    if attr.name == "bpm":
                        bpm = attr.value
                    elif attr.name == "tag":
                        tags.append(attr.value)

            # Get platform info
            platform_info = []

            # Try to get platform info, but handle database schema conflicts
            try:
                track_platform_info = self.track_repo.get_all_platform_info(column_to_int(track.id))
            except Exception as e:
                logger.warning(f"Failed to get platform info for track {track.id}: {e}")
                track_platform_info = []

            for info in track_platform_info:
                platform_data = {
                    "platform": column_to_str(info.platform),
                    "platform_id": column_to_str(info.platform_id),
                    "uri": column_to_str(info.uri) if column_to_str(info.uri) else None,
                }

                # Add additional platform-specific data if available
                if column_to_str(info.platform_data):
                    import json

                    try:
                        additional_data = json.loads(column_to_str(info.platform_data))
                        platform_data.update(additional_data)
                    except (json.JSONDecodeError, TypeError):
                        pass

                platform_info.append(platform_data)

            # Check if track has images directly from the images relationship
            has_image = False
            if hasattr(track, "images") and track.images and len(track.images) > 0:
                has_image = True

            track_items.append(
                LocalTrackItem(
                    track_id=track.id,
                    title=column_to_str(track.title),
                    artist=column_to_str(track.artist),
                    duration_ms=column_to_int(track.duration_ms),
                    album=album_name,
                    added_at=added_at,
                    local_path=column_to_str(track.local_path),
                    genre=genre,
                    bpm=bpm,
                    tags=tags,
                    platform_info=platform_info,
                    quality=column_to_int(track.quality),
                    has_image=has_image,
                )
            )

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Local Database"

    def _ensure_authenticated(self) -> bool:
        """For local database, authentication is not needed.

        Returns:
            Always True since we don't need authentication for local database
        """
        return True

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any) -> None:
        """Show a context menu for a local playlist.

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
        if not playlist_item:
            return

        # Create context menu
        menu = QMenu(tree_view)

        # Basic operations available for all local playlists
        if not playlist_item.is_folder():
            # For imported playlists, allow rename and sync
            if hasattr(playlist_item, "source_platform") and playlist_item.source_platform:
                # Add sync action for imported playlists
                sync_action = menu.addAction(
                    f"Sync with {playlist_item.source_platform.capitalize()}"
                )
                sync_action.triggered.connect(
                    lambda: self._sync_playlist(playlist_item.item_id, tree_view)
                )

                menu.addSeparator()

                # Show rename for imported playlists
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(
                    lambda: self._rename_playlist(playlist_item.item_id, tree_view)
                )
            else:
                # For local playlists, show export menu
                export_menu = menu.addMenu("Export to...")

                # Add spotify export option
                spotify_action = export_menu.addAction("Spotify")
                spotify_action.triggered.connect(
                    lambda: self.export_playlist(playlist_item.item_id, "spotify", tree_view)
                )  # type: ignore

                # Add rekordbox export option
                rekordbox_action = export_menu.addAction("Rekordbox")
                rekordbox_action.triggered.connect(
                    lambda: self.export_playlist(playlist_item.item_id, "rekordbox", tree_view)
                )  # type: ignore

                # Add rename and remove options for local playlists
                menu.addSeparator()
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(
                    lambda: self._rename_playlist(playlist_item.item_id, tree_view)
                )

        # Add remove action for both folders and playlists that are not imported
        if not (hasattr(playlist_item, "source_platform") and playlist_item.source_platform):
            remove_action = menu.addAction("Remove")
            remove_action.triggered.connect(
                lambda: self._remove_playlist(playlist_item.item_id, tree_view)
            )

        # Show the menu at the cursor position
        menu.exec(tree_view.viewport().mapToGlobal(position))  # type: ignore

    def _rename_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Rename a playlist.

        Args:
            playlist_id: ID of the playlist to rename
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            QMessageBox.critical(
                parent, "Rename Error", f"Playlist with ID {playlist_id} not found."
            )
            return False

        # Show input dialog for new name
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            parent, "Rename Playlist", "Enter new playlist name:", text=playlist.name
        )

        if not ok or not new_name.strip():
            return False

        try:
            # Update the playlist name
            self.playlist_repo.update(playlist_id, {"name": new_name.strip()})

            # Refresh the UI
            self.refresh()
            return True
        except Exception as e:
            logger.exception(f"Error renaming playlist: {e}")
            QMessageBox.critical(parent, "Rename Error", f"Failed to rename playlist: {str(e)}")
            return False

    def _remove_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Remove a playlist.

        Args:
            playlist_id: ID of the playlist to remove
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            QMessageBox.critical(
                parent, "Remove Error", f"Playlist with ID {playlist_id} not found."
            )
            return False

        # For folders, check if they have children
        if playlist.is_folder and playlist.children:
            response = QMessageBox.question(
                parent,
                "Remove Folder",
                f"The folder '{playlist.name}' contains {len(playlist.children)} "
                "playlists/folders. "
                "Do you want to remove it and all its contents?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return False

        # For playlists, confirm removal
        else:
            track_count = len(playlist.tracks) if playlist.tracks else 0
            response = QMessageBox.question(
                parent,
                "Remove Playlist",
                f"Are you sure you want to remove the playlist '{playlist.name}'? "
                f"It contains {track_count} tracks. "
                "The tracks will remain in your library.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return False

        try:
            # Delete the playlist
            self.playlist_repo.delete(playlist_id)

            # Refresh the UI
            self.refresh()
            return True
        except Exception as e:
            logger.exception(f"Error removing playlist: {e}")
            QMessageBox.critical(parent, "Remove Error", f"Failed to remove playlist: {str(e)}")
            return False

    def create_new_playlist(self, parent: QWidget | None = None) -> bool:
        """Create a new playlist or folder.

        Args:
            parent: Parent widget for the dialog

        Returns:
            True if successful, False otherwise
        """
        # Import here to avoid circular imports
        from selecta.ui.create_playlist_dialog import CreatePlaylistDialog

        # Get all folder playlists for parent selection
        folders = []
        try:
            all_playlists = self.playlist_repo.get_all()
            for pl in all_playlists:
                if pl.is_folder:
                    folders.append((pl.id, pl.name))
        except Exception as e:
            logger.warning(f"Failed to fetch folders for playlist creation: {e}")

        # Show create playlist dialog
        dialog = CreatePlaylistDialog(parent, available_folders=folders)

        if dialog.exec() != CreatePlaylistDialog.DialogCode.Accepted:
            return False

        values = dialog.get_values()
        name = values["name"]
        is_folder = values["is_folder"]
        parent_id = values["parent_id"]

        if not name:
            QMessageBox.warning(
                parent, "Missing Information", "Please enter a name for the playlist."
            )
            return False

        try:
            # Import here to avoid circular imports
            from selecta.core.data.models.db import Playlist

            # Create the new playlist or folder
            new_playlist = Playlist(
                name=name,
                is_folder=is_folder,
                is_local=True,
                parent_id=parent_id,
                description="",
            )

            self.playlist_repo.session.add(new_playlist)
            self.playlist_repo.session.commit()

            # Refresh the UI
            self.refresh()

            QMessageBox.information(
                parent,
                "Playlist Created",
                f"The {'folder' if is_folder else 'playlist'} '{name}' was created successfully.",
            )

            return True
        except Exception as e:
            logger.exception(f"Error creating playlist: {e}")
            QMessageBox.critical(parent, "Creation Error", f"Failed to create playlist: {str(e)}")
            return False

    def _init_spotify_client(self) -> SpotifyClient | None:
        """Initialize the Spotify client if not already done.

        Returns:
            SpotifyClient if successfully initialized, None otherwise
        """
        if self._spotify_client is not None:
            return self._spotify_client

        try:
            settings_repo = SettingsRepository()
            client = PlatformFactory.create("spotify", settings_repo)
            if isinstance(client, SpotifyClient):
                self._spotify_client = client
                return self._spotify_client
            return None
        except Exception as e:
            logger.exception(f"Failed to initialize Spotify client: {e}")
            return None

    def _init_rekordbox_client(self) -> RekordboxClient | None:
        """Initialize the Rekordbox client if not already done.

        Returns:
            RekordboxClient if successfully initialized, None otherwise
        """
        if self._rekordbox_client is not None:
            return self._rekordbox_client

        try:
            settings_repo = SettingsRepository()
            client = PlatformFactory.create("rekordbox", settings_repo)
            if isinstance(client, RekordboxClient):
                self._rekordbox_client = client
                return self._rekordbox_client
            return None
        except Exception as e:
            logger.exception(f"Failed to initialize Rekordbox client: {e}")
            return None

    def _sync_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Sync a playlist with its source platform.

        This function performs two-way sync:
        1. Import new tracks from the platform to the local playlist
        2. Export local tracks back to the platform

        All tracks in the local playlist are preserved.

        Args:
            playlist_id: ID of the playlist to sync
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Get the playlist from the database
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            QMessageBox.critical(parent, "Sync Error", f"Playlist with ID {playlist_id} not found.")
            return False

        # Check if this is an imported playlist
        if playlist.is_local or not playlist.source_platform or not playlist.platform_id:
            QMessageBox.warning(
                parent,
                "Sync Error",
                "This playlist was not imported from a platform and cannot be synced.",
            )
            return False

        # Initialize the appropriate client based on the source platform
        client = None
        if playlist.source_platform == "spotify":
            client = self._init_spotify_client()
        elif playlist.source_platform == "rekordbox":
            client = self._init_rekordbox_client()

            # Check if Rekordbox is running
            try:
                import psutil
                from pyrekordbox.config import get_rekordbox_pid

                pid = get_rekordbox_pid()
                if pid:
                    try:
                        process = psutil.Process(pid)
                        status = process.status()

                        # Only warn for active processes (running/sleeping)
                        if status in ["running", "sleeping"]:
                            response = QMessageBox.question(
                                parent,
                                "Rekordbox Running",
                                f"Rekordbox is currently running (status: {status}). "
                                "This might cause database conflicts.\n\n"
                                "Do you want to continue anyway?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            )

                            if response != QMessageBox.StandardButton.Yes:
                                return False
                    except Exception:
                        # If we can't get the process status, just continue
                        pass
            except Exception:
                # If we can't check for Rekordbox, just continue
                pass
        else:
            QMessageBox.warning(
                parent,
                "Platform Not Supported",
                f"Syncing with {playlist.source_platform} is not supported.",
            )
            return False

        if not client:
            QMessageBox.warning(
                parent,
                "Authentication Required",
                f"You need to be authenticated with {playlist.source_platform.capitalize()} "
                "to sync playlists.",
            )
            return False

        try:
            # Get the latest tracks from the platform
            if playlist.source_platform == "spotify" or playlist.source_platform == "rekordbox":
                platform_tracks, platform_playlist = client.import_playlist_to_local(
                    playlist.platform_id
                )
            else:
                return False  # Shouldn't reach here due to earlier check

            # Get repositories
            track_repo = self.track_repo
            playlist_repo = self.playlist_repo

            # Update playlist name if it changed on the platform
            if platform_playlist.name != playlist.name:
                response = QMessageBox.question(
                    parent,
                    "Update Playlist Name",
                    f"The playlist name has changed on {playlist.source_platform.capitalize()} "
                    f"from '{playlist.name}' to '{platform_playlist.name}'. "
                    "Do you want to update it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if response == QMessageBox.StandardButton.Yes:
                    playlist.name = platform_playlist.name
                    playlist_repo.session.commit()

            # Track updates
            tracks_added = 0
            tracks_updated = 0

            # STEP 1: Import tracks from platform to local playlist

            # Get existing tracks in the playlist
            current_tracks = playlist_repo.get_playlist_tracks(playlist_id)

            # Create a mapping of platform tracks by ID
            # and collect IDs in the remote platform playlist
            platform_tracks_by_id = {}
            platform_playlist_ids = set()  # Track IDs in the remote platform playlist

            for platform_track in platform_tracks:
                if playlist.source_platform == "spotify":
                    platform_id = platform_track.id
                elif playlist.source_platform == "rekordbox":
                    platform_id = str(platform_track.id)
                else:
                    continue
                platform_tracks_by_id[platform_id] = platform_track
                platform_playlist_ids.add(platform_id)

            # Track what's already in our local playlist
            local_playlist_platform_ids = set()  # Platform IDs already in our local playlist
            tracks_with_this_platform_info = {}  # Map of platform_id -> Track
            tracks_with_other_platform_info = []  # Tracks with metadata from other platforms
            tracks_without_platform_info = []  # Tracks without any platform metadata

            for track in current_tracks:
                has_this_platform_info = False
                has_other_platform_info = False

                # Check each platform info associated with this track
                for platform_info in track.platform_info:
                    if platform_info.platform == playlist.source_platform:
                        # This track has metadata from our source platform
                        has_this_platform_info = True
                        tracks_with_this_platform_info[platform_info.platform_id] = track
                        local_playlist_platform_ids.add(platform_info.platform_id)
                    else:
                        # This track has metadata from another platform
                        has_other_platform_info = True

                if not has_this_platform_info and has_other_platform_info:
                    tracks_with_other_platform_info.append(track)
                elif not has_this_platform_info and not has_other_platform_info:
                    tracks_without_platform_info.append(track)

            # Add new tracks from the platform to our local playlist
            for platform_id, platform_track in platform_tracks_by_id.items():
                if platform_id in local_playlist_platform_ids:
                    # Track exists, nothing to do
                    tracks_updated += 1
                else:
                    # Add new track from platform
                    if playlist.source_platform == "spotify":
                        # Create a new track
                        track = Track(
                            title=platform_track.name,
                            artist=", ".join(platform_track.artist_names),
                            duration_ms=platform_track.duration_ms,
                            year=platform_track.album_release_date[:4]
                            if platform_track.album_release_date
                            else None,
                            is_available_locally=False,  # Spotify tracks aren't local files
                        )
                        track_repo.session.add(track)
                        track_repo.session.flush()  # Get the ID

                        # Add Spotify platform info
                        import json

                        platform_data = json.dumps(platform_track.to_dict())
                        track_info = TrackPlatformInfo(
                            track_id=track.id,
                            platform="spotify",
                            platform_id=platform_track.id,
                            uri=platform_track.uri,
                            platform_data=platform_data,
                        )
                        track_repo.session.add(track_info)
                        track_repo.session.flush()

                    elif playlist.source_platform == "rekordbox":
                        # Create a new track
                        track = Track(
                            title=platform_track.title,
                            artist=platform_track.artist_name,
                            duration_ms=platform_track.duration_ms,
                            bpm=platform_track.bpm,
                            year=None,  # Rekordbox doesn't provide year directly
                            is_available_locally=False,  # Will update if file exists
                        )

                        # Check if the file exists (if path is provided)
                        if platform_track.folder_path and os.path.exists(
                            platform_track.folder_path
                        ):
                            track.local_path = platform_track.folder_path
                            track.is_available_locally = True

                        track_repo.session.add(track)
                        track_repo.session.flush()  # Get the ID

                        # Add Rekordbox platform info
                        import json

                        platform_data = json.dumps(platform_track.to_dict())
                        track_info = TrackPlatformInfo(
                            track_id=track.id,
                            platform="rekordbox",
                            platform_id=str(platform_track.id),
                            uri=None,
                            platform_data=platform_data,
                        )
                        track_repo.session.add(track_info)
                        track_repo.session.flush()

                    # Add to playlist
                    playlist_repo.add_track(playlist.id, track.id)
                    tracks_added += 1

            # STEP 2: Find tracks in local playlist that need to be exported to the platform
            # Track IDs to send to platform (already in platform collection)
            tracks_to_export = []
            # Local file tracks that need to be added to platform collection first
            tracks_to_add_and_export = []
            # Tracks that can't be exported (no platform metadata and no local file)

            tracks_not_exportable = []
            # Check each track with metadata from this platform
            for platform_id, track in tracks_with_this_platform_info.items():
                if platform_id not in platform_playlist_ids:
                    # This track has platform metadata but isn't in the platform playlist yet
                    # This is a track the user added locally that should be exported
                    if playlist.source_platform == "spotify":
                        # Find the URI for Spotify
                        for platform_info in track.platform_info:
                            if platform_info.platform == "spotify" and platform_info.uri:
                                tracks_to_export.append(platform_info.uri)
                                break
                    elif playlist.source_platform == "rekordbox":
                        # Use the ID directly for Rekordbox
                        tracks_to_export.append(int(platform_id))

            # For tracks with other platform metadata or no metadata, check if they have local files
            # that could be added to the platform collection first
            if playlist.source_platform == "rekordbox":  # Only applicable for Rekordbox right now
                for track in tracks_with_other_platform_info + tracks_without_platform_info:
                    if (
                        track.is_available_locally
                        and track.local_path
                        and os.path.exists(track.local_path)
                    ):
                        # This track has a local audio file that could be added to Rekordbox first
                        tracks_to_add_and_export.append(track)
                    else:
                        tracks_not_exportable.append(track)
            else:
                # For Spotify, we can't add local tracks to the collection
                tracks_not_exportable.extend(
                    tracks_with_other_platform_info + tracks_without_platform_info
                )

            # Count tracks that can't be exported
            non_exportable_count = len(tracks_not_exportable)

            # STEP 3: Export tracks to platform if needed
            exports_successful = 0
            adds_successful = 0

            # First handle tracks that are already in the platform collection
            if tracks_to_export:
                try:
                    if playlist.source_platform == "spotify":
                        # Export to Spotify
                        response = QMessageBox.question(
                            parent,
                            "Export to Spotify",
                            f"Found {len(tracks_to_export)} tracks in the local playlist that are "
                            "not in the Spotify playlist. "
                            f"Do you want to add them to the Spotify playlist?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        )

                        if response == QMessageBox.StandardButton.Yes:
                            client.export_tracks_to_playlist(
                                playlist_name=platform_playlist.name,
                                track_uris=tracks_to_export,
                                existing_playlist_id=playlist.platform_id,
                            )
                            exports_successful = len(tracks_to_export)

                    elif playlist.source_platform == "rekordbox":
                        # Export to Rekordbox
                        response = QMessageBox.question(
                            parent,
                            "Export to Rekordbox",
                            f"Found {len(tracks_to_export)} tracks in the local playlist that are "
                            "not in the Rekordbox playlist. "
                            f"Do you want to add them to the Rekordbox playlist?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        )

                        if response == QMessageBox.StandardButton.Yes:
                            # Add each track to the playlist in Rekordbox
                            for track_id in tracks_to_export:
                                try:
                                    # First try without force option
                                    client.add_track_to_playlist(playlist.platform_id, track_id)
                                except RuntimeError as re:
                                    error_msg = str(re)
                                    # Handle Rekordbox running error specifically
                                    if "Rekordbox is running" in error_msg:
                                        # Ask user if they want to continue with force option
                                        response = QMessageBox.question(
                                            parent,
                                            "Rekordbox Running",
                                            "Rekordbox is currently running. This might cause "
                                            "database conflicts.\n\n"
                                            "Do you want to continue anyway?",
                                            QMessageBox.StandardButton.Yes
                                            | QMessageBox.StandardButton.No,
                                        )

                                        if response == QMessageBox.StandardButton.Yes:
                                            # User wants to continue, use force=True for this and
                                            # all remaining operations
                                            client.add_track_to_playlist(
                                                playlist.platform_id, track_id, force=True
                                            )
                                        else:
                                            # User doesn't want to continue, stop the operation
                                            raise RuntimeError(
                                                "Operation cancelled by user because "
                                                "Rekordbox is running"
                                            ) from re
                                    else:
                                        # Some other runtime error, just re-raise it
                                        raise
                            exports_successful = len(tracks_to_export)

                except Exception as e:
                    logger.exception(f"Error exporting tracks to {playlist.source_platform}: {e}")
                    QMessageBox.warning(
                        parent,
                        "Export Warning",
                        "Some tracks could not be exported to "
                        f"{playlist.source_platform.capitalize()}: {str(e)}",
                    )

            # Now handle local tracks that need to be added to the platform collection first
            if tracks_to_add_and_export and playlist.source_platform == "rekordbox":
                try:
                    # Ask user if they want to add the local files to Rekordbox
                    response = QMessageBox.question(
                        parent,
                        "Add Local Files to Rekordbox",
                        f"Found {len(tracks_to_add_and_export)} local "
                        "audio files that aren't in Rekordbox yet. "
                        f"Do you want to add them to Rekordbox and include them in the playlist?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if response == QMessageBox.StandardButton.Yes:
                        # We need to add each track to Rekordbox collection first,
                        # then to the playlist
                        # This is a placeholder - the actual implementation would depend on how your
                        # Rekordbox client allows adding local files to the collection
                        for track in tracks_to_add_and_export:
                            # Add the track to Rekordbox collection and then to the playlist
                            try:
                                if not track.local_path:
                                    continue

                                force_mode = False
                                try:
                                    # First try without force option
                                    rekordbox_track_id = client.add_track_to_collection(
                                        track.local_path
                                    )
                                except RuntimeError as re:
                                    error_msg = str(re)
                                    # Handle Rekordbox running error specifically
                                    if "Rekordbox is running" in error_msg:
                                        # Ask user if they want to continue with force option
                                        if not force_mode:
                                            response = QMessageBox.question(
                                                parent,
                                                "Rekordbox Running",
                                                "Rekordbox is currently running. This might cause "
                                                "database conflicts.\n\n"
                                                "Do you want to continue anyway?",
                                                QMessageBox.StandardButton.Yes
                                                | QMessageBox.StandardButton.No,
                                            )

                                            if response == QMessageBox.StandardButton.Yes:
                                                # User wants to continue, enable force mode
                                                # for this and all remaining operations
                                                force_mode = True
                                                rekordbox_track_id = client.add_track_to_collection(
                                                    track.local_path, force=True
                                                )
                                            else:
                                                # User doesn't want to continue, stop the operation
                                                raise RuntimeError(  # noqa: B904
                                                    "Operation cancelled by user because "
                                                    "Rekordbox is running"
                                                )
                                    else:
                                        # Some other runtime error, just re-raise it
                                        raise

                                if rekordbox_track_id:
                                    # Add to playlist, using force_mode if needed
                                    try:
                                        client.add_track_to_playlist(
                                            playlist.platform_id,
                                            rekordbox_track_id,
                                            force=force_mode,
                                        )
                                    except RuntimeError as re:
                                        error_msg = str(re)
                                        # Handle Rekordbox running error specifically
                                        if "Rekordbox is running" in error_msg and not force_mode:
                                            # Ask user if they want to continue with force option
                                            response = QMessageBox.question(
                                                parent,
                                                "Rekordbox Running",
                                                "Rekordbox is currently running. This might cause "
                                                "database conflicts.\n\n"
                                                "Do you want to continue anyway?",
                                                QMessageBox.StandardButton.Yes
                                                | QMessageBox.StandardButton.No,
                                            )

                                            if response == QMessageBox.StandardButton.Yes:
                                                # User wants to continue, enable force mode for this
                                                # and all remaining operations
                                                force_mode = True
                                                client.add_track_to_playlist(
                                                    playlist.platform_id,
                                                    rekordbox_track_id,
                                                    force=True,
                                                )
                                            else:
                                                # User doesn't want to continue, stop the operation
                                                raise RuntimeError(  # noqa: B904
                                                    "Operation cancelled by user because "
                                                    "Rekordbox is running"
                                                )
                                        else:
                                            # Some other runtime error, just re-raise it
                                            raise

                                    adds_successful += 1

                                    # Update local track with new Rekordbox metadata
                                    import json

                                    track_info = TrackPlatformInfo(
                                        track_id=track.id,
                                        platform="rekordbox",
                                        platform_id=str(rekordbox_track_id),
                                        uri=None,
                                        platform_data="{}",
                                    )
                                    track_repo.session.add(track_info)
                                    track_repo.session.flush()
                            except Exception as track_e:
                                logger.exception(
                                    f"Failed to add track {track.local_path} to "
                                    f"Rekordbox: {track_e}"
                                )

                        track_repo.session.commit()

                except Exception as e:
                    logger.exception(f"Error adding local files to Rekordbox: {e}")
                    QMessageBox.warning(
                        parent,
                        "Export Warning",
                        f"Some local files could not be added to Rekordbox: {str(e)}",
                    )

            # Update sync timestamp
            playlist.last_synced = datetime.now(UTC)
            playlist_repo.session.commit()

            # Show success message with detailed sync info
            import_message = (
                f"Playlist '{playlist.name}' synced successfully with "
                f"{playlist.source_platform.capitalize()}.\n\n"
                f"Import: {tracks_added} new tracks added from "
                f"{playlist.source_platform.capitalize()}, "
                f"{tracks_updated} tracks already existed."
            )

            export_message = ""
            if tracks_to_export:
                export_message = (
                    f"\n\nExport: {exports_successful} of {len(tracks_to_export)} "
                    "tracks were exported to {playlist.source_platform.capitalize()}."
                )

            local_files_message = ""
            if tracks_to_add_and_export:
                local_files_message = (
                    f"\n\nLocal Files: {adds_successful} of"
                    f" {len(tracks_to_add_and_export)} local audio files were added to "
                    f"{playlist.source_platform.capitalize()}."
                )
                if adds_successful == 0:
                    local_files_message += (
                        "\nAdding local files to Rekordbox will be supported in a future update."
                    )

            info_message = ""
            if non_exportable_count > 0:
                info_message = (
                    f"\n\nNote: {non_exportable_count} track(s) in the local playlist "
                    "couldn't be exported "
                    "(no local file or {playlist.source_platform.capitalize()} metadata)."
                )

            QMessageBox.information(
                parent,
                "Sync Successful",
                import_message + export_message + local_files_message + info_message,
            )

            # Refresh the UI
            self.refresh()

            return True

        except Exception as e:
            logger.exception(f"Error syncing playlist with {playlist.source_platform}: {e}")
            QMessageBox.critical(parent, "Sync Error", f"Failed to sync playlist: {str(e)}")
            return False

    def export_playlist(
        self, playlist_id: Any, target_platform: str, parent: QWidget | None = None
    ) -> bool:
        """Export a local playlist to a target platform.

        Args:
            playlist_id: ID of the local playlist to export
            target_platform: Platform to export to ('spotify', 'rekordbox')
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Get the playlist from the database
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            QMessageBox.critical(
                parent, "Export Error", f"Playlist with ID {playlist_id} not found."
            )
            return False

        # Get tracks in the playlist
        tracks = self.playlist_repo.get_playlist_tracks(playlist_id)
        if not tracks:
            QMessageBox.warning(parent, "Export Error", "The playlist is empty.")
            return False

        # Handle based on target platform
        if target_platform == "spotify":
            return self._export_to_spotify(playlist, tracks, parent)
        elif target_platform == "rekordbox":
            return self._export_to_rekordbox(playlist, tracks, parent)
        else:
            QMessageBox.critical(parent, "Export Error", f"Unsupported platform: {target_platform}")
            return False

    def _export_to_spotify(self, playlist: Any, tracks: list[Any], parent: QWidget | None) -> bool:
        """Export a playlist to Spotify.

        Args:
            playlist: The playlist to export
            tracks: The tracks in the playlist
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Initialize Spotify client
        spotify_client = self._init_spotify_client()
        if not spotify_client or not spotify_client.is_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Required",
                "You need to be authenticated with Spotify to export playlists. "
                "Please go to the Spotify section and authenticate first.",
            )
            return False

        # Show export dialog
        dialog = ImportExportPlaylistDialog(
            parent, mode="export", platform="spotify", default_name=playlist.name
        )

        if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
            return False

        dialog_values = dialog.get_values()
        playlist_name = dialog_values["name"]

        # Collect tracks with Spotify metadata
        spotify_track_uris = []
        skipped_tracks = []

        for track in tracks:
            # Look for Spotify platform info
            has_spotify = False
            for platform_info in track.platform_info:
                if platform_info.platform == "spotify" and platform_info.uri:
                    spotify_track_uris.append(platform_info.uri)
                    has_spotify = True
                    break

            if not has_spotify:
                skipped_tracks.append(f"{track.artist} - {track.title}")

        # If no tracks have Spotify info, show error
        if not spotify_track_uris:
            QMessageBox.critical(
                parent,
                "Export Error",
                "None of the tracks in this playlist have Spotify metadata. "
                "Cannot export to Spotify.",
            )
            return False

        try:
            # Create the playlist on Spotify
            spotify_client.export_tracks_to_playlist(playlist_name, spotify_track_uris)

            # Show success message with skipped tracks info
            if skipped_tracks:
                message = (
                    f"Playlist '{playlist_name}' exported to Spotify with "
                    f"{len(spotify_track_uris)} tracks.\n\n"
                    f"{len(skipped_tracks)} tracks were skipped because they don't "
                    f"have Spotify metadata:"
                )
                # Add up to 5 skipped tracks to the message
                for _, track_name in enumerate(skipped_tracks[:5]):
                    message += f"\n- {track_name}"

                if len(skipped_tracks) > 5:
                    message += f"\n- ... and {len(skipped_tracks) - 5} more"
            else:
                message = (
                    f"Playlist '{playlist_name}' exported to Spotify with all"
                    f" {len(spotify_track_uris)} tracks."
                )

            QMessageBox.information(parent, "Export Successful", message)

            return True

        except Exception as e:
            logger.exception(f"Error exporting playlist to Spotify: {e}")
            QMessageBox.critical(
                parent, "Export Error", f"Failed to export playlist to Spotify: {str(e)}"
            )
            return False

    def _export_to_rekordbox(
        self, playlist: Any, tracks: list[Any], parent: QWidget | None
    ) -> bool:
        """Export a playlist to Rekordbox.

        Args:
            playlist: The playlist to export
            tracks: The tracks in the playlist
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Initialize Rekordbox client
        rekordbox_client = self._init_rekordbox_client()

        # Check for running Rekordbox process but allow the user to continue if they want
        try:
            import psutil
            from pyrekordbox.config import get_rekordbox_pid

            pid = get_rekordbox_pid()
            if pid:
                # Check if the process is actually running or just suspended
                try:
                    process = psutil.Process(pid)
                    status = process.status()

                    # Only warn for active processes (running/sleeping), not suspended ones
                    if status in ["running", "sleeping"]:
                        response = QMessageBox.question(
                            parent,
                            "Rekordbox Running",
                            f"Rekordbox is currently running (status: {status}). This might cause "
                            "database conflicts.\n\n"
                            "Do you want to continue anyway?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        )

                        if response != QMessageBox.StandardButton.Yes:
                            return False  # User doesn't want to continue
                        else:
                            # User wants to continue - we'll use force=True in operations later
                            logger.warning(
                                "User chose to continue exporting playlist while "
                                "Rekordbox is running"
                            )
                    else:
                        # Process exists but is suspended or in another non-active state
                        logger.info(
                            f"Rekordbox process exists with PID {pid} but status is {status}, "
                            "proceeding anyway"
                        )
                except psutil.NoSuchProcess:
                    # Process doesn't exist anymore despite the PID being found
                    logger.info(
                        f"Rekordbox process with PID {pid} no longer exists, proceeding anyway"
                    )
            # If no PID or process is suspended, we can continue
        except Exception as e:
            logger.debug(f"Failed to check if Rekordbox is running: {e}")
            # Continue anyway

        if not rekordbox_client or not rekordbox_client.is_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Required",
                "You need to be authenticated with Rekordbox to export playlists. "
                "Please go to the Rekordbox section and authenticate first.",
            )
            return False

        # Get available folder list for the dialog
        try:
            available_folders = rekordbox_client.get_all_folders()
        except Exception as e:
            logger.warning(f"Error getting Rekordbox folders: {e}")
            available_folders = []

        # Show export dialog
        dialog = ImportExportPlaylistDialog(
            parent,
            mode="export",
            platform="rekordbox",
            default_name=playlist.name,
            enable_folder_selection=True,
            available_folders=available_folders,
        )

        if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
            return False

        dialog_values = dialog.get_values()
        playlist_name = dialog_values["name"]
        parent_folder_id = dialog_values.get("parent_folder_id")

        # Collect tracks with Rekordbox metadata or local files
        rekordbox_track_ids = []
        local_file_tracks = []
        skipped_tracks = []

        for track in tracks:
            # First check if track has Rekordbox platform info
            has_rekordbox = False
            for platform_info in track.platform_info:
                if platform_info.platform == "rekordbox":
                    rekordbox_track_ids.append(int(platform_info.platform_id))
                    has_rekordbox = True
                    break

            # If no Rekordbox info, check if it has a local file
            if not has_rekordbox and track.local_path and track.is_available_locally:
                local_file_tracks.append(track)
                continue

            # If neither, add to skipped tracks
            if not has_rekordbox:
                skipped_tracks.append(f"{track.artist} - {track.title}")

        # If no tracks have Rekordbox info or local files, show error
        if not rekordbox_track_ids and not local_file_tracks:
            QMessageBox.critical(
                parent,
                "Export Error",
                "None of the tracks in this playlist have Rekordbox metadata or local files. "
                "Cannot export to Rekordbox.",
            )
            return False

        # Track whether we should use force mode
        # (when Rekordbox is running but user wants to continue)
        # This is handled on a per-operation basis

        try:
            # First try without force, then with force if needed
            try:
                # Create the playlist on Rekordbox
                _ = rekordbox_client.export_tracks_to_playlist(
                    playlist_name, rekordbox_track_ids, parent_folder_id
                )
            except RuntimeError as re:
                error_msg = str(re)
                # Handle Rekordbox running error specifically
                if "Rekordbox is running" in error_msg:
                    # Ask user if they want to continue with force option
                    response = QMessageBox.question(
                        parent,
                        "Rekordbox Running",
                        "Rekordbox is currently running. This might cause database conflicts.\n\n"
                        "Do you want to continue anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if response == QMessageBox.StandardButton.Yes:
                        # User wants to continue - we need a manual approach since
                        # export_tracks_to_playlist doesn't have a force parameter
                        # Create the playlist with force mode

                        # Create the playlist with force=True
                        playlist_obj = rekordbox_client.create_playlist(
                            playlist_name, parent_folder_id, force=True
                        )

                        # Add each track individually with force=True
                        for track_id in rekordbox_track_ids:
                            rekordbox_client.add_track_to_playlist(
                                playlist_obj.id, track_id, force=True
                            )

                    else:
                        # User doesn't want to continue, stop the operation
                        raise RuntimeError(  # noqa: B904
                            "Operation cancelled by user because Rekordbox is running"
                        )
                else:
                    # Some other runtime error, just re-raise it
                    raise

            # For local files, we would need to add them to Rekordbox first
            # This is a complex process that would require more implementation
            # For now, let's just count them as skipped
            all_skipped = skipped_tracks + [
                f"{t.artist} - {t.title} (local file)" for t in local_file_tracks
            ]

            # Show success message with skipped tracks info
            if all_skipped:
                message = (
                    f"Playlist '{playlist_name}' exported to Rekordbox with "
                    f"{len(rekordbox_track_ids)} tracks.\n\n"
                    f"{len(all_skipped)} tracks were skipped:"
                )
                # Add up to 5 skipped tracks to the message
                for _, track_name in enumerate(all_skipped[:5]):
                    message += f"\n- {track_name}"

                if len(all_skipped) > 5:
                    message += f"\n- ... and {len(all_skipped) - 5} more"
            else:
                message = (
                    f"Playlist '{playlist_name}' exported to Rekordbox with all "
                    f"{len(rekordbox_track_ids)} tracks."
                )

            QMessageBox.information(parent, "Export Successful", message)

            return True

        except RuntimeError as e:
            error_msg = str(e)
            logger.exception(f"Runtime error exporting playlist to Rekordbox: {error_msg}")

            # Special handling for the "Rekordbox is running" error
            if "Rekordbox is running" in error_msg:
                # Don't show another error if user cancelled the operation
                if "cancelled by user" in error_msg:
                    logger.info("Export operation was cancelled by the user")
                else:
                    # Offer the user a choice to continue anyway
                    response = QMessageBox.question(
                        parent,
                        "Rekordbox Running",
                        "Rekordbox is currently running. This might cause database conflicts.\n\n"
                        "Do you want to continue anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if response == QMessageBox.StandardButton.Yes:
                        # Try again with force=True
                        try:
                            # Create new playlist with force=True
                            rekordbox_client.export_tracks_to_playlist(
                                playlist_name, rekordbox_track_ids, parent_folder_id, force=True
                            )

                            # For local files, we would need to add them to Rekordbox first
                            # This is a complex process that would require more implementation
                            # For now, let's just count them as skipped
                            all_skipped = skipped_tracks + [
                                f"{t.artist} - {t.title} (local file)" for t in local_file_tracks
                            ]

                            # Show success message with skipped tracks info
                            if all_skipped:
                                message = (
                                    f"Playlist '{playlist_name}' exported to Rekordbox with "
                                    f"{len(rekordbox_track_ids)} tracks.\n\n"
                                    f"{len(all_skipped)} tracks were skipped:"
                                )
                                # Add up to 5 skipped tracks to the message
                                for _, track_name in enumerate(all_skipped[:5]):
                                    message += f"\n- {track_name}"

                                if len(all_skipped) > 5:
                                    message += f"\n- ... and {len(all_skipped) - 5} more"
                            else:
                                message = (
                                    f"Playlist '{playlist_name}' exported to Rekordbox with all "
                                    f"{len(rekordbox_track_ids)} tracks."
                                )

                            QMessageBox.information(parent, "Export Successful", message)

                            return True
                        except Exception as force_error:
                            logger.exception(
                                f"Error exporting playlist with force=True: {force_error}"
                            )
                            QMessageBox.critical(
                                parent,
                                "Export Error",
                                f"Failed to export playlist to Rekordbox even with force option: "
                                f"{str(force_error)}",
                            )
                            return False
            else:
                QMessageBox.critical(
                    parent, "Export Error", f"Failed to export playlist to Rekordbox: {error_msg}"
                )
            return False

        except Exception as e:
            logger.exception(f"Error exporting playlist to Rekordbox: {e}")
            QMessageBox.critical(
                parent, "Export Error", f"Failed to export playlist to Rekordbox: {str(e)}"
            )
            return False
