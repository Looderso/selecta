# src/selecta/ui/components/playlist/abstract_playlist_data_provider.py
"""Abstract implementation of PlaylistDataProvider with common functionality."""

from abc import abstractmethod
from typing import Any

from loguru import logger
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.core.utils.cache_manager import CacheManager
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class AbstractPlaylistDataProvider(PlaylistDataProvider):
    """Abstract implementation of PlaylistDataProvider with caching and common functionality."""

    # Signal to notify when local playlists have changed
    local_playlists_changed = pyqtSignal()

    def __init__(self, client: AbstractPlatform | None = None, cache_timeout: float = 300.0):
        """Initialize the abstract playlist data provider.

        Args:
            client: Platform client instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        super().__init__()
        self.client = client
        self.cache = CacheManager(default_timeout=cache_timeout)

        # Common cache keys
        self._playlists_cache_key = f"{self.get_platform_name().lower()}_playlists"

    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        Returns:
            True if connected, False otherwise
        """
        return self._ensure_authenticated()

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists with caching.

        Returns:
            List of playlist items
        """
        # Try to get from cache first
        if self.cache.has_valid(self._playlists_cache_key):
            return self.cache.get(self._playlists_cache_key, [])

        # Check authentication
        if not self._ensure_authenticated():
            logger.warning(f"{self.get_platform_name()} client is not authenticated")
            return []

        try:
            # Get fresh data
            playlists = self._fetch_playlists()

            # Cache the result
            self.cache.set(self._playlists_cache_key, playlists)

            return playlists
        except Exception as e:
            logger.exception(f"Error getting {self.get_platform_name()} playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist with caching.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        # Generate cache key for this playlist's tracks
        cache_key = f"{self.get_platform_name().lower()}_tracks_{playlist_id}"

        # Try to get from cache first - show cached data immediately if available
        # to prevent UI locking while data is being fetched
        if self.cache.has_valid(cache_key):
            cached_data = self.cache.get(cache_key, [])

            # Only trigger background refresh if we have data to show
            # This ensures we don't have empty loading states while refreshing
            if cached_data:
                # Trigger a background refresh after returning cached data
                # This ensures our cache stays fresh without blocking the UI
                self._trigger_background_refresh(playlist_id, cache_key)
                return cached_data
            # If cache is empty, continue to fetch new data

        # Check authentication
        if not self._ensure_authenticated():
            logger.warning(f"{self.get_platform_name()} client is not authenticated")
            return []

        try:
            # Get fresh data
            tracks = self._fetch_playlist_tracks(playlist_id)

            # Cache the result
            self.cache.set(cache_key, tracks)

            return tracks
        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def refresh(self) -> None:
        """Refresh all cached data and notify listeners."""
        # Clear the cache
        self.cache.clear()

        # Notify listeners
        self.notify_refresh_needed()

    def refresh_playlist(self, playlist_id: Any) -> None:
        """Refresh a specific playlist's tracks.

        Args:
            playlist_id: ID of the playlist to refresh
        """
        # Invalidate just this playlist's cache
        cache_key = f"{self.get_platform_name().lower()}_tracks_{playlist_id}"
        self.cache.invalidate(cache_key)

        # Notify listeners
        self.notify_refresh_needed()

    def _trigger_background_refresh(self, playlist_id: Any, cache_key: str) -> None:
        """Trigger a background refresh of a playlist's tracks.

        This ensures the cache stays fresh without blocking the UI,
        addressing the issue of playlists appearing to be stuck while loading.

        Args:
            playlist_id: The playlist ID
            cache_key: Cache key for the playlist's tracks
        """
        # Skip for non-authenticated clients (will be handled in main method)
        if not self._ensure_authenticated():
            return

        # Use ThreadManager to run the refresh in background
        from selecta.core.utils.worker import ThreadManager

        def background_refresh_task() -> None:
            try:
                # Fetch fresh data directly from source
                fresh_tracks = self._fetch_playlist_tracks(playlist_id)

                # Update cache with fresh data
                self.cache.set(cache_key, fresh_tracks)

                platform = self.get_platform_name()
                logger.debug(f"Background refresh completed for {platform} playlist {playlist_id}")
            except Exception as e:
                # Just log errors, don't interrupt the UI
                logger.error(f"Error in background refresh for {playlist_id}: {e}")

        # Run the task in background with low priority
        thread_manager = ThreadManager()
        thread_manager.run_task(background_refresh_task)

    def sync_playlist(self, local_playlist_id: str, parent: QWidget | None = None) -> bool:
        """Sync a library playlist with its platform source.

        This method implements the enhanced sync functionality with preview dialog.

        Args:
            local_playlist_id: ID of the library playlist to sync
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    f"Not connected to {self.get_platform_name()}. Please connect first.",
                )
            return False

        try:
            # Create a sync manager
            if self.client is None:
                raise ValueError(f"No {self.get_platform_name()} client available")
            sync_manager = PlatformSyncManager(self.client)

            # Get changes preview
            try:
                preview = sync_manager.preview_sync(int(local_playlist_id))
            except Exception as e:
                logger.exception(f"Error getting sync preview: {e}")
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Sync Preview Failed",
                        f"Failed to get sync preview: {str(e)}",
                    )
                return False

            # Check if there are changes to sync
            changes_count = (
                len(preview.platform_additions)
                + len(preview.platform_removals)
                + len(preview.library_additions)
                + len(preview.library_removals)
            )

            if changes_count == 0:
                # No changes to sync
                if parent:
                    QMessageBox.information(
                        parent,
                        "Playlists in Sync",
                        f"The library playlist is already in sync with {self.get_platform_name()}.",
                    )
                return True

            # Show sync preview dialog
            from selecta.ui.dialogs.sync_preview_dialog import SyncPreviewDialog

            sync_dialog = SyncPreviewDialog(parent, sync_preview=preview)

            # If dialog is accepted, apply the selected changes
            if sync_dialog.exec():
                # Get selected changes
                selected_changes = sync_dialog.get_selected_changes()

                # Apply changes
                try:
                    # Show progress in dialog
                    sync_dialog.show_progress(0, 100)

                    # Apply changes
                    result = sync_manager.apply_sync_changes(
                        int(local_playlist_id), selected_changes
                    )

                    # Update dialog with result
                    sync_dialog.show_progress(100, 100)
                    sync_dialog.update_with_result(result)

                    # Show success message
                    if parent:
                        total_changes = result.total_changes_applied
                        if total_changes > 0:
                            QMessageBox.information(
                                parent,
                                "Sync Successful",
                                f"Successfully applied {total_changes} changes.",
                            )
                        else:
                            QMessageBox.information(
                                parent,
                                "No Changes Applied",
                                "No changes were applied during sync.",
                            )

                    # Signal that local playlists have changed if any changes were applied
                    if result.total_changes_applied > 0:
                        self.local_playlists_changed.emit()

                    return result.success

                except Exception as e:
                    logger.exception(f"Error applying sync changes: {e}")
                    if parent:
                        QMessageBox.critical(
                            parent,
                            "Sync Failed",
                            f"Failed to apply sync changes: {str(e)}",
                        )
                    return False

            return False  # Dialog was cancelled

        except Exception as e:
            logger.exception(f"Error syncing {self.get_platform_name()} playlist: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Sync Failed",
                    f"Failed to sync playlist: {str(e)}",
                )
            return False

    def show_playlist_context_menu(
        self, tree_view: QTreeView, position: Any, parent: QWidget | None = None
    ) -> None:
        """Show a context menu for a platform playlist.

        This provides a default implementation that can be overridden by platform-specific
        providers.

        Args:
            tree_view: The tree view containing the playlist
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        # Debug logging to verify this method is called
        logger.debug(
            f"AbstractPlaylistDataProvider.show_playlist_context_menu "
            f"called for {self.get_platform_name()}"
        )

        index = tree_view.indexAt(position)
        if not index.isValid():
            logger.debug("Right-click on empty space, showing minimal context menu")
            # Create context menu for empty space
            menu = QMenu(tree_view)

            # Add refresh option
            if menu is not None:
                refresh_action = menu.addAction("Refresh All")
                if refresh_action is not None:
                    refresh_action.triggered.connect(self.refresh)

                # Show the menu
                if tree_view is not None and tree_view.viewport() is not None:
                    action = menu.exec(tree_view.viewport().mapToGlobal(position))
            return

        # Get the playlist item from the internal pointer
        item = index.internalPointer()
        if not item:
            logger.debug(f"Invalid item: {item}")
            return

        # Check if the item has an id attribute (could be 'id' or 'item_id')
        has_id = hasattr(item, "id") or hasattr(item, "item_id")
        if not has_id:
            logger.debug(f"Item has no id or item_id attribute: {item}")
            return

        # Get the ID from either attribute
        item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
        logger.debug(
            f"Found playlist item: id={item_id}, "
            f"name={item.name if hasattr(item, 'name') else 'unknown'}"
        )

        # Create the context menu
        menu = QMenu(tree_view)

        # Current platform
        platform_name = self.get_platform_name().lower()

        # Check if this playlist is already imported (linked to the Library)
        is_imported = hasattr(item, "is_imported") and item.is_imported

        # Platform-specific context menu options

        # Add context menu options based on import status
        if menu is not None:
            if is_imported:
                # For already imported playlists, show sync option
                sync_action = menu.addAction("Sync with Library")

                # Add option to import additional tracks to existing playlist
                add_to_playlist_action = menu.addAction("Add Tracks to Existing Playlist")

                # Add refresh option
                menu.addSeparator()
                refresh_action = menu.addAction("Refresh")
            else:
                # For non-imported playlists, show import options
                import_action = menu.addAction("Import to Library")
                import_to_existing_action = menu.addAction("Import to Existing Playlist")

                # Add refresh option
                menu.addSeparator()
                refresh_action = menu.addAction("Refresh")

        # Show the menu and handle the selected action
        if menu is not None and tree_view is not None and tree_view.viewport() is not None:
            action = menu.exec(tree_view.viewport().mapToGlobal(position))
        else:
            action = None
        if not action:
            return

        # No common actions to handle at this level

        # Handle action based on whether playlist is imported
        if is_imported:
            if action == sync_action:
                # For sync, we need to get the Library playlist ID linked to this platform playlist
                try:
                    from selecta.core.data.repositories.playlist_repository import (
                        PlaylistRepository,
                    )

                    playlist_repo = PlaylistRepository()

                    # Get the ID from either attribute
                    item_id = getattr(item, "id", None) or getattr(item, "item_id", None)

                    # Find the linked Library playlist
                    library_playlist = playlist_repo.get_by_platform_id(platform_name, str(item_id))

                    if library_playlist:
                        # Sync the found Library playlist with this platform
                        self.sync_playlist(str(library_playlist.id), parent)
                    else:
                        # If no linked playlist found, fall back to importing
                        QMessageBox.information(
                            parent,
                            "Sync Not Possible",
                            f"Cannot find a Library playlist linked to this "
                            f"{platform_name.capitalize()} playlist. "
                            "Will import as a new playlist instead.",
                        )
                        self.import_playlist(item_id, parent)
                except Exception as e:
                    logger.exception(f"Error during sync action: {e}")
                    QMessageBox.critical(parent, "Sync Error", f"An error occurred: {str(e)}")

            elif action == add_to_playlist_action:
                # Get the ID from either attribute
                item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
                self.import_to_existing_playlist(item_id, parent)
            elif action == refresh_action:
                # Get the ID from either attribute
                item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
                self.refresh_playlist(item_id)
        else:
            # Handle non-imported playlist actions
            if action == import_action:
                # Get the ID from either attribute
                item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
                self.import_playlist(item_id, parent)
            elif action == import_to_existing_action:
                # Get the ID from either attribute
                item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
                self.import_to_existing_playlist(item_id, parent)
            elif action == refresh_action:
                # Get the ID from either attribute
                item_id = getattr(item, "id", None) or getattr(item, "item_id", None)
                self.refresh_playlist(item_id)

    def show_track_context_menu(
        self, table_view: Any, position: Any, parent: QWidget | None = None
    ) -> None:
        """Show a context menu for a platform track.

        This provides a default implementation that can be overridden by platform-specific
        providers.

        Args:
            table_view: The table view containing the track
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        index = table_view.indexAt(position)
        if not index.isValid():
            return

        # Get the current selected tracks
        selected_indexes = table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Get the first selected track (for single-track operations)
        first_row = selected_indexes[0].row()
        model = table_view.model()
        first_track = model.get_track(first_row)

        if not first_track:
            return

        # Create multi-selection list if needed
        selected_tracks = []
        for index in selected_indexes:
            row = index.row()
            track = model.get_track(row)
            if track:
                selected_tracks.append(track)

        # Create the context menu
        menu = QMenu(table_view)

        # Only allow these actions for a single track
        is_single_track = len(selected_tracks) == 1
        current_platform = self.get_platform_name().lower()

        if menu is not None:
            if is_single_track:
                play_action = menu.addAction("Play")
                menu.addSeparator()
                add_to_library_action = menu.addAction("Add to Library")

                # Add search on other platforms submenu
                search_menu = menu.addMenu("Search On")

                # Add platform-specific search options (excluding current platform)
                if current_platform != "spotify" and search_menu is not None:
                    search_spotify_action = search_menu.addAction("Spotify")
                else:
                    search_spotify_action = None

                if current_platform != "discogs" and search_menu is not None:
                    search_discogs_action = search_menu.addAction("Discogs")
                else:
                    search_discogs_action = None

                if current_platform != "youtube" and search_menu is not None:
                    search_youtube_action = search_menu.addAction("YouTube")
                else:
                    search_youtube_action = None

                if current_platform != "rekordbox" and search_menu is not None:
                    search_rekordbox_action = search_menu.addAction("Rekordbox")
                    if search_rekordbox_action is not None:
                        search_rekordbox_action.setEnabled(False)  # Not implemented yet
                else:
                    search_rekordbox_action = None
            else:
                # Multi-track actions
                tracks_count = len(selected_tracks)
                add_to_library_action = menu.addAction(f"Add {tracks_count} Tracks to Library")
                play_action = None
                search_spotify_action = None
                search_discogs_action = None
                search_youtube_action = None
                search_rekordbox_action = None
        else:
            # Menu could not be created
            add_to_library_action = None
            play_action = None
            search_spotify_action = None
            search_discogs_action = None
            search_youtube_action = None
            search_rekordbox_action = None

        # Show the menu and handle the selected action
        action = None
        if menu is not None and table_view is not None and table_view.viewport() is not None:
            action = menu.exec(table_view.viewport().mapToGlobal(position))

        if not action:
            return

        # Handle single-track actions
        if is_single_track and action == play_action:
            # Get the main window
            main_window = table_view.window()

            # Emit play track signal if available
            if hasattr(main_window, "play_track"):
                main_window.play_track(first_track)

        # Handle search actions
        elif is_single_track and search_spotify_action and action == search_spotify_action:
            main_window = table_view.window()
            search_query = f"{first_track.artist} {first_track.title}"
            if hasattr(main_window, "show_spotify_search"):
                main_window.show_spotify_search(search_query)

        elif is_single_track and search_discogs_action and action == search_discogs_action:
            main_window = table_view.window()
            search_query = f"{first_track.artist} {first_track.title}"
            if hasattr(main_window, "show_discogs_search"):
                main_window.show_discogs_search(search_query)

        elif is_single_track and search_youtube_action and action == search_youtube_action:
            main_window = table_view.window()
            search_query = f"{first_track.artist} {first_track.title}"
            if hasattr(main_window, "show_youtube_search"):
                main_window.show_youtube_search(search_query)

        # Handle adding to library
        elif action == add_to_library_action:
            self._add_tracks_to_library(selected_tracks, parent)

    def _add_tracks_to_library(self, tracks: list[Any], parent: QWidget | None = None) -> bool:
        """Add platform tracks to the library.

        Args:
            tracks: List of platform track items to add to the library
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not tracks:
            return False

        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    f"Not connected to {self.get_platform_name()}. Please connect first.",
                )
            return False

        try:
            # Show progress message
            if parent:
                QMessageBox.information(
                    parent,
                    "Adding Tracks",
                    f"Adding {len(tracks)} track(s) to library...",
                )

            # Create a sync manager
            if self.client is None:
                raise ValueError(f"No {self.get_platform_name()} client available")
            sync_manager = PlatformSyncManager(self.client)

            # Track success counter
            successful_imports = 0

            # Import each track
            for track in tracks:
                try:
                    # Import the track
                    imported_track = sync_manager.link_manager.import_track(track)
                    if imported_track:
                        successful_imports += 1
                except Exception as e:
                    track_id = getattr(track, "id", "unknown")
                    logger.warning(f"Failed to import track {track_id}: {e}")

            # Show result message
            if parent:
                if successful_imports > 0:
                    QMessageBox.information(
                        parent,
                        "Import Successful",
                        f"Successfully added {successful_imports} of {len(tracks)} track(s) to "
                        "library.",
                    )
                else:
                    QMessageBox.warning(
                        parent,
                        "Import Failed",
                        "Failed to add any tracks to library.",
                    )

            # Signal that local tracks have changed
            if successful_imports > 0:
                self.local_playlists_changed.emit()

            return successful_imports > 0

        except Exception as e:
            logger.exception(f"Error adding {self.get_platform_name()} tracks to library: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Import Failed",
                    f"Failed to add tracks to library: {str(e)}",
                )
            return False

    def import_to_existing_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import tracks from a platform playlist to an existing library playlist.

        Args:
            playlist_id: ID of the platform playlist to import
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Not Connected",
                    f"Not connected to {self.get_platform_name()}. Please connect first.",
                )
            return False
        try:
            # First, get all library playlists
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            playlist_repo = PlaylistRepository()
            library_playlists = playlist_repo.get_all()

            # Filter out folders
            regular_playlists = [(p.id, p.name) for p in library_playlists if not p.is_folder]

            if not regular_playlists:
                QMessageBox.warning(
                    parent,
                    "No Playlists Found",
                    "There are no playlists in your library. Please create a playlist first.",
                )
                return False

            # Create a dialog to select the target playlist
            from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

            dialog = QDialog(parent)
            dialog.setWindowTitle("Select Target Playlist")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout(dialog)

            # Description
            label = QLabel("Select the playlist to add the tracks to:")
            layout.addWidget(label)

            # Combo box for playlist selection
            combo = QComboBox()
            for _, name in regular_playlists:
                combo.addItem(name)
            layout.addWidget(combo)

            # Button box
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            if not dialog.exec():
                return False

            # Get the selected playlist
            selected_index = combo.currentIndex()
            if selected_index < 0:
                return False

            target_playlist_id = regular_playlists[selected_index][0]

            # Show a progress dialog
            if parent:
                QMessageBox.information(
                    parent,
                    "Importing Tracks",
                    f"Importing {self.get_platform_name()} playlist tracks. "
                    "This may take a moment...",
                )

            # Create a sync manager
            if self.client is None:
                raise ValueError(f"No {self.get_platform_name()} client available")
            sync_manager = PlatformSyncManager(self.client)

            # Import the playlist to the existing target playlist
            platform_playlist_id = str(playlist_id) if playlist_id is not None else ""
            target_playlist, imported_tracks = sync_manager.import_playlist(
                platform_playlist_id=platform_playlist_id, target_playlist_id=target_playlist_id
            )

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Import Successful",
                    f"Imported {len(imported_tracks)} tracks to '{target_playlist.name}'.",
                )

            # Signal that local playlists have changed
            self.local_playlists_changed.emit()
            return True

        except Exception as e:
            logger.exception(
                f"Error importing {self.get_platform_name()} playlist to existing playlist: {e}"
            )
            if parent:
                QMessageBox.critical(
                    parent,
                    "Import Failed",
                    f"Failed to import tracks: {str(e)}",
                )
            return False

    def _ensure_authenticated(self) -> bool:
        """Ensure the client is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.client:
            return False

        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False

    @abstractmethod
    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from the platform API.

        This method should be implemented by platform-specific providers.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from the platform API.

        This method should be implemented by platform-specific providers.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass

    def _show_collection_management_dialog(self, parent: QWidget) -> None:
        """Show the Collection management dialog.

        Args:
            parent: Parent widget
        """
        from loguru import logger

        logger.debug(
            f"Showing Collection management dialog from {self.get_platform_name()} provider"
        )

        try:
            # Import here to avoid circular imports
            from selecta.ui.dialogs.collection_management_dialog import CollectionManagementDialog

            # Create and show the dialog
            dialog = CollectionManagementDialog(parent)

            # Connect the collection modified signal to refresh our view
            dialog.collection_modified.connect(self.refresh)

            # Show the dialog
            dialog.exec()

            logger.debug("Collection management dialog closed")
        except Exception as e:
            logger.exception(f"Error showing Collection management dialog: {e}")
            QMessageBox.critical(
                parent, "Error", f"Failed to open Collection management dialog: {str(e)}"
            )
