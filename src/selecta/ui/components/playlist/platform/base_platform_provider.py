"""Base implementation of the platform data provider interface.

This module provides a base implementation of the IPlatformDataProvider interface
that can be extended by platform-specific providers to ensure consistent behavior.
"""

from abc import abstractmethod
from collections.abc import Callable
from typing import Any, cast

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.utils.cache_manager import CacheManager
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.playlist.interfaces import (
    ICacheManager,
    IPlatformClient,
    IPlatformDataProvider,
    IPlaylistItem,
    ITrackItem,
    PlatformCapability,
)


class BasePlatformDataProvider(IPlatformDataProvider):
    """Base implementation of IPlatformDataProvider.

    This class provides common functionality for all platform data providers,
    including caching, refresh callbacks, and standard UI behaviors.
    """

    def __init__(self, client: IPlatformClient | None = None, cache_timeout: float = 300.0):
        """Initialize the base platform data provider.

        Args:
            client: Platform client instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        self.client = client
        self.cache: ICacheManager = cast(ICacheManager, CacheManager(default_timeout=cache_timeout))
        self._refresh_callbacks: set[Callable[[], None]] = set()

        # Flag to prevent recursive refreshes
        self._is_refreshing = False

        # Cache keys - each platform should customize these in their constructor
        self._platform_name = self.get_platform_name().lower()
        self._playlists_cache_key = f"{self._platform_name}_playlists"

    def register_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when data needs to be refreshed.

        Args:
            callback: Function to call when refresh is needed
        """
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.add(callback)

    def unregister_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a previously registered refresh callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._refresh_callbacks:
            self._refresh_callbacks.remove(callback)

    def notify_refresh_needed(self) -> None:
        """Notify all registered listeners that data needs to be refreshed."""
        for callback in self._refresh_callbacks:
            callback()

    def get_all_playlists(self) -> list[IPlaylistItem]:
        """Get all playlists with caching.

        Returns:
            List of playlist items
        """
        # Try to get from cache first
        if self.cache.has_valid(self._playlists_cache_key):
            return self.cache.get(self._playlists_cache_key, [])

        # Check authentication
        if not self.is_connected():
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

    def get_playlist_tracks(self, playlist_id: Any) -> list[ITrackItem]:
        """Get all tracks in a playlist with caching.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        # Generate cache key for this playlist's tracks
        cache_key = f"{self._platform_name}_tracks_{playlist_id}"

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

        # Check authentication
        if not self.is_connected():
            logger.warning(f"{self.get_platform_name()} client is not authenticated")
            # Return empty list instead of triggering authentication
            return []

        try:
            # Get fresh data
            tracks = self._fetch_playlist_tracks(playlist_id)

            # Cache the result
            self.cache.set(cache_key, tracks)

            return tracks
        except Exception as e:
            logger.error(f"Error getting tracks for playlist {playlist_id}: {e}")

            # Return cached data if available, even if expired
            if self.cache.has(cache_key):
                logger.info(f"Returning expired cache data after fetch error for {playlist_id}")
                return self.cache.get(cache_key, [], ignore_expiry=True)

            return []

    def refresh(self) -> None:
        """Refresh all cached data and notify listeners."""
        # Skip if already refreshing to prevent infinite loops
        if self._is_refreshing:
            logger.debug("Skipping refresh - already in progress")
            return

        # Set flag to prevent reentrant calls
        self._is_refreshing = True

        try:
            # Clear the cache
            self.cache.clear()

            # Notify listeners
            self.notify_refresh_needed()
        finally:
            # Always reset the refreshing flag
            self._is_refreshing = False

    def refresh_playlist(self, playlist_id: Any) -> None:
        """Refresh a specific playlist's tracks.

        Args:
            playlist_id: ID of the playlist to refresh
        """
        # Invalidate just this playlist's cache
        cache_key = f"{self._platform_name}_tracks_{playlist_id}"
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
        if not self.is_connected():
            return

        # Use ThreadManager to run the refresh in background
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

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a platform playlist.

        This provides a default implementation that can be overridden by platform-specific
        providers.

        Args:
            tree_view: The tree view containing the playlist
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        index = tree_view.indexAt(position)
        if not index.isValid():
            # Create context menu for empty space
            menu = QMenu(tree_view)

            # Add refresh option
            refresh_action = menu.addAction("Refresh All")
            if refresh_action is not None:
                refresh_action.triggered.connect(self.refresh)

            # Show the menu
            viewport = tree_view.viewport()
            if viewport is not None:
                menu.exec(viewport.mapToGlobal(position))
            return

        # Get the playlist item from the internal pointer
        item = index.internalPointer()
        if not item:
            return

        # Create the context menu
        menu = QMenu(tree_view)

        # Check if this playlist is imported
        is_imported = False
        if hasattr(item, "is_imported"):
            is_imported = item.is_imported
            logger.debug(f"Playlist {item.name} (ID: {getattr(item, 'item_id', 'unknown')}) is_imported={is_imported}")

        # Add context menu options based on import status
        if is_imported:
            # For already imported playlists, show sync option
            if PlatformCapability.SYNC_PLAYLISTS in self.get_capabilities():
                sync_action = menu.addAction("Sync with Library")
                if sync_action is not None:
                    # Convert item_id to string for the sync_playlist method
                    item_id = getattr(item, "item_id", None)
                    if item_id is not None:
                        sync_action.triggered.connect(lambda: self.sync_playlist(str(item_id), parent))
        else:
            # For non-imported playlists, show import options
            if PlatformCapability.IMPORT_PLAYLISTS in self.get_capabilities():
                import_action = menu.addAction("Import to Library")
                if import_action is not None:
                    item_id = getattr(item, "item_id", None)
                    import_action.triggered.connect(lambda: self.import_playlist(item_id, parent))

        # Add refresh option
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        if refresh_action is not None:
            item_id = getattr(item, "item_id", None)
            refresh_action.triggered.connect(lambda: self.refresh_playlist(item_id))

        # Show the menu
        viewport = tree_view.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(position))

    def show_track_context_menu(self, table_view: Any, position: Any, parent: QWidget | None = None) -> None:
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

        if is_single_track:
            play_action = menu.addAction("Play")
            menu.addSeparator()

            if PlatformCapability.IMPORT_TRACKS in self.get_capabilities():
                add_to_library_action = menu.addAction("Add to Library")
                if add_to_library_action is not None:
                    add_to_library_action.triggered.connect(lambda: self._add_tracks_to_library([first_track], parent))

            # Add search on other platforms submenu
            search_menu = menu.addMenu("Search On")

            # Add platform-specific search options (excluding current platform)
            platform_search_actions = {}
            for platform in ["spotify", "discogs", "youtube", "rekordbox"]:
                if platform != current_platform:
                    # Check if search_menu is not None before adding action
                    action = None
                    if search_menu is not None:
                        action = search_menu.addAction(platform.capitalize())
                        # Store the action only if it was successfully created
                        if action is not None:
                            platform_search_actions[platform] = action
                            # Enable/disable based on app state
                            action.setEnabled(platform not in ["rekordbox"])  # Rekordbox search not implemented
        else:
            # Multi-track actions
            tracks_count = len(selected_tracks)
            if PlatformCapability.IMPORT_TRACKS in self.get_capabilities():
                add_to_library_action = menu.addAction(f"Add {tracks_count} Tracks to Library")
                if add_to_library_action is not None:
                    # Wrap in a lambda to avoid line length issues
                    add_to_library_action.triggered.connect(
                        lambda: self._add_tracks_to_library(selected_tracks, parent)
                    )

        # Show the menu and handle the selected action
        viewport = table_view.viewport()
        action = menu.exec(viewport.mapToGlobal(position)) if viewport is not None else None
        if not action:
            return

        # Handle action
        if is_single_track and action == play_action:
            # Get the main window
            main_window = table_view.window()

            # Emit play track signal if available
            if hasattr(main_window, "play_track"):
                main_window.play_track(first_track)

        # Handle search actions
        if is_single_track:
            for platform, search_action in platform_search_actions.items():
                if action == search_action:
                    self._search_on_platform(platform, first_track, table_view)

    def _search_on_platform(self, platform: str, track: Any, parent_widget: QWidget) -> None:
        """Search for a track on another platform.

        Args:
            platform: Platform to search on
            track: Track to search for
            parent_widget: Parent widget
        """
        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window
        main_window = parent_widget.window()

        # Try to call the appropriate search method on the main window
        search_method_name = f"show_{platform}_search"
        if hasattr(main_window, search_method_name):
            search_method = getattr(main_window, search_method_name)
            if callable(search_method):
                search_method(search_query)

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
                from PyQt6.QtWidgets import QMessageBox

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
            from selecta.core.platform.sync_manager import PlatformSyncManager

            if self.client is None:
                raise ValueError(f"No {self.get_platform_name()} client available")

            # Cast client to AbstractPlatform to satisfy type checking
            # This is safe because IPlatformClient implements the required methods
            platform_client = cast(AbstractPlatform, self.client)
            sync_manager = PlatformSyncManager(platform_client)

            # Track success counter
            successful_imports = 0

            # Import each track
            for track in tracks:
                try:
                    # Import the track with proper error handling
                    try:
                        imported_track = sync_manager.link_manager.import_track(track)
                        if imported_track:
                            successful_imports += 1
                    except ValueError as e:
                        # Log validation errors (missing title/artist)
                        track_info = getattr(track, "title", "Unknown") + " by " + getattr(track, "artist", "Unknown")
                        logger.warning(f"Import validation error for track {track_info}: {str(e)}")

                        # Show error in parent window if available
                        if parent:
                            from PyQt6.QtWidgets import QMessageBox

                            QMessageBox.warning(parent, "Track Import Error", f"Failed to import track: {str(e)}")
                    except Exception as e:
                        # Log unexpected errors
                        logger.exception(f"Unexpected error importing track: {str(e)}")
                except Exception as e:
                    track_id = getattr(track, "id", "unknown")
                    logger.warning(f"Failed to import track {track_id}: {e}")

            # Show result message
            if parent:
                if successful_imports > 0:
                    QMessageBox.information(
                        parent,
                        "Import Successful",
                        f"Successfully added {successful_imports} of {len(tracks)} track(s) to library.",
                    )
                else:
                    QMessageBox.warning(
                        parent,
                        "Import Failed",
                        "Failed to add any tracks to library.",
                    )

            # Signal that local tracks have changed
            if successful_imports > 0:
                # Notify all registered listeners about the change
                self.notify_refresh_needed()

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
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
                    f"Importing {self.get_platform_name()} playlist tracks. This may take a moment...",
                )

            # Create a sync manager
            from selecta.core.platform.sync_manager import PlatformSyncManager

            if self.client is None:
                raise ValueError(f"No {self.get_platform_name()} client available")

            # Cast client to AbstractPlatform to satisfy type checking
            # This is safe because IPlatformClient implements the required methods
            platform_client = cast(AbstractPlatform, self.client)
            sync_manager = PlatformSyncManager(platform_client)

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
            self.notify_refresh_needed()
            return True

        except Exception as e:
            logger.exception(f"Error importing {self.get_platform_name()} playlist to existing playlist: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Import Failed",
                    f"Failed to import tracks: {str(e)}",
                )
            return False

    # Abstract methods that platform-specific providers must implement

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform provider.

        Returns:
            List of supported capabilities
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def connect_platform(self, parent: QWidget | None = None) -> bool:
        """Connect to the platform.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successfully connected
        """
        pass

    @abstractmethod
    def _fetch_playlists(self) -> list[IPlaylistItem]:
        """Fetch playlists from the platform API.

        This method should be implemented by platform-specific providers.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[ITrackItem]:
        """Fetch tracks for a playlist from the platform API.

        This method should be implemented by platform-specific providers.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass

    @abstractmethod
    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a platform playlist to the local library.

        Args:
            playlist_id: ID of the playlist to import
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def export_playlist(self, playlist_id: str, target_platform: str, parent: QWidget | None = None) -> bool:
        """Export a local playlist to a platform.

        Args:
            playlist_id: ID of the local playlist to export
            target_platform: Platform to export to
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a playlist bidirectionally between local and platform.

        Args:
            playlist_id: ID of the playlist to sync
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        pass
