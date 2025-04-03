# src/selecta/ui/components/playlist/playlist_data_provider.py
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from PyQt6.QtWidgets import QTreeView, QWidget

from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class PlaylistDataProvider(ABC):
    """Interface for providing playlist data to the playlist component."""

    def __init__(self):
        """Initialize the playlist data provider."""
        self._refresh_callbacks = []

    @abstractmethod
    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        pass

    @abstractmethod
    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any) -> None:
        """Show the context menu for a playlist item.

        Args:
            tree_view: The tree view
            position: Position where the context menu was requested
        """
        # This method should be implemented by subclasses
        pass

    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool:
        """Import a platform playlist to the local database.

        Args:
            playlist_id: ID of the playlist to import
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Default implementation does nothing
        # Platform-specific providers should override this
        return False

    def export_playlist(
        self, playlist_id: Any, target_platform: str, parent: QWidget | None = None
    ) -> bool:
        """Export a local playlist to a platform.

        Args:
            playlist_id: ID of the local playlist to export
            target_platform: Platform to export to ('spotify', 'rekordbox')
            parent: Parent widget for dialogs

        Returns:
            True if successful, False otherwise
        """
        # Default implementation does nothing
        # The local playlist provider should override this
        return False

    def register_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when data needs to be refreshed.

        Args:
            callback: Function to call when refresh is needed
        """
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.append(callback)

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
