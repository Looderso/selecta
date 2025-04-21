"""Discogs playlist data provider implementation."""

from typing import Any, Protocol, TypeVar, cast, runtime_checkable

from loguru import logger
from PyQt6.QtWidgets import (
    QMenu,
    QMessageBox,
    QTreeView,
    QWidget,
)

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.ui.components.playlist.interfaces import (
    IPlatformClient,
    IPlaylistItem,
    ITrackItem,
    PlatformCapability,
)
from selecta.ui.components.playlist.platform.base_platform_provider import BasePlatformDataProvider
from selecta.ui.components.playlist.platform.discogs.discogs_playlist_item import DiscogsPlaylistItem
from selecta.ui.components.playlist.platform.discogs.discogs_track_item import DiscogsTrackItem
from selecta.ui.dialogs import ImportExportPlaylistDialog


# Define a Protocol that matches the client interface needed for the BasePlatformDataProvider
@runtime_checkable
class PlatformClientProtocol(Protocol):
    """Protocol for platform clients that can be used by BasePlatformDataProvider."""

    def is_authenticated(self) -> bool: ...  # noqa: D102
    def authenticate(self) -> bool: ...  # noqa: D102
    def get_capabilities(self) -> list[PlatformCapability]: ...  # noqa: D102


# Type variable for DiscogsClient
TDiscogsClient = TypeVar("TDiscogsClient", bound=DiscogsClient)


class DiscogsDataProvider(BasePlatformDataProvider):
    """Data provider for Discogs collection and wantlist.

    This provider implements access to the Discogs platform, allowing
    users to browse and import vinyl collection and wantlist data.
    """

    def __init__(self, client: DiscogsClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Discogs playlist data provider.

        Args:
            client: Optional DiscogsClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Discogs client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("discogs", settings_repo)
            if not isinstance(client_instance, DiscogsClient):
                raise ValueError("Could not create Discogs client")
            self.client = client_instance
        else:
            self.client = client

        # DiscogsClient already implements IPlatformClient methods, but
        # we need to cast it to satisfy the type checker
        platform_client = cast(IPlatformClient, self.client)

        # Initialize the base provider
        super().__init__(client=platform_client, cache_timeout=cache_timeout)

        # Additional cache keys specific to Discogs
        self._collection_cache_key = "discogs_collection"
        self._wantlist_cache_key = "discogs_wantlist"

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Discogs"

    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform provider.

        Returns:
            List of supported capabilities
        """
        return [
            PlatformCapability.IMPORT_PLAYLISTS,
            PlatformCapability.IMPORT_TRACKS,
            PlatformCapability.SYNC_PLAYLISTS,
        ]

    def is_connected(self) -> bool:
        """Check if the provider is connected to its platform.

        Returns:
            True if connected, False otherwise
        """
        if self.client is None:
            return False
        return self.client.is_authenticated()

    def connect_platform(self, parent: QWidget | None = None) -> bool:
        """Connect to the Discogs platform.

        Args:
            parent: Parent widget for dialogs

        Returns:
            True if successfully connected
        """
        if self.client is None:
            if parent:
                QMessageBox.critical(
                    parent,
                    "Connection Error",
                    "Discogs client not initialized.",
                )
            return False

        # Try to authenticate
        try:
            if self.client.is_authenticated():
                # Already authenticated
                return True

            # Start the authentication flow
            result = self.client.authenticate()

            if result:
                # Refresh UI after successful authentication
                self.refresh()
                return True
            else:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Authentication Failed",
                        "Failed to authenticate with Discogs.",
                    )
                return False
        except Exception as e:
            logger.exception(f"Error connecting to Discogs: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Connection Error",
                    f"Error connecting to Discogs: {str(e)}",
                )
            return False

    def _fetch_playlists(self) -> list[IPlaylistItem]:
        """Fetch 'playlists' from Discogs (collection and wantlist).

        Returns:
            List of playlist items
        """
        # Always create a fresh list of playlist items
        playlist_items = []

        # Create root folder
        root_folder = DiscogsPlaylistItem(
            name="Discogs",
            item_id="discogs_root",
            is_folder_flag=True,
            track_count=0,
        )
        playlist_items.append(root_folder)

        # Check authentication only once
        if not self.is_connected():
            # Still return the root folder even when not authenticated
            return playlist_items

        # Get collection count from cache or API
        collection_count = 0
        try:
            if self.cache.has_valid(self._collection_cache_key):
                collection = self.cache.get(self._collection_cache_key, [])
                collection_count = len(collection)
            else:
                collection = self.client.get_collection()
                collection_count = len(collection)
                # Cache the collection data
                self.cache.set(self._collection_cache_key, collection)

            collection_item = DiscogsPlaylistItem(
                name=f"Collection ({collection_count} items)",
                item_id="collection",
                parent_id="discogs_root",
                is_folder_flag=False,
                track_count=collection_count,
                list_type="collection",
            )
            playlist_items.append(collection_item)
        except Exception as e:
            logger.error(f"Error getting Discogs collection: {e}")
            # Add an empty collection placeholder
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Collection (error)",
                    item_id="collection",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="collection",
                )
            )

        # Get wantlist count from cache or API
        wantlist_count = 0
        try:
            if self.cache.has_valid(self._wantlist_cache_key):
                wantlist = self.cache.get(self._wantlist_cache_key, [])
                wantlist_count = len(wantlist)
            else:
                wantlist = self.client.get_wantlist()
                wantlist_count = len(wantlist)
                # Cache the wantlist data
                self.cache.set(self._wantlist_cache_key, wantlist)

            wantlist_item = DiscogsPlaylistItem(
                name=f"Wantlist ({wantlist_count} items)",
                item_id="wantlist",
                parent_id="discogs_root",
                is_folder_flag=False,
                track_count=wantlist_count,
                list_type="wantlist",
            )
            playlist_items.append(wantlist_item)
        except Exception as e:
            logger.error(f"Error getting Discogs wantlist: {e}")
            # Add an empty wantlist placeholder
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Wantlist (error)",
                    item_id="wantlist",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="wantlist",
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[ITrackItem]:
        """Fetch tracks for a 'playlist' (collection or wantlist).

        Args:
            playlist_id: ID of the 'playlist' ('collection' or 'wantlist')

        Returns:
            List of track items
        """
        # Root folder has no tracks
        if playlist_id == "discogs_root":
            return []

        if not self.is_connected():
            return []

        track_items = []

        try:
            # Get tracks based on playlist type
            if playlist_id == "collection":
                # Get collection items from cache or API
                collection = self.cache.get_or_set(self._collection_cache_key, lambda: self.client.get_collection())

                for i, vinyl in enumerate(collection):
                    release = vinyl.release
                    track_items.append(
                        DiscogsTrackItem(
                            track_id=f"collection_{release.id}_{i}",  # Create unique ID
                            title=release.title,
                            artist=release.artist,
                            album=release.title,  # Discogs releases are albums
                            year=release.year,
                            genre=release.genre[0] if release.genre else None,
                            format=", ".join(release.format) if release.format else None,
                            label=release.label,
                            catno=release.catno,
                            country=release.country,
                            added_at=vinyl.date_added,
                            discogs_id=release.id,
                            discogs_uri=release.uri,
                            thumb_url=release.thumb_url,
                            cover_url=release.cover_url,
                            is_owned=True,
                            notes=vinyl.notes,
                        )
                    )
            elif playlist_id == "wantlist":
                # Get wantlist items from cache or API
                wantlist = self.cache.get_or_set(self._wantlist_cache_key, lambda: self.client.get_wantlist())

                for i, vinyl in enumerate(wantlist):
                    release = vinyl.release
                    track_items.append(
                        DiscogsTrackItem(
                            track_id=f"wantlist_{release.id}_{i}",  # Create unique ID
                            title=release.title,
                            artist=release.artist,
                            album=release.title,  # Discogs releases are albums
                            year=release.year,
                            genre=release.genre[0] if release.genre else None,
                            format=", ".join(release.format) if release.format else None,
                            label=release.label,
                            catno=release.catno,
                            country=release.country,
                            added_at=vinyl.date_added,
                            discogs_id=release.id,
                            discogs_uri=release.uri,
                            thumb_url=release.thumb_url,
                            cover_url=release.cover_url,
                            is_wanted=True,
                            notes=vinyl.notes,
                        )
                    )
        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")

        return track_items

    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a Discogs playlist (collection or wantlist).

        Args:
            tree_view: The tree view
            position: Position where the context menu was requested
            parent: Parent widget for dialogs
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

        # Add import action (only for collection/wantlist, not the root)
        if playlist_item.item_id in ["collection", "wantlist"]:
            import_action = menu.addAction("Import to Local Library")
            # Since menu.addAction() should not return None, this is safe
            # but we verify it just to be type-safe
            if import_action is not None:
                import_action.triggered.connect(
                    lambda: self.import_playlist(playlist_item.item_id, self._get_parent_widget(tree_view, parent))
                )

        # Show the menu at the cursor position
        viewport = tree_view.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(position))

    def _get_parent_widget(self, default_widget: QWidget, parent: QWidget | None = None) -> QWidget:
        """Get the parent widget for dialog operations.

        Args:
            default_widget: Default widget to use if parent is None
            parent: Optional parent widget

        Returns:
            Parent widget to use for dialogs
        """
        return parent if parent is not None else default_widget

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a Discogs collection or wantlist to the local library.

        Args:
            playlist_id: ID of the playlist to import (collection or wantlist)
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with Discogs to import playlists.",
                )
            return False

        # Check if the playlist_id is valid (collection or wantlist)
        if playlist_id not in ["collection", "wantlist"]:
            if parent:
                QMessageBox.critical(
                    parent,
                    "Import Error",
                    "Invalid Discogs list type. Must be 'collection' or 'wantlist'.",
                )
            return False

        try:
            # Show the import dialog to let the user set the playlist name
            default_name = f"Discogs {playlist_id.capitalize()}"
            dialog = ImportExportPlaylistDialog(parent, mode="import", platform="discogs", default_name=default_name)

            if dialog.exec() != ImportExportPlaylistDialog.DialogCode.Accepted:
                return False

            dialog_values = dialog.get_values()
            playlist_name = dialog_values["name"]

            # Create a sync manager for handling the import
            if self.client is None:
                raise ValueError("No Discogs client available")

            # Cast client to AbstractPlatform to satisfy type checking
            platform_client = cast(AbstractPlatform, self.client)
            sync_manager = PlatformSyncManager(platform_client)

            # Check if playlist already exists
            playlist_repo = PlaylistRepository()
            existing_playlist = playlist_repo.get_by_platform_id("discogs", playlist_id)

            if existing_playlist:
                if parent:
                    response = QMessageBox.question(
                        parent,
                        "Playlist Already Exists",
                        f"A playlist from Discogs with this ID already exists: "
                        f"'{existing_playlist.name}'. "
                        "Do you want to update it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if response != QMessageBox.StandardButton.Yes:
                        return False

                # Use sync manager to update the existing playlist
                try:
                    # Sync the playlist with existing one
                    # The sync_playlist method can return either a tuple or a SyncResult
                    # We need to handle both cases
                    sync_result = sync_manager.sync_playlist(existing_playlist.id)

                    # If it's a tuple, unpack it
                    if isinstance(sync_result, tuple) and len(sync_result) == 2:
                        tracks_added, _ = sync_result  # We only need tracks_added, ignore the second value
                    else:
                        # If it's a SyncResult, extract the value we need
                        tracks_added = getattr(sync_result, "library_additions_applied", 0)

                    # Update name if changed
                    if playlist_name != existing_playlist.name:
                        playlist_repo.update(existing_playlist.id, {"name": playlist_name})

                    if parent:
                        QMessageBox.information(
                            parent,
                            "Sync Successful",
                            f"Playlist '{playlist_name}' synced successfully.\n"
                            f"{tracks_added} new records added from Discogs.",
                        )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error syncing Discogs playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Sync Error", f"Failed to sync playlist: {str(e)}")
                    return False
            else:
                # Import new playlist using the sync manager
                try:
                    # Import the playlist
                    local_playlist, local_tracks = sync_manager.import_playlist(playlist_id)

                    # Update name if different from what was imported
                    if playlist_name != local_playlist.name:
                        playlist_repo.update(local_playlist.id, {"name": playlist_name})

                    if parent:
                        QMessageBox.information(
                            parent,
                            "Import Successful",
                            f"Playlist '{playlist_name}' imported successfully.\n{len(local_tracks)} records imported.",
                        )

                    # Refresh the UI to show the imported playlist
                    self.notify_refresh_needed()
                    return True
                except Exception as e:
                    logger.exception(f"Error importing Discogs playlist: {e}")
                    if parent:
                        QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
                    return False

        except Exception as e:
            logger.exception(f"Error importing Discogs playlist: {e}")
            if parent:
                QMessageBox.critical(parent, "Import Error", f"Failed to import playlist: {str(e)}")
            return False

    def export_playlist(self, playlist_id: str, target_platform: str, parent: QWidget | None = None) -> bool:
        """Export a library playlist to Discogs.

        This method intentionally does not support exporting full playlists to Discogs,
        as Discogs is not a playlist platform but rather a vinyl collection manager.
        Individual tracks can be added to the wantlist or collection through track operations.

        Args:
            playlist_id: Library playlist ID
            target_platform: Target platform name
            parent: Parent widget for dialogs

        Returns:
            False as Discogs doesn't support playlist export
        """
        if parent:
            QMessageBox.information(
                parent,
                "Discogs Operation",
                "Discogs doesn't support direct playlist exports. Instead, use track-level operations "
                "to mark individual tracks as part of your vinyl collection or wantlist.",
            )
        return False

    def sync_playlist(self, playlist_id: str, parent: QWidget | None = None) -> bool:
        """Refresh Discogs collection or wantlist data.

        This method only updates the library with the latest data from Discogs.
        Discogs is used for tracking vinyl ownership and wanted items rather than
        traditional playlist synchronization.

        Args:
            playlist_id: Library playlist ID
            parent: Parent widget for dialogs

        Returns:
            True if successfully refreshed
        """
        if not self.is_connected():
            if parent:
                QMessageBox.warning(
                    parent,
                    "Authentication Error",
                    "You must be authenticated with Discogs to update collection or wantlist data.",
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

            # Check if this playlist is linked to Discogs
            platform_id = source_playlist.get_platform_id("discogs")

            if not platform_id:
                if parent:
                    QMessageBox.warning(
                        parent,
                        "Not Linked to Discogs",
                        f"Playlist '{source_playlist.name}' is not linked to Discogs. "
                        "Please import your Discogs collection or wantlist first.",
                    )
                return False

            # Create a sync manager
            if self.client is None:
                raise ValueError("No Discogs client available")

            # Cast client to AbstractPlatform to satisfy type checking
            platform_client = cast(AbstractPlatform, self.client)
            sync_manager = PlatformSyncManager(platform_client)

            # Show progress information
            if parent:
                QMessageBox.information(
                    parent,
                    "Updating Discogs Data",
                    "Fetching the latest data from Discogs. This may take a moment...",
                )

            # Sync the Discogs data (only one-way, from Discogs to library)
            # Handle the sync result which can be either a tuple or SyncResult
            sync_result = sync_manager.sync_playlist(local_playlist_id=int(playlist_id))

            # Extract the number of tracks added
            if isinstance(sync_result, tuple) and len(sync_result) == 2:
                tracks_added_to_library, _ = sync_result
            else:
                # If it's a SyncResult, extract the value we need
                tracks_added_to_library = getattr(sync_result, "library_additions_applied", 0)

            # Show success message
            if platform_id == "collection":
                action_message = "vinyl collection"
            elif platform_id == "wantlist":
                action_message = "wantlist"
            else:
                action_message = "Discogs data"

            if parent:
                QMessageBox.information(
                    parent,
                    "Update Successful",
                    f"Successfully updated {action_message} data.\n"
                    f"Added {tracks_added_to_library} new records to library from Discogs.",
                )

            # Refresh playlists
            self.notify_refresh_needed()

            return True
        except Exception as e:
            logger.exception(f"Error updating Discogs data: {e}")
            if parent:
                QMessageBox.critical(parent, "Update Failed", f"Failed to update Discogs data: {str(e)}")
            return False
