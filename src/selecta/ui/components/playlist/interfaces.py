"""Base interfaces and protocols for the playlist component.

This module defines the core interfaces that all platform-specific implementations
must follow to ensure consistency across the application.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol, TypedDict

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QTreeView, QWidget


class PlatformCapability(Enum):
    """Capabilities that a platform might support."""

    IMPORT_PLAYLISTS = auto()
    EXPORT_PLAYLISTS = auto()
    SYNC_PLAYLISTS = auto()
    CREATE_PLAYLISTS = auto()
    DELETE_PLAYLISTS = auto()
    MODIFY_PLAYLISTS = auto()
    IMPORT_TRACKS = auto()
    EXPORT_TRACKS = auto()
    SEARCH = auto()
    FOLDERS = auto()
    COVER_ART = auto()
    RATINGS = auto()


class PlatformMetadata(TypedDict, total=False):
    """Type for platform-specific metadata."""

    platform: str
    platform_id: str
    uri: str | None
    url: str | None
    metadata: dict[str, Any]


class IPlaylistItem(Protocol):
    """Protocol defining the interface for a playlist item.

    This protocol ensures that all playlist items across platforms
    provide a consistent interface to the UI components.
    """

    name: str
    item_id: Any
    parent_id: Any | None
    track_count: int

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        ...

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        ...

    def get_platform_icons(self) -> list[str]:
        """Get list of platform names for displaying sync icons.

        Returns:
            List of platform names that this playlist is synced with
        """
        ...


class ITrackItem(Protocol):
    """Protocol defining the interface for a track item.

    This protocol ensures that all track items across platforms
    provide a consistent interface to the UI components.
    """

    track_id: Any
    title: str
    artist: str
    album: str | None
    duration_ms: int | None
    added_at: datetime | None
    has_image: bool

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        ...

    @property
    def duration_str(self) -> str:
        """Get a formatted string representation of the track duration.

        Returns:
            String representation of duration (MM:SS)
        """
        ...


class IPlatformClient(ABC):
    """Interface for platform clients.

    This abstract class defines the methods that all platform clients must implement
    to interact with their respective music platforms.
    """

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with the platform.

        Returns:
            True if authenticated, False otherwise
        """
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns:
            True if authentication was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[PlatformCapability]:
        """Get the capabilities supported by this platform.

        Returns:
            List of supported capabilities
        """
        pass


class IPlatformDataProvider(ABC):
    """Interface for platform data providers.

    This abstract class defines the methods that all platform data providers must
    implement to provide playlist and track data to the UI components.
    """

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
    def get_all_playlists(self) -> list[IPlaylistItem]:
        """Get all playlists from the platform.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: Any) -> list[ITrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass

    @abstractmethod
    def refresh(self) -> None:
        """Refresh all cached data and notify listeners."""
        pass

    @abstractmethod
    def refresh_playlist(self, playlist_id: Any) -> None:
        """Refresh a specific playlist's tracks.

        Args:
            playlist_id: ID of the playlist to refresh
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

    @abstractmethod
    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a platform playlist.

        Args:
            tree_view: The tree view
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        pass

    @abstractmethod
    def show_track_context_menu(self, table_view: Any, position: Any, parent: QWidget | None = None) -> None:
        """Show a context menu for a platform track.

        Args:
            table_view: The table view
            position: Position where to show the menu
            parent: Parent widget for dialogs
        """
        pass

    @abstractmethod
    def register_refresh_callback(self, callback: Callable) -> None:
        """Register a callback to be called when data needs to be refreshed.

        Args:
            callback: Function to call when refresh is needed
        """
        pass

    @abstractmethod
    def unregister_refresh_callback(self, callback: Callable) -> None:
        """Unregister a previously registered refresh callback.

        Args:
            callback: Function to remove from callbacks
        """
        pass

    @abstractmethod
    def notify_refresh_needed(self) -> None:
        """Notify all registered listeners that data needs to be refreshed."""
        pass


class ICacheManager(ABC):
    """Interface for cache managers.

    This abstract class defines the methods that a cache manager must implement
    to provide consistent caching across platform providers.
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.

        Args:
            key: Cache key
            default: Default value to return if key not found

        Returns:
            Cached value or default
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, timeout: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Optional timeout in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value from the cache.

        Args:
            key: Cache key to delete
        """
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def has_valid(self, key: str) -> bool:
        """Check if a key exists in the cache and is not expired.

        Args:
            key: Cache key

        Returns:
            True if key exists and is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_or_set(self, key: str, default_func: Callable, timeout: float | None = None) -> Any:
        """Get a value from the cache, or set it if not present.

        Args:
            key: Cache key
            default_func: Function to call to get default value if key not found
            timeout: Optional timeout in seconds

        Returns:
            Cached value or result of default_func
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all values from the cache."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Invalidate a cached value without removing it.

        This marks the value as expired but keeps it in the cache.

        Args:
            key: Cache key to invalidate
        """
        pass


class SyncOperation(Enum):
    """Types of sync operations."""

    IMPORT_FROM_PLATFORM = auto()  # Platform -> Local
    EXPORT_TO_PLATFORM = auto()  # Local -> Platform
    BIDIRECTIONAL = auto()  # Both directions


class SyncPreview(TypedDict):
    """Preview of sync operations to be performed."""

    platform_additions: list[dict[str, Any]]  # Tracks to add to platform
    platform_removals: list[dict[str, Any]]  # Tracks to remove from platform
    library_additions: list[dict[str, Any]]  # Tracks to add to library
    library_removals: list[dict[str, Any]]  # Tracks to remove from library


class SyncResult(TypedDict):
    """Results of sync operations."""

    success: bool
    platform_additions_applied: int
    platform_removals_applied: int
    library_additions_applied: int
    library_removals_applied: int
    total_changes_applied: int
    errors: list[str]


class ISyncManager(ABC):
    """Interface for sync managers.

    This abstract class defines the methods that all sync managers must implement
    to provide consistent sync functionality across platforms.
    """

    @abstractmethod
    def preview_sync(self, local_playlist_id: int) -> SyncPreview:
        """Get a preview of sync operations to be performed.

        Args:
            local_playlist_id: ID of the local playlist

        Returns:
            Preview of sync operations
        """
        pass

    @abstractmethod
    def apply_sync_changes(self, local_playlist_id: int, selected_changes: dict[str, list[Any]]) -> SyncResult:
        """Apply selected sync changes.

        Args:
            local_playlist_id: ID of the local playlist
            selected_changes: Dictionary of changes to apply

        Returns:
            Result of sync operations
        """
        pass

    @abstractmethod
    def sync_playlist(
        self,
        local_playlist_id: int,
        operation: SyncOperation = SyncOperation.BIDIRECTIONAL,
        apply_all_changes: bool = False,
    ) -> tuple[int, int] | SyncResult:
        """Sync a playlist between local and platform.

        Args:
            local_playlist_id: ID of the local playlist
            operation: Type of sync operation
            apply_all_changes: Whether to apply all changes automatically

        Returns:
            Tuple of (tracks_added, tracks_exported) if apply_all_changes is False,
            or SyncResult if apply_all_changes is True
        """
        pass

    @abstractmethod
    def import_playlist(
        self,
        platform_playlist_id: str,
        target_name: str | None = None,
        target_playlist_id: int | None = None,
    ) -> tuple[Any, list[Any]]:
        """Import a platform playlist to the local library.

        Args:
            platform_playlist_id: ID of the platform playlist
            target_name: Optional name for the imported playlist
            target_playlist_id: Optional ID of an existing playlist to import into

        Returns:
            Tuple of (local_playlist, imported_tracks)
        """
        pass

    @abstractmethod
    def export_playlist(
        self,
        local_playlist_id: int,
        platform_playlist_id: str | None = None,
        platform_playlist_name: str | None = None,
        parent_folder_id: Any | None = None,
    ) -> str:
        """Export a local playlist to the platform.

        Args:
            local_playlist_id: ID of the local playlist
            platform_playlist_id: Optional ID of an existing platform playlist
            platform_playlist_name: Optional name for the exported playlist
            parent_folder_id: Optional ID of a parent folder

        Returns:
            ID of the platform playlist
        """
        pass
