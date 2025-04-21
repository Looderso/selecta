"""Data provider for Rekordbox.

This module provides the implementation of the platform data provider for Rekordbox,
extending the base provider with Rekordbox-specific functionality.
"""

from typing import Any, cast

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.types import SyncResult
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.ui.components.playlist.interfaces import (
    IPlatformClient,
    PlatformCapability,
)
from selecta.ui.components.playlist.platform.base_platform_provider import BasePlatformDataProvider
from selecta.ui.components.playlist.platform.rekordbox.rekordbox_playlist_item import RekordboxPlaylistItem
from selecta.ui.components.playlist.platform.rekordbox.rekordbox_track_item import RekordboxTrackItem
from selecta.ui.dialogs import ImportExportPlaylistDialog


class RekordboxDataProvider(BasePlatformDataProvider):
    """Data provider for Rekordbox.

    This provider implements access to the Rekordbox platform, allowing
    users to browse, import, export, and sync playlists.

    Note: This class includes special handling for Rekordbox playlist selection
    behavior to fix selection issues specific to Rekordbox.
    """

    def __init__(self, client: IPlatformClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Rekordbox data provider.

        Args:
            client: Optional Rekordbox client
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # If no client is provided, create one
        if client is None:
            settings_repo = SettingsRepository()
            platform_client = PlatformFactory.create("rekordbox", settings_repo)
            if not platform_client:
                raise ValueError("Could not create Rekordbox client")
            # Cast to the interface type for the provider
            client = cast(IPlatformClient, platform_client)

        # Initialize the base provider
        super().__init__(client=client, cache_timeout=cache_timeout)

        # Store a reference to the client with proper typing for direct access when needed
        self.rekordbox_client = cast(RekordboxClient, self.client)

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Rekordbox"

    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform provider.

        Returns:
            List of supported capabilities
        """
        # Re-enable FOLDERS capability now that we've fixed the issues
        return [
            PlatformCapability.IMPORT_PLAYLISTS,
            PlatformCapability.EXPORT_PLAYLISTS,
            PlatformCapability.SYNC_PLAYLISTS,
            PlatformCapability.IMPORT_TRACKS,
            PlatformCapability.FOLDERS,  # Folder support enabled
        ]

    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        Returns:
            True if connected, False otherwise
        """
        if self.client is None:
            return False

        # Try to authenticate and catch any errors
        try:
            auth_result = self.client.is_authenticated()

            # If authentication failed, log more details
            if not auth_result:
                logger.warning("Rekordbox authentication failed - check database connection")

            return auth_result
        except Exception as e:
            logger.error(f"Error during Rekordbox authentication check: {e}")
            return False

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
                "Failed to authenticate with Rekordbox. Please check your database path.",
            )
        return False

    def _fetch_playlists(self) -> list[RekordboxPlaylistItem]:
        """Fetch playlists from Rekordbox.

        Returns:
            List of Rekordbox playlist items
        """
        if not self.is_connected():
            return []

        # Get all playlists from Rekordbox
        try:
            rekordbox_playlists = self.rekordbox_client.get_all_playlists()
        except Exception as e:
            logger.error(f"Error fetching Rekordbox playlists: {e}")
            return []

        # Create repository to check if playlists are imported
        playlist_repo = PlaylistRepository()

        # Get all imported Rekordbox playlists
        imported_rekordbox_ids = set()
        try:
            # Get all playlists linked to Rekordbox
            imported_playlists = playlist_repo.get_playlists_by_platform("rekordbox")

            # Extract the platform_ids
            for playlist in imported_playlists:
                platform_id = playlist.get_platform_id("rekordbox")
                if platform_id:
                    imported_rekordbox_ids.add(platform_id)
        except Exception as e:
            logger.warning(f"Error fetching imported Rekordbox playlists: {e}")

        # =========== CRITICAL FIX: PROPERLY REORGANIZE FOLDERS AND PLAYLISTS ============
        # 1. Map IDs to their respective playlists and check parent-child relationships
        items_by_id = {}  # Maps ID to playlist item
        folder_ids = set()  # Keeps track of all folder IDs

        # First, create all playlist items and track which ones are folders
        for rb_item in rekordbox_playlists:
            # Check if this playlist has been imported (only applies to non-folders)
            is_imported = False
            if not rb_item.is_folder:
                playlist_id = str(rb_item.id)
                is_imported = playlist_id in imported_rekordbox_ids

            # Create playlist item, using status directly from the object
            item = RekordboxPlaylistItem(
                name=rb_item.name,
                item_id=rb_item.id,
                parent_id=rb_item.parent_id,
                is_folder_flag=rb_item.is_folder,  # Pass the folder status directly
                track_count=len(rb_item.tracks) if not rb_item.is_folder else 0,
                is_imported=is_imported,
            )

            # Store in our mapping and track folders
            items_by_id[rb_item.id] = item
            if rb_item.is_folder:
                folder_ids.add(rb_item.id)

        # 2. Check for and fix issues
        # Check for self-references (items that are their own parents)
        for item_id, item in items_by_id.items():
            if item.parent_id == item_id:
                logger.debug(f"Fixing self-reference: Item '{item.name}' (ID: {item_id}) is its own parent")
                item.parent_id = None  # Set to root

        # 3. Verify parent IDs exist - if not, set to root
        for _, item in items_by_id.items():
            if item.parent_id and item.parent_id not in items_by_id:
                item.parent_id = None

        # 4. Check for circular references in the hierarchy
        def detect_cycle(item_id, visited=None, path=None):
            if visited is None:
                visited = set()
            if path is None:
                path = []

            # If we've seen this item before in the current path, there's a cycle
            if item_id in path:
                # Fix by setting parent to None (root)
                items_by_id[item_id].parent_id = None
                return True

            # If we've fully processed this item before, no need to check again
            if item_id in visited:
                return False

            # Add to path for cycle detection
            path.append(item_id)

            # Get the item
            item = items_by_id[item_id]

            # If it has a parent, check if that parent creates a cycle
            if item.parent_id and item.parent_id in items_by_id and detect_cycle(item.parent_id, visited, path):
                # Fix by setting parent to None (root)
                item.parent_id = None
                return False  # Cycle is fixed

            # Mark as fully visited and remove from current path
            visited.add(item_id)
            path.pop()
            return False

        # Check each item for cycles
        for item_id in items_by_id:
            detect_cycle(item_id)

        # 5. Ensure non-folders don't have children (this is the key fix!)
        # Find items that are children of non-folders and reparent them
        for _, item in items_by_id.items():
            if item.parent_id and item.parent_id not in folder_ids:
                parent = items_by_id[item.parent_id]

                # Either set to root or to the parent's parent
                if parent.parent_id and parent.parent_id in folder_ids:
                    item.parent_id = parent.parent_id
                else:
                    item.parent_id = None

        # 6. Finally, create the list to return
        result_items = list(items_by_id.values())

        # Return all items - the model will organize them correctly
        return result_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[RekordboxTrackItem]:
        """Fetch tracks for a playlist from Rekordbox.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of Rekordbox track items
        """
        if not self.is_connected():
            return []

        # Get the tracks from Rekordbox
        rekordbox_tracks = self.rekordbox_client.get_playlist_tracks(playlist_id)

        # Convert tracks to TrackItem objects
        track_items = []
        for rb_track in rekordbox_tracks:
            # Use duration_ms from the track directly
            duration_ms = rb_track.duration_ms

            # Convert to TrackItem
            track_items.append(
                RekordboxTrackItem(
                    track_id=rb_track.id,
                    title=rb_track.title,
                    artist=rb_track.artist_name,
                    album=rb_track.album_name,
                    duration_ms=duration_ms,
                    added_at=None,  # Rekordbox tracks don't have added_at property
                    bpm=rb_track.bpm,
                    key=rb_track.key,
                    path=rb_track.folder_path,
                    rating=rb_track.rating,
                    created_at=rb_track.created_at,
                )
            )

        return track_items

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a Rekordbox playlist to the local library.

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
                    "You must be authenticated with Rekordbox to import playlists.",
                )
            return False

        try:
            # Get basic playlist info for the dialog
            rekordbox_playlist = self.rekordbox_client.get_playlist_by_id(str(playlist_id))

            # Check if playlist exists
            if rekordbox_playlist is None:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Import Error",
                        f"Cannot find playlist with ID {playlist_id}.",
                    )
                return False

            # Skip folder import
            if rekordbox_playlist.is_folder:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Import Error",
                        "Cannot import folders directly. Please import playlists inside the folder.",
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

            # Cast to AbstractPlatform for sync manager
            platform_client = cast(AbstractPlatform, self.client)

            # Create a sync manager for handling the import
            sync_manager = PlatformSyncManager(platform_client)

            # Check if playlist already exists
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
                            f"{tracks_added} new tracks added from Rekordbox.",
                        )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error syncing Rekordbox playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Sync Error", f"Failed to sync playlist: {str(e)}")
                    return False
            else:
                # Import new playlist using the sync manager
                try:
                    # Import the playlist using PlatformSyncManager
                    logger.info(f"Starting import of Rekordbox playlist: {playlist_name}")

                    # Import the playlist, passing the custom name
                    local_playlist, local_tracks = sync_manager.import_playlist(
                        platform_playlist_id=str(playlist_id), target_name=playlist_name
                    )

                    logger.info(f"Imported {len(local_tracks)} tracks from Rekordbox playlist")

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
                        f"Successfully imported Rekordbox playlist '{playlist_name}' with {len(local_tracks)} tracks"
                    )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error importing Rekordbox playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
                    return False

        except Exception as e:
            logger.exception(f"Error importing Rekordbox playlist: {e}")
            if parent:
                QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False

    def export_playlist(self, playlist_id: str, target_platform: str, parent: QWidget | None = None) -> bool:
        """Export a local playlist to Rekordbox.

        Args:
            playlist_id: Local playlist ID
            target_platform: Target platform name
            parent: Parent widget for dialogs

        Returns:
            True if successfully exported
        """
        if target_platform.lower() != "rekordbox":
            logger.warning(f"Attempted to export to non-Rekordbox platform: {target_platform}")
            return False

        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with Rekordbox to export playlists.",
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

            # Get the rekordbox folders for folder selection
            all_playlists = self.rekordbox_client.get_all_playlists()
            rekordbox_folders = [p for p in all_playlists if p.is_folder]
            folder_options = [(str(f.id), f.name) for f in rekordbox_folders]

            # Show the export dialog to let the user set the playlist name and parent folder
            dialog = ImportExportPlaylistDialog(
                parent,
                mode="export",
                platform="rekordbox",
                default_name=source_playlist.name,
                enable_folder_selection=True,
                available_folders=folder_options,
            )

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]
            parent_folder_id = dialog_values.get("parent_folder_id")

            # Cast to AbstractPlatform for sync manager
            platform_client = cast(AbstractPlatform, self.client)

            # Create a sync manager
            sync_manager = PlatformSyncManager(platform_client)

            # Check if this playlist is already linked to Rekordbox
            platform_id = source_playlist.get_platform_id("rekordbox")

            # Export the playlist
            _ = sync_manager.export_playlist(  # Ignoring returned ID since we don't use it
                local_playlist_id=int(playlist_id),
                platform_playlist_id=platform_id,
                platform_playlist_name=playlist_name,
                parent_folder_id=parent_folder_id,
            )

            # Show success message
            if parent:
                QMessageBox.information(
                    parent,
                    "Export Successful",
                    f"Successfully exported playlist '{source_playlist.name}' to Rekordbox as '{playlist_name}'.",
                )

            # Refresh playlists
            self.refresh()

            return True
        except Exception as e:
            logger.exception(f"Error exporting playlist to Rekordbox: {e}")
            if parent:
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
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with Rekordbox to sync playlists.",
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

            # Check if this playlist is linked to Rekordbox
            platform_id = source_playlist.get_platform_id("rekordbox")

            if not platform_id:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Not Linked to Rekordbox",
                        f"Playlist '{source_playlist.name}' is not linked to Rekordbox. Please export it first.",
                    )
                return False

            # Show progress information
            if parent:
                QMessageBox.information(
                    parent,
                    "Syncing Playlist",
                    "Syncing playlist with Rekordbox. This may take a moment...",
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
                    f"Successfully synced playlist '{source_playlist.name}' with Rekordbox.\n"
                    f"Added {tracks_added_to_library} tracks to library, "
                    f"added {tracks_added_to_platform} tracks to Rekordbox.",
                )

            # Refresh playlists
            self.notify_refresh_needed()

            return True
        except Exception as e:
            logger.exception(f"Error syncing playlist with Rekordbox: {e}")
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
        """Show a context menu for a Rekordbox playlist.

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
            menu = QMessageBox(dialog_parent)
            menu.setText("Right-click on a playlist to show options")
            menu.exec()
            return

        # Get the playlist item
        playlist_item = index.internalPointer()
        if not isinstance(playlist_item, RekordboxPlaylistItem):
            return

        # Create context menu based on playlist type and status
        menu = QMenu(dialog_parent)

        # For folders, we only show refresh option
        if playlist_item.is_folder():
            refresh_action = menu.addAction("Refresh")
            if refresh_action is not None:
                refresh_action.triggered.connect(self.refresh)
        else:
            # For regular playlists, show import option if not already imported
            if not playlist_item.is_imported():
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

    def _sync_playlist_via_library(self, rekordbox_playlist_id: str, parent: QWidget | None = None) -> bool:
        """Sync a Rekordbox playlist via the library provider.

        Args:
            rekordbox_playlist_id: Rekordbox playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully synced
        """
        try:
            # Find the local playlist ID for this Rekordbox playlist
            playlist_repo = PlaylistRepository()
            local_playlist = playlist_repo.get_by_platform_id("rekordbox", rekordbox_playlist_id)

            if not local_playlist:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Playlist Not Found",
                        "Cannot find this playlist in the library. Please import it first.",
                    )
                return False

            # Get the library provider from the registry
            from selecta.ui.components.playlist.platform.platform_registry import get_platform_registry

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
            logger.exception(f"Error syncing Rekordbox playlist via library: {e}")
            if parent:
                QMessageBox.critical(parent, "Sync Failed", f"Failed to sync playlist: {str(e)}")
            return False
