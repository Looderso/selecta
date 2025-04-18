"""Local database playlist data provider implementation."""

import json
import os
from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QRadioButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.database import get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.local.local_playlist_item import LocalPlaylistItem
from selecta.ui.components.playlist.local.local_track_item import LocalTrackItem
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem
from selecta.ui.dialogs import ImportExportPlaylistDialog


class LocalPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for local playlists."""

    def __init__(self, cache_timeout: float = 300.0):
        """Initialize the local playlist data provider.

        Args:
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create a database session
        self.session = get_session()
        self.playlist_repo = PlaylistRepository(self.session)
        self.track_repo = TrackRepository(self.session)

        # Platform clients (will be initialized on-demand)
        self._spotify_client = None
        self._rekordbox_client = None
        self._discogs_client = None

        # Initialize the abstract provider with None as client (not needed for local)
        super().__init__(None, cache_timeout)

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch all local playlists from the database.

        Returns:
            List of playlist items
        """
        try:
            # Get all playlists from the database
            playlists = self.playlist_repo.get_all()

            # Convert to PlaylistItems
            playlist_items = []

            for playlist in playlists:
                # Get counts, checking for None values
                track_count = self.playlist_repo.get_track_count(playlist.id)

                # Check if this is an imported playlist - we don't use the platform name
                # in the UI yet, but it's available in the model if needed later

                # Create a folder or playlist item
                if playlist.is_folder:
                    # Skip folders for now - folders will be implemented in a future update
                    # This is a placeholder to handle folders in DB without showing them in UI
                    continue
                else:
                    # This is a regular playlist
                    playlist_items.append(
                        LocalPlaylistItem(
                            name=playlist.name,
                            item_id=playlist.id,
                            track_count=track_count,
                            is_folder_flag=False,
                            description=playlist.description,
                            source_platform=playlist.source_platform,
                            platform_id=playlist.platform_id,
                        )
                    )

            return playlist_items
        except Exception as e:
            logger.exception(f"Error fetching playlists: {e}")
            return []

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist with caching.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        try:
            # Get all tracks in the playlist
            tracks = self.playlist_repo.get_playlist_tracks(playlist_id)

            # Create TrackItems
            track_items = []

            for track in tracks:
                # This will always be a LibraryDatabase Track
                # Create a LocalTrackItem
                # Get all platforms this track is available on
                available_platforms = []
                # Store a map of platform -> uri for direct access
                platform_uris = {}

                for platform_info in track.platform_info:
                    available_platforms.append(platform_info.platform)
                    if platform_info.uri:  # Store URI if available (for Spotify)
                        platform_uris[platform_info.platform] = platform_info.uri

                # Check if the audio quality attribute exists
                has_audio_quality = True
                try:
                    quality = track.quality
                except (AttributeError, KeyError):
                    has_audio_quality = False
                    quality = None

                # Get genre names if available
                genre_str = ""
                if hasattr(track, "genres") and track.genres:
                    genre_str = ", ".join([g.name for g in track.genres])

                # Create platform info list for the track item
                platform_info_list = []
                for info in track.platform_info:
                    platform_info_list.append({"platform": info.platform, "id": info.platform_id})

                track_items.append(
                    LocalTrackItem(
                        track_id=track.id,
                        title=track.title,
                        artist=track.artist,
                        album=track.album or "",
                        genre=genre_str,
                        duration_ms=track.duration_ms,
                        local_path=track.local_path or "",
                        bpm=track.bpm or 0,
                        quality=quality if has_audio_quality else -1,
                        platform_info=platform_info_list,
                        has_image=bool(track.images),
                    )
                )

            return track_items

        except Exception as e:
            logger.exception(f"Error fetching playlist tracks: {e}")
            return []

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Local"

    def _ensure_authenticated(self) -> bool:
        """Override to ensure we always return True for local provider.

        The local provider doesn't need authentication for basic operations.

        Returns:
            Always True for local provider
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
        if not playlist_item or playlist_item.is_folder():
            return

        # Create context menu
        menu = QMenu(tree_view)

        # Figure out which platform options to show
        if playlist_item.is_imported() and playlist_item.source_platform:
            # This is an imported playlist - we can sync it
            sync_action = menu.addAction(f"Sync with {playlist_item.source_platform.capitalize()}")
            sync_action.triggered.connect(
                lambda: self.sync_playlist(playlist_item.item_id, tree_view)
            )

        # Add export actions for all platforms
        export_menu = menu.addMenu("Export to...")

        # Add export to Spotify action
        export_spotify_action = export_menu.addAction("Spotify")
        export_spotify_action.triggered.connect(
            lambda: self.export_playlist(playlist_item.item_id, "spotify", tree_view)
        )

        # Add export to Rekordbox action
        export_rekordbox_action = export_menu.addAction("Rekordbox")
        export_rekordbox_action.triggered.connect(
            lambda: self.export_playlist(playlist_item.item_id, "rekordbox", tree_view)
        )

        # Add export to Discogs action
        export_discogs_action = export_menu.addAction("Discogs")
        export_discogs_action.triggered.connect(
            lambda: self.export_playlist(playlist_item.item_id, "discogs", tree_view)
        )

        # Add delete action
        delete_action = menu.addAction("Delete Playlist")
        delete_action.triggered.connect(
            lambda: self._delete_playlist(playlist_item.item_id, tree_view)
        )

        # Show the menu at the cursor position
        menu.exec(tree_view.viewport().mapToGlobal(position))

    def _delete_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> None:
        """Delete a playlist.

        Args:
            playlist_id: ID of the playlist to delete
            parent: Parent widget for dialogs
        """
        # Get the playlist from the database
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            QMessageBox.critical(
                parent, "Delete Error", f"Playlist with ID {playlist_id} not found."
            )
            return

        # Ask for confirmation
        response = QMessageBox.question(
            parent,
            "Confirm Delete",
            f"Are you sure you want to delete the playlist '{playlist.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Delete the playlist
        try:
            self.playlist_repo.delete(playlist_id)
            QMessageBox.information(
                parent, "Delete Successful", f"Playlist '{playlist.name}' was deleted."
            )
            self.refresh()  # Refresh the UI
        except Exception as e:
            logger.exception(f"Error deleting playlist: {e}")
            QMessageBox.critical(parent, "Delete Error", f"Failed to delete playlist: {str(e)}")

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

    def _init_discogs_client(self) -> DiscogsClient | None:
        """Initialize the Discogs client if not already done.

        Returns:
            DiscogsClient if successfully initialized, None otherwise
        """
        if self._discogs_client is not None:
            return self._discogs_client

        try:
            settings_repo = SettingsRepository()
            client = PlatformFactory.create("discogs", settings_repo)
            if isinstance(client, DiscogsClient):
                self._discogs_client = client
                return self._discogs_client
            return None
        except Exception as e:
            logger.exception(f"Failed to initialize Discogs client: {e}")
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
        elif playlist.source_platform == "discogs":
            client = self._init_discogs_client()

            # For Discogs, show a dialog to select collection or wantlist since the platform_id
            # in the database doesn't necessarily differentiate between them
            dialog = QDialog(parent)
            dialog.setWindowTitle("Sync with Discogs")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout(dialog)

            # Description
            description_label = QLabel(
                "Choose whether to sync with your Discogs collection or wantlist."
            )
            description_label.setWordWrap(True)
            layout.addWidget(description_label)

            # Radio buttons for collection or wantlist
            collection_radio = QRadioButton("Sync with Collection")
            wantlist_radio = QRadioButton("Sync with Wantlist")

            # Try to determine which was used previously based on platform_id
            if playlist.platform_id == "wantlist":
                wantlist_radio.setChecked(True)
            else:
                collection_radio.setChecked(True)  # Default or if platform_id is "collection"

            layout.addWidget(collection_radio)
            layout.addWidget(wantlist_radio)

            # Button box
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

            # Update the platform_id based on user selection
            target = "collection" if collection_radio.isChecked() else "wantlist"

            # Update playlist if the target changed
            if playlist.platform_id != target:
                self.playlist_repo.update(playlist.id, {"platform_id": target})
                playlist.platform_id = target
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
            # Create a PlatformSyncManager to handle the sync
            from selecta.core.platform.sync_manager import PlatformSyncManager

            sync_manager = PlatformSyncManager(client)

            # For Rekordbox, determine if we need to use force option
            force = False
            if playlist.source_platform == "rekordbox":
                try:
                    import psutil
                    from pyrekordbox.config import get_rekordbox_pid

                    pid = get_rekordbox_pid()
                    if pid and psutil.Process(pid).status() in ["running", "sleeping"]:
                        force = True
                except:
                    pass

            # For Discogs, we need to use the target (collection/wantlist) from the platform_id
            extra_args = {}
            if playlist.source_platform == "rekordbox" and force:
                extra_args["force"] = force

            # Perform the sync using the sync manager
            tracks_added, tracks_exported = sync_manager.sync_playlist(playlist.id)

            # Show success message with stats
            message = f"Playlist '{playlist.name}' synced successfully.\n\n"
            if tracks_added > 0:
                platform_name = playlist.source_platform.capitalize()
                message += f"- {tracks_added} new tracks were imported from {platform_name}.\n"
            if tracks_exported > 0:
                platform_name = playlist.source_platform.capitalize()
                message += f"- {tracks_exported} tracks were exported to {platform_name}.\n"
            if tracks_added == 0 and tracks_exported == 0:
                message += "The playlist is already in sync; no changes were made."

            QMessageBox.information(parent, "Sync Successful", message)

            # Refresh the UI
            self.notify_refresh_needed()

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
        elif target_platform == "discogs":
            return self._export_to_discogs(playlist, tracks, parent)
        else:
            QMessageBox.critical(parent, "Export Error", f"Unsupported platform: {target_platform}")
            return False

    def _export_to_spotify(self, playlist: Any, tracks: list[Any], parent: QWidget | None) -> bool:
        """Export a playlist to Spotify using the PlatformSyncManager.

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

        # Create PlatformSyncManager for Spotify
        from selecta.core.platform.sync_manager import PlatformSyncManager

        sync_manager = PlatformSyncManager(spotify_client)

        # Check which tracks have Spotify metadata
        spotify_track_count = 0
        skipped_tracks = []

        for track in tracks:
            has_spotify = False
            for platform_info in track.platform_info:
                if platform_info.platform == "spotify" and platform_info.platform_id:
                    spotify_track_count += 1
                    has_spotify = True
                    break

            if not has_spotify:
                skipped_tracks.append(f"{track.artist} - {track.title}")

        # If no tracks have Spotify info, show error
        if spotify_track_count == 0:
            QMessageBox.critical(
                parent,
                "Export Error",
                "None of the tracks in this playlist have Spotify metadata. "
                "Cannot export to Spotify.",
            )
            return False

        # Warn about skipped tracks if any
        if skipped_tracks:
            warning_message = (
                f"{len(skipped_tracks)} of {len(tracks)} tracks will be skipped because they don't "
                "have Spotify metadata.\n\n"
                "Do you want to continue with the export?"
            )
            response = QMessageBox.question(
                parent,
                "Some Tracks Will Be Skipped",
                warning_message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return False

        try:
            # Update the playlist name if it was changed in the dialog
            if playlist_name != playlist.name:
                self.playlist_repo.update(playlist.id, {"name": playlist_name})

            # Export the playlist using the sync manager
            platform_playlist_id = sync_manager.export_playlist(
                local_playlist_id=playlist.id,
            )

            # Update the local playlist with the platform connection
            if platform_playlist_id and not playlist.platform_id:
                self.playlist_repo.update(
                    playlist.id,
                    {
                        "source_platform": "spotify",
                        "platform_id": platform_playlist_id,
                        "is_local": False,
                    },
                )

            # Show success message with skipped tracks info
            if skipped_tracks:
                message = (
                    f"Playlist '{playlist_name}' exported to Spotify with "
                    f"{spotify_track_count} tracks.\n\n"
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
                    f"Playlist '{playlist_name}' exported to Spotify with all "
                    f"{spotify_track_count} tracks."
                )

            QMessageBox.information(parent, "Export Successful", message)

            # Refresh the UI
            self.notify_refresh_needed()
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
        """Export a playlist to Rekordbox using the PlatformSyncManager.

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
        force = False  # Default setting for operations
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
                            # User wants to continue - we'll use force=True in operations
                            force = True
                            logger.warning(
                                "User chose to continue exporting playlist while "
                                "Rekordbox is running"
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process not running or can't access it, so continue
                    pass
        except (ImportError, Exception) as e:
            # Could not check if Rekordbox is running, just continue
            logger.warning(f"Failed to check if Rekordbox is running: {e}")

        if not rekordbox_client or not rekordbox_client.is_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Required",
                "You need to be connected to Rekordbox to export playlists. "
                "Please go to the Rekordbox section and connect first.",
            )
            return False

        # Show export dialog
        dialog = ImportExportPlaylistDialog(
            parent,
            mode="export",
            platform="rekordbox",
            default_name=playlist.name,
            enable_folder_selection=True,
            available_folders=rekordbox_client.get_all_folders(),
        )

        if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
            return False

        dialog_values = dialog.get_values()
        playlist_name = dialog_values["name"]
        parent_folder_id = dialog_values.get("parent_folder_id")

        # Create PlatformSyncManager for Rekordbox
        from selecta.core.platform.sync_manager import PlatformSyncManager

        sync_manager = PlatformSyncManager(rekordbox_client)

        # Check which tracks have Rekordbox metadata or can be added
        rekordbox_track_count = 0
        local_files_to_add = []
        skipped_tracks = []

        for track in tracks:
            # First check if it has Rekordbox metadata
            has_rekordbox = False
            for platform_info in track.platform_info:
                if platform_info.platform == "rekordbox" and platform_info.platform_id:
                    try:
                        # Validate ID format
                        int(platform_info.platform_id)  # Just to check if it's a valid integer
                        rekordbox_track_count += 1
                        has_rekordbox = True
                        break
                    except (ValueError, TypeError):
                        track_id = platform_info.platform_id
                        logger.warning(f"Invalid Rekordbox ID for track {track.id}: {track_id}")

            # If no Rekordbox metadata, check if it's a local file that can be added
            if not has_rekordbox and track.is_available_locally and track.local_path:
                if os.path.exists(track.local_path):
                    local_files_to_add.append(track)
                else:
                    skipped_tracks.append(f"{track.artist} - {track.title} (missing file)")
            elif not has_rekordbox:
                skipped_tracks.append(f"{track.artist} - {track.title}")

        # If no tracks can be exported, show error
        if rekordbox_track_count == 0 and not local_files_to_add:
            QMessageBox.critical(
                parent,
                "Export Error",
                "None of the tracks in this playlist have Rekordbox metadata "
                "or local audio files. Cannot export to Rekordbox.",
            )
            return False

        # Warn about tracks that will be skipped
        if skipped_tracks and rekordbox_track_count > 0:
            warning_message = (
                f"{len(skipped_tracks)} of {len(tracks)} tracks will be skipped because they "
                "don't have Rekordbox metadata or local audio files.\n\n"
                "Do you want to continue with the export?"
            )
            response = QMessageBox.question(
                parent,
                "Some Tracks Will Be Skipped",
                warning_message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return False

        # Add local files to Rekordbox if needed
        if local_files_to_add:
            response = QMessageBox.question(
                parent,
                "Add Local Files to Rekordbox",
                f"Found {len(local_files_to_add)} local audio files that are not in your "
                "Rekordbox collection. Do you want to add them first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if response == QMessageBox.StandardButton.Yes:
                # Add each local file to Rekordbox
                track_repo = TrackRepository()
                progress_dialog = QProgressDialog(
                    "Adding files to Rekordbox...", "Cancel", 0, len(local_files_to_add), parent
                )
                progress_dialog.setWindowTitle("Adding Files")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setValue(0)
                progress_dialog.show()

                for i, track in enumerate(local_files_to_add):
                    # Check if user cancelled
                    if progress_dialog.wasCanceled():
                        break

                    progress_dialog.setValue(i)
                    progress_dialog.setLabelText(f"Adding: {os.path.basename(track.local_path)}")
                    QApplication.processEvents()  # Allow UI to update

                    try:
                        # Import the track to Rekordbox
                        rb_track = rekordbox_client.import_track(track.local_path, force=force)
                        if rb_track and rb_track.id:
                            # Save the Rekordbox ID to our database
                            platform_data = json.dumps(
                                {
                                    "id": rb_track.id,
                                    "title": rb_track.title,
                                    "artist": rb_track.artist_name,
                                    "bpm": rb_track.bpm,
                                }
                            )

                            track_repo.add_platform_info(
                                track_id=track.id,
                                platform="rekordbox",
                                platform_id=str(rb_track.id),
                                uri=None,
                                metadata=platform_data,
                            )

                            rekordbox_track_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to add file {track.local_path} to Rekordbox: {e}")

                # Close progress dialog
                progress_dialog.setValue(len(local_files_to_add))

        # Update playlist name if changed
        if playlist_name != playlist.name:
            self.playlist_repo.update(playlist.id, {"name": playlist_name})

        try:
            # Export the playlist using the sync manager
            platform_playlist_id = sync_manager.export_playlist(
                local_playlist_id=playlist.id,
                parent_folder_id=parent_folder_id,
                force=force,
            )

            # Update the local playlist with the platform connection
            if platform_playlist_id and not playlist.platform_id:
                self.playlist_repo.update(
                    playlist.id,
                    {
                        "source_platform": "rekordbox",
                        "platform_id": platform_playlist_id,
                        "is_local": False,
                    },
                )

            # Show success message
            message = (
                f"Playlist '{playlist_name}' was successfully exported to Rekordbox "
                f"with {rekordbox_track_count} tracks."
            )

            if skipped_tracks:
                message += f"\n\n{len(skipped_tracks)} tracks were skipped because they don't "
                message += "have Rekordbox metadata or local audio files."

            QMessageBox.information(parent, "Export Successful", message)

            # Refresh the UI
            self.notify_refresh_needed()
            return True

        except Exception as e:
            logger.exception(f"Error exporting playlist to Rekordbox: {e}")
            QMessageBox.critical(
                parent, "Export Error", f"Failed to export playlist to Rekordbox: {str(e)}"
            )
            return False

    def _export_to_discogs(self, playlist: Any, tracks: list[Any], parent: QWidget | None) -> bool:
        """Export a playlist to Discogs (collection or wantlist).

        Args:
            playlist: The playlist to export
            tracks: The tracks in the playlist
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Initialize Discogs client
        discogs_client = self._init_discogs_client()
        if not discogs_client or not discogs_client.is_authenticated():
            QMessageBox.warning(
                parent,
                "Authentication Required",
                "You need to be authenticated with Discogs to export playlists. "
                "Please go to the Discogs section and authenticate first.",
            )
            return False

        # Show export dialog
        dialog = QDialog(parent)
        dialog.setWindowTitle("Export to Discogs")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Description
        description_label = QLabel(
            "Choose whether to add these records to your Discogs collection or wantlist."
        )
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Radio buttons for collection or wantlist
        collection_radio = QRadioButton("Add to Collection")
        wantlist_radio = QRadioButton("Add to Wantlist")
        collection_radio.setChecked(True)  # Default to collection

        layout.addWidget(collection_radio)
        layout.addWidget(wantlist_radio)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        # Determine target: collection or wantlist
        target = "collection" if collection_radio.isChecked() else "wantlist"

        # Create PlatformSyncManager for Discogs
        from selecta.core.platform.sync_manager import PlatformSyncManager

        sync_manager = PlatformSyncManager(discogs_client)

        # Check which tracks have Discogs metadata
        discogs_track_count = 0
        skipped_tracks = []

        for track in tracks:
            has_discogs = False
            for platform_info in track.platform_info:
                if platform_info.platform == "discogs" and platform_info.platform_id:
                    discogs_track_count += 1
                    has_discogs = True
                    break

            if not has_discogs:
                skipped_tracks.append(f"{track.artist} - {track.title}")

        # If no tracks have Discogs info, show error
        if discogs_track_count == 0:
            QMessageBox.critical(
                parent,
                "Export Error",
                "None of the tracks in this playlist have Discogs metadata. "
                "Cannot export to Discogs.",
            )
            return False

        # Warn about skipped tracks if any
        if skipped_tracks:
            warning_message = (
                f"{len(skipped_tracks)} of {len(tracks)} tracks will be skipped because they don't "
                "have Discogs metadata.\n\n"
                "Do you want to continue with the export?"
            )
            response = QMessageBox.question(
                parent,
                "Some Tracks Will Be Skipped",
                warning_message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return False

        try:
            # Export the playlist using the sync manager with the target as existing_playlist_id
            sync_manager.export_playlist(
                local_playlist_id=playlist.id,
                platform_playlist_id=target,
            )

            # Show success message with skipped tracks info
            if skipped_tracks:
                message = (
                    f"{discogs_track_count} records were added to your Discogs {target}.\n\n"
                    f"{len(skipped_tracks)} tracks were skipped because they don't "
                    f"have Discogs metadata:"
                )
                # Add up to 5 skipped tracks to the message
                for _, track_name in enumerate(skipped_tracks[:5]):
                    message += f"\n- {track_name}"

                if len(skipped_tracks) > 5:
                    message += f"\n- ... and {len(skipped_tracks) - 5} more"
            else:
                message = (
                    f"All {discogs_track_count} records were successfully added to your "
                    f"Discogs {target}."
                )

            QMessageBox.information(parent, "Export Successful", message)
            return True

        except Exception as e:
            logger.exception(f"Error exporting playlist to Discogs: {e}")
            QMessageBox.critical(
                parent, "Export Error", f"Failed to export to Discogs {target}: {str(e)}"
            )
            return False
