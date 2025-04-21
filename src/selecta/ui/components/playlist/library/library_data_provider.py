"""Data provider for the local library.

This module provides the LibraryDataProvider class which extends BasePlatformDataProvider
to implement the local library-specific playlist and track operations.
"""

from typing import Any

from loguru import logger
from PyQt6.QtWidgets import QMenu, QMessageBox, QTreeView, QWidget

from selecta.core.data.database import get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.ui.components.playlist.interfaces import (
    PlatformCapability,
)
from selecta.ui.components.playlist.library.library_playlist_item import LibraryPlaylistItem
from selecta.ui.components.playlist.library.library_track_item import LibraryTrackItem
from selecta.ui.components.playlist.platform.base_platform_provider import BasePlatformDataProvider
from selecta.ui.components.playlist.platform.platform_registry import get_platform_registry


class LibraryDataProvider(BasePlatformDataProvider):
    """Data provider for the local library.

    This provider implements access to the local music library database.
    """

    # Constants for Collection playlist
    COLLECTION_NAME = "Collection"
    COLLECTION_DESCRIPTION = "Master collection of all tracks"

    def __init__(self, cache_timeout: float = 300.0):
        """Initialize the library data provider.

        Args:
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Initialize the base provider with no client: local provider doesn't need a platform client
        super().__init__(client=None, cache_timeout=cache_timeout)

        # Create database session and repositories
        self.session = get_session()
        self.playlist_repo = PlaylistRepository(self.session)
        self.track_repo = TrackRepository(self.session)

        # Ensure Collection playlist exists
        self._collection_playlist_id = self._ensure_collection_playlist()

        # Initialize current playlist ID (will be set when showing specific playlist)
        self._current_playlist_id = None

    def _get_parent_widget(self, default_widget: QWidget, parent: QWidget | None = None) -> QWidget:
        """Get the parent widget for dialog operations.

        Args:
            default_widget: Default widget to use if parent is None
            parent: Explicit parent widget if provided

        Returns:
            The appropriate parent widget
        """
        return parent if parent is not None else default_widget

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Library"

    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform provider.

        Returns:
            List of supported capabilities
        """
        return [
            PlatformCapability.IMPORT_PLAYLISTS,
            PlatformCapability.EXPORT_PLAYLISTS,
            PlatformCapability.SYNC_PLAYLISTS,
            PlatformCapability.CREATE_PLAYLISTS,
            PlatformCapability.DELETE_PLAYLISTS,
            PlatformCapability.MODIFY_PLAYLISTS,
            PlatformCapability.IMPORT_TRACKS,
            PlatformCapability.EXPORT_TRACKS,
            PlatformCapability.SEARCH,
            PlatformCapability.FOLDERS,
            PlatformCapability.COVER_ART,
            PlatformCapability.RATINGS,
        ]

    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        For Library provider, this always returns True since we always have
        access to the local database.

        Returns:
            Always True for Library provider
        """
        return True

    def connect_platform(self, parent: QWidget | None = None) -> bool:
        """Connect to the platform.

        For Library provider, this is a no-op as we're always connected.

        Args:
            parent: Parent widget for dialogs

        Returns:
            Always True for Library provider
        """
        return True

    def _ensure_collection_playlist(self) -> int:
        """Ensure that the Collection playlist exists.

        If it doesn't exist, create it.

        Returns:
            ID of the Collection playlist
        """
        # Check if Collection playlist already exists
        playlists = self.playlist_repo.get_all()
        for playlist in playlists:
            if playlist.name == self.COLLECTION_NAME:
                logger.debug(f"Found existing Collection playlist with ID {playlist.id}")
                return playlist.id

        # Create Collection playlist if it doesn't exist
        logger.info("Creating Collection playlist")
        playlist = self.playlist_repo.create(
            {
                "name": self.COLLECTION_NAME,
                "description": self.COLLECTION_DESCRIPTION,
                "is_folder": False,
                "is_local": True,
            }
        )

        return playlist.id

    def _fetch_playlists(self) -> list[LibraryPlaylistItem]:
        """Fetch all library playlists from the database.

        Returns:
            List of playlist items
        """
        try:
            # Get all playlists from the database
            playlists = self.playlist_repo.get_all()

            # Convert to PlaylistItems
            playlist_items = []

            for playlist in playlists:
                # Get track count
                track_count = self.playlist_repo.get_track_count(playlist.id)

                # Skip folders for now
                if playlist.is_folder:
                    continue

                # Determine which platforms this playlist is synced with
                synced_platforms = []

                # If it has a source platform, it's synced with that platform
                if playlist.source_platform:
                    synced_platforms.append(playlist.source_platform)

                # Check if this playlist is exported to any platforms
                if playlist.platform_id:
                    # Add logic here to check if exported to specific platforms
                    # and add them to synced_platforms
                    pass

                # Create the playlist item
                playlist_items.append(
                    LibraryPlaylistItem(
                        name=playlist.name,
                        item_id=playlist.id,
                        track_count=track_count,
                        is_folder_flag=False,
                        description=playlist.description,
                        source_platform=playlist.source_platform,
                        platform_id=playlist.platform_id,
                        is_collection=(playlist.name == self.COLLECTION_NAME),
                        synced_platforms=synced_platforms,
                    )
                )

            return playlist_items
        except Exception as e:
            logger.exception(f"Error fetching library playlists: {e}")
            return []

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[LibraryTrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        try:
            # Get all tracks in the playlist
            tracks = self.playlist_repo.get_playlist_tracks(playlist_id)

            # Convert to TrackItems
            track_items = []

            for track in tracks:
                # Get all platforms this track is available on
                available_platforms = []

                # Create platform info list
                platform_info_list = []
                for info in track.platform_info:
                    platform_name = info.platform
                    available_platforms.append(platform_name)

                    platform_info_list.append(
                        {
                            "platform": platform_name,
                            "platform_id": info.platform_id,
                            "uri": info.uri,
                        }
                    )

                # Get genre names if available
                genre_str = ""
                if hasattr(track, "genres") and track.genres:
                    genre_str = ", ".join([g.name for g in track.genres])

                # Get tags if available
                tags = []
                if hasattr(track, "tags") and track.tags:
                    tags = [tag.name for tag in track.tags]

                # Create the track item
                track_items.append(
                    LibraryTrackItem(
                        track_id=track.id,
                        title=track.title,
                        artist=track.artist,
                        album=track.album,
                        genre=genre_str,
                        duration_ms=track.duration_ms,
                        local_path=track.local_path,
                        bpm=track.bpm,
                        tags=tags,
                        platform_info=platform_info_list,
                        quality=track.quality if hasattr(track, "quality") else -1,
                        has_image=bool(track.images),
                        platforms=available_platforms,
                    )
                )

            return track_items
        except Exception as e:
            logger.exception(f"Error fetching playlist tracks: {e}")
            return []

    def _ensure_tracks_in_collection(self, track_ids: list[int]) -> None:
        """Ensure all tracks are in the Collection playlist.

        Args:
            track_ids: List of track IDs to ensure are in Collection
        """
        if not track_ids:
            return

        # Get tracks already in Collection
        collection_tracks = self.playlist_repo.get_playlist_tracks(self._collection_playlist_id)
        collection_track_ids = [t.id for t in collection_tracks]

        # Find tracks not already in Collection
        tracks_to_add = [t_id for t_id in track_ids if t_id not in collection_track_ids]

        # Add tracks to Collection if needed
        for track_id in tracks_to_add:
            try:
                self.playlist_repo.add_track(self._collection_playlist_id, track_id)
                logger.debug(f"Added track {track_id} to Collection")
            except Exception as e:
                logger.error(f"Failed to add track {track_id} to Collection: {e}")

    def show_track_context_menu(self, table_view: Any, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a track.

        Args:
            table_view: The table view
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        # Use parent if provided, otherwise use table_view
        # (parent_widget not used in this implementation)

        index = table_view.indexAt(position)
        if not index.isValid():
            return

        # Get the current selected tracks
        selected_indexes = table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        # Collect all selected tracks
        selected_tracks = []
        for index in selected_indexes:
            row = index.row()
            model = table_view.model()
            track = model.get_track(row)
            if track:
                selected_tracks.append(track)

        if not selected_tracks:
            return

        # Use the first track as a reference for single-track operations
        first_track = selected_tracks[0]

        # Create context menu
        menu = QMenu(table_view)

        # Get current playlist ID if it exists
        current_playlist_id = self._current_playlist_id

        # In a playlist view - add option to remove from current playlist
        if current_playlist_id is not None and current_playlist_id != self._collection_playlist_id and menu:
            remove_action = menu.addAction("Remove from current playlist")
            if remove_action:
                remove_action.triggered.connect(
                    lambda _=False: self._remove_tracks_from_playlist(current_playlist_id, selected_tracks)
                )
            menu.addSeparator()

        # Add to Collection option
        add_to_collection_action = menu.addAction("Add to Collection")
        if add_to_collection_action:
            add_to_collection_action.triggered.connect(lambda _=False: self._add_tracks_to_collection(selected_tracks))

        # Add to playlist submenu
        add_menu = menu.addMenu("Add to playlist")

        # Get all regular (non-folder) playlists
        all_playlists = self.playlist_repo.get_all()
        has_playlists = False

        # Track actions to playlists mapping for the menu handlers
        playlist_actions = {}

        for playlist in all_playlists:
            # Skip folders, the current playlist, and Collection
            if (
                playlist.is_folder
                or (current_playlist_id is not None and playlist.id == current_playlist_id)
                or (hasattr(playlist, "name") and playlist.name == self.COLLECTION_NAME)
            ):
                continue

            has_playlists = True
            if add_menu is not None:
                playlist_action = add_menu.addAction(playlist.name)
                playlist_actions[playlist.id] = playlist_action

        # Connect actions separately to avoid lambda capture issues
        for pid, action in playlist_actions.items():
            if action:  # Ensure action is not None
                action.triggered.connect(lambda _=False, pid=pid: self._add_tracks_to_playlist(pid, selected_tracks))

        if not has_playlists and add_menu is not None:
            no_playlist_action = add_menu.addAction("No playlists available")
            if no_playlist_action:  # Ensure action is not None
                no_playlist_action.setEnabled(False)

        # Add option to create a new playlist with these tracks
        if add_menu:
            add_menu.addSeparator()
            new_playlist_action = add_menu.addAction("Create new playlist...")
            if new_playlist_action:  # Ensure action is not None
                new_playlist_action.triggered.connect(
                    lambda _=False: self._create_playlist_with_tracks(selected_tracks)
                )

        # Add search actions (only enabled for single track)
        if len(selected_tracks) == 1 and menu:
            menu.addSeparator()
            search_menu = menu.addMenu("Search On")
            if search_menu:
                # Get all platforms that support search
                registry = get_platform_registry()
                search_platforms = registry.get_platforms_with_capability(PlatformCapability.SEARCH)

                # Track platform actions for search handler
                platform_actions = {}

                for platform in search_platforms:
                    action = search_menu.addAction(platform.capitalize())
                    if action:
                        platform_actions[platform] = action

                # Connect each action separately to avoid lambda capture issues
                for platform, action in platform_actions.items():
                    if action:  # Ensure action is not None
                        action.triggered.connect(
                            lambda _=False, p=platform: self._search_on_platform(p, first_track, table_view)
                        )

        # Show the menu at the cursor position
        if menu and table_view and table_view.viewport():
            menu.exec(table_view.viewport().mapToGlobal(position))

    def _add_tracks_to_collection(self, tracks: list[Any]) -> None:
        """Add tracks to the Collection playlist.

        Args:
            tracks: List of track objects to add to Collection
        """
        if not tracks:
            return

        try:
            # Get tracks IDs and add to Collection
            track_ids = [track.track_id for track in tracks]
            self._ensure_tracks_in_collection(track_ids)

            # Refresh the UI if needed
            self.notify_refresh_needed()

        except Exception as e:
            logger.exception(f"Error adding tracks to Collection: {e}")

    def _add_tracks_to_playlist(self, playlist_id: int, tracks: list[Any]) -> None:
        """Add selected tracks to a playlist.

        Args:
            playlist_id: The ID of the playlist to add tracks to
            tracks: List of track objects to add
        """
        if not tracks:
            return

        try:
            # Get the playlist
            playlist = self.playlist_repo.get_by_id(playlist_id)
            if not playlist:
                logger.error(f"Playlist with ID {playlist_id} not found.")
                return

            # Track counters
            added_count = 0
            already_exists_count = 0
            track_ids_to_add_to_collection = []

            # Get existing track IDs in playlist for faster lookup
            existing_track_ids = {pt.id for pt in playlist.tracks}

            # Add each track to the playlist
            for track in tracks:
                try:
                    # Check if the track is already in the playlist
                    if track.track_id in existing_track_ids:
                        already_exists_count += 1
                        continue

                    # Add track to playlist
                    self.playlist_repo.add_track(playlist.id, track.track_id)
                    added_count += 1

                    # Collect track IDs to add to Collection (as a batch operation)
                    if playlist.id != self._collection_playlist_id:
                        track_ids_to_add_to_collection.append(track.track_id)

                except Exception as e:
                    logger.warning(f"Failed to add track {track.track_id} to playlist: {e}")

            # Ensure tracks are also in Collection (do this as a batch)
            if track_ids_to_add_to_collection:
                self._ensure_tracks_in_collection(track_ids_to_add_to_collection)

            # Show success message
            if added_count > 0 or already_exists_count > 0:
                messages = []
                if added_count > 0:
                    suffix = "s" if added_count > 1 else ""
                    messages.append(f"Added {added_count} track{suffix} to playlist '{playlist.name}'.")

                if already_exists_count > 0:
                    suffix = "s" if already_exists_count > 1 else ""
                    messages.append(f"{already_exists_count} track{suffix} already in playlist.")

                QMessageBox.information(None, "Tracks Added", "\n".join(messages))

            # Refresh if this is the currently displayed playlist
            if self._current_playlist_id is not None and self._current_playlist_id == playlist_id:
                self.refresh()

        except Exception as e:
            logger.exception(f"Error adding tracks to playlist: {e}")
            QMessageBox.critical(None, "Error", f"Failed to add tracks to playlist: {str(e)}")

    def _remove_tracks_from_playlist(self, playlist_id: int, tracks: list[Any]) -> None:
        """Remove selected tracks from a playlist.

        Args:
            playlist_id: The ID of the playlist to remove tracks from
            tracks: List of track objects to remove
        """
        if not tracks:
            return

        # Confirm removal
        response = QMessageBox.question(
            None,
            "Remove Tracks",
            f"Are you sure you want to remove {len(tracks)} track{'s' if len(tracks) > 1 else ''} from this playlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            # Create a repository instance
            playlist_repo = self.playlist_repo

            # Get the playlist
            playlist = playlist_repo.get_by_id(playlist_id)
            if not playlist:
                QMessageBox.critical(None, "Error", f"Playlist with ID {playlist_id} not found.")
                return

            # Remove each track from the playlist
            removed_count = 0
            for track in tracks:
                try:
                    if playlist_repo.remove_track(playlist_id, track.track_id):
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove track {track.track_id} from playlist: {e}")

            # Show success message
            if removed_count > 0:
                QMessageBox.information(
                    None,
                    "Tracks Removed",
                    f"Removed {removed_count} track{'s' if removed_count > 1 else ''} from playlist '{playlist.name}'.",
                )

                # Refresh the view
                self.refresh()
            else:
                QMessageBox.information(None, "No Tracks Removed", "No tracks were removed from the playlist.")

        except Exception as e:
            logger.exception(f"Error removing tracks from playlist: {e}")
            QMessageBox.critical(None, "Error", f"Failed to remove tracks from playlist: {str(e)}")

    def _create_playlist_with_tracks(self, tracks: list[Any]) -> None:
        """Create a new playlist and add the selected tracks to it.

        Args:
            tracks: List of track objects to add to the new playlist
        """
        if not tracks:
            return

        # Import the create playlist dialog
        from selecta.ui.dialogs import CreatePlaylistDialog

        # Get all folder playlists for parent selection
        folders = []
        try:
            all_playlists = self.playlist_repo.get_all()
            folders = [(pl.id, pl.name) for pl in all_playlists if pl.is_folder]
        except Exception as e:
            logger.warning(f"Failed to fetch folders for playlist creation: {e}")

        # Show create playlist dialog
        dialog = CreatePlaylistDialog(None, available_folders=folders)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        # Get values from dialog
        values = dialog.get_values()
        name = values.get("name", "")
        is_folder = values.get("is_folder", False)
        parent_id = values.get("parent_id")

        # Validate inputs
        if not name:
            QMessageBox.warning(None, "Missing Information", "Please enter a name for the playlist.")
            return

        if is_folder:
            QMessageBox.warning(
                None,
                "Cannot Add Tracks to Folder",
                "You cannot add tracks to a folder. Please create a regular playlist instead.",
            )
            return

        try:
            # Create the new playlist using repository
            new_playlist = self.playlist_repo.create(
                {
                    "name": name,
                    "is_folder": False,  # Always create as regular playlist when adding tracks
                    "is_local": True,
                    "parent_id": parent_id,
                    "description": "",
                }
            )

            # Add tracks to the playlist
            added_count = 0
            track_ids_to_add_to_collection = []

            for track in tracks:
                try:
                    self.playlist_repo.add_track(new_playlist.id, track.track_id)
                    added_count += 1
                    track_ids_to_add_to_collection.append(track.track_id)
                except Exception as e:
                    logger.warning(f"Failed to add track {track.track_id} to new playlist: {e}")

            # Ensure all tracks are also in Collection (do this as a batch)
            if track_ids_to_add_to_collection:
                self._ensure_tracks_in_collection(track_ids_to_add_to_collection)

            # Show success message
            suffix = "s" if added_count > 1 else ""
            QMessageBox.information(
                None, "Playlist Created", f"Created playlist '{name}' with {added_count} track{suffix}."
            )

            # Refresh the view to show the new playlist
            self.refresh()

        except Exception as e:
            logger.exception(f"Error creating playlist with tracks: {e}")
            QMessageBox.critical(None, "Error", f"Failed to create playlist: {str(e)}")

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a platform playlist to the local library.

        Since this is the Library provider, this method doesn't actually do anything.
        The Library provider is the target of imports, not the source.

        Args:
            playlist_id: ID of the playlist to import
            parent: Parent widget for dialogs

        Returns:
            False as Library provider doesn't import playlists
        """
        if parent:
            QMessageBox.information(
                parent,
                "Import Not Supported",
                "The Library is the destination for imports from other platforms. "
                "Please use the import function from a platform like Spotify or Rekordbox.",
            )
        return False

    def export_playlist(self, playlist_id: str, target_platform: str, parent: QWidget | None = None) -> bool:
        """Export a local playlist to a platform.

        Args:
            playlist_id: ID of the local playlist to export
            target_platform: Platform to export to
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Get the provider for the target platform
        registry = get_platform_registry()
        target_provider = registry.get_provider(target_platform)

        if not target_provider:
            if parent:
                QMessageBox.warning(
                    parent,
                    "Export Failed",
                    f"Platform '{target_platform}' not available. Please ensure it is properly configured.",
                )
            return False

        # Check if the target platform supports exports
        if PlatformCapability.EXPORT_PLAYLISTS not in target_provider.get_capabilities():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Export Not Supported",
                    f"The {target_platform.capitalize()} platform does not support exporting playlists.",
                )
            return False

        # Use the target platform's export implementation
        return target_provider.export_playlist(playlist_id, target_platform, parent)

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Synchronize a playlist with its source platform.

        Args:
            playlist_id: ID of the playlist to sync
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Get the playlist from the database
        playlist = self.playlist_repo.get_by_id(int(playlist_id))
        if not playlist:
            if parent:
                QMessageBox.critical(parent, "Sync Error", f"Playlist with ID {playlist_id} not found.")
            return False

        # Check if this is an imported playlist
        if not playlist.source_platform or not playlist.platform_id:
            if parent:
                QMessageBox.warning(
                    parent,
                    "Sync Error",
                    "This playlist was not imported from a platform and cannot be synced.",
                )
            return False

        # Get the provider for the source platform
        registry = get_platform_registry()
        source_provider = registry.get_provider(playlist.source_platform)

        if not source_provider:
            if parent:
                QMessageBox.warning(
                    parent,
                    "Sync Failed",
                    f"Platform '{playlist.source_platform}' not available. Please ensure it is properly configured.",
                )
            return False

        # Check if the source platform supports sync
        if PlatformCapability.SYNC_PLAYLISTS not in source_provider.get_capabilities():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Sync Not Supported",
                    f"The {playlist.source_platform.capitalize()} platform does not support syncing playlists.",
                )
            return False

        # Use the source platform's sync implementation
        return source_provider.sync_playlist(playlist_id, parent)

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a library playlist.

        Args:
            tree_view: The tree view
            position: Position where the context menu was requested
            parent: Parent widget for dialogs
        """
        # Get the playlist item at this position
        index = tree_view.indexAt(position)
        dialog_parent = self._get_parent_widget(tree_view, parent)

        if not index.isValid():
            # Right-click on empty space
            menu = QMenu(tree_view)

            # Add Collection management option
            manage_action = menu.addAction("Manage Collection...")
            if manage_action:
                manage_action.triggered.connect(lambda _=False: self._show_collection_management_dialog(dialog_parent))

            # Add refresh option
            menu.addSeparator()
            refresh_action = menu.addAction("Refresh All")
            if refresh_action:
                refresh_action.triggered.connect(lambda _=False: self.refresh())

            # Show the menu
            viewport = tree_view.viewport()
            if viewport is not None:
                menu.exec(viewport.mapToGlobal(position))
            return

        # Get the playlist item
        playlist_item = index.internalPointer()
        if not playlist_item or playlist_item.is_folder():
            return

        # Create context menu
        menu = QMenu(tree_view)

        # Special handling for Collection playlist
        is_collection = False
        if hasattr(playlist_item, "is_collection") and playlist_item.is_collection:
            is_collection = True

            # Add Collection management option to Collection playlist
            manage_action = menu.addAction("Manage Collection...")
            if manage_action:
                manage_action.triggered.connect(lambda _=False: self._show_collection_management_dialog(dialog_parent))
            menu.addSeparator()

        # Figure out which platform options to show
        item_id = str(playlist_item.item_id)

        # Check if this is an imported playlist that we can sync
        if (
            hasattr(playlist_item, "is_imported")
            and callable(playlist_item.is_imported)
            and playlist_item.is_imported()
            and hasattr(playlist_item, "source_platform")
            and playlist_item.source_platform
        ):
            source_platform = playlist_item.source_platform
            sync_action = menu.addAction(f"Sync with {source_platform.capitalize()}")
            if sync_action:
                sync_action.triggered.connect(lambda _=False: self.sync_playlist(item_id, dialog_parent))

        # Add export actions for all platforms that support it
        registry = get_platform_registry()
        export_platforms = registry.get_platforms_with_capability(PlatformCapability.EXPORT_PLAYLISTS)

        if export_platforms:
            export_menu = menu.addMenu("Export to...")

            for platform in export_platforms:
                # Create separate handler function for each platform to avoid lambda capture issues
                def create_export_handler(p, item_id=item_id):
                    return lambda _=False: self.export_playlist(item_id, p, dialog_parent)

                if export_menu is not None:
                    export_action = export_menu.addAction(platform.capitalize())
                    if export_action:
                        export_action.triggered.connect(create_export_handler(platform))

        # Only show delete action if this is not the Collection playlist
        if not is_collection:
            # Add delete action
            menu.addSeparator()
            delete_action = menu.addAction("Delete Playlist")
            if delete_action:
                delete_action.triggered.connect(
                    lambda _=False: self._delete_playlist(playlist_item.item_id, dialog_parent)
                )

        # Show the menu at the cursor position
        if menu and tree_view:
            viewport = tree_view.viewport()
            if viewport is not None:
                menu.exec(viewport.mapToGlobal(position))

    def _delete_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> None:
        """Delete a playlist.

        Args:
            playlist_id: ID of the playlist to delete
            parent: Parent widget for dialogs
        """
        # Don't allow deletion of Collection playlist
        if playlist_id == self._collection_playlist_id:
            if parent:
                QMessageBox.warning(
                    parent,
                    "Cannot Delete Collection",
                    "The Collection playlist cannot be deleted as it contains all tracks in your library.",
                )
            return

        # Get the playlist from the database
        playlist = self.playlist_repo.get_by_id(playlist_id)
        if not playlist:
            if parent:
                QMessageBox.critical(parent, "Delete Error", f"Playlist with ID {playlist_id} not found.")
            return

        # Ask for confirmation
        if parent:
            response = QMessageBox.question(
                parent,
                "Confirm Delete",
                f"Are you sure you want to delete the playlist '{playlist.name}'?\n\n"
                "This will not delete the tracks from your library.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return

        # Delete the playlist
        try:
            self.playlist_repo.delete(playlist_id)
            if parent:
                QMessageBox.information(parent, "Delete Successful", f"Playlist '{playlist.name}' was deleted.")
            self.refresh()  # Refresh the UI
        except Exception as e:
            logger.exception(f"Error deleting playlist: {e}")
            if parent:
                QMessageBox.critical(parent, "Delete Error", f"Failed to delete playlist: {str(e)}")

    def _show_collection_management_dialog(self, parent: QWidget) -> None:
        """Show the Collection management dialog.

        Args:
            parent: Parent widget
        """
        try:
            # Import here to avoid circular imports
            from selecta.ui.dialogs.collection_management_dialog import CollectionManagementDialog

            # Create and show the dialog
            dialog = CollectionManagementDialog(parent)

            # Connect the collection modified signal to refresh our view
            dialog.collection_modified.connect(self.refresh)

            # Show the dialog
            dialog.exec()
        except Exception as e:
            logger.exception(f"Error showing Collection management dialog: {e}")
            if parent:
                QMessageBox.critical(parent, "Error", f"Failed to open Collection management dialog: {str(e)}")

    def _search_on_platform(self, platform: str, track: Any, parent: QWidget) -> None:
        """Search for a track on another platform.

        Args:
            platform: Platform to search on
            track: Track to search for
            parent: Parent widget
        """
        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window
        main_window = parent.window()

        # Try to call the appropriate search method on the main window
        search_method_name = f"show_{platform}_search"
        if hasattr(main_window, search_method_name):
            search_method = getattr(main_window, search_method_name)
            if callable(search_method):
                search_method(search_query)
