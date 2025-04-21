"""Base implementations for playlist and track items.

This module provides standardized base classes for playlist and track items
that platform-specific implementations can extend to ensure consistency.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.interfaces import IPlaylistItem, ITrackItem


class BasePlaylistItem(IPlaylistItem, ABC):
    """Base implementation of a playlist item.

    This class provides common functionality for all playlist items
    across different platforms.
    """

    def __init__(
        self,
        name: str,
        item_id: Any,
        parent_id: Any | None = None,
        is_folder_flag: bool = False,
        track_count: int = 0,
        synced_platforms: list[str] | None = None,
    ):
        """Initialize a base playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            track_count: Number of tracks in the playlist
            synced_platforms: List of platforms this playlist is synced with
        """
        self.name = name
        self.item_id = item_id
        self.parent_id = parent_id
        self._is_folder = is_folder_flag
        self.track_count = track_count
        self.synced_platforms = synced_platforms or []
        self.children: list[BasePlaylistItem] = []

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        return self._is_folder

    def get_platform_icons(self) -> list[str]:
        """Get list of platform names for displaying sync icons.

        Returns:
            List of platform names that this playlist is synced with
        """
        return self.synced_platforms

    def add_child(self, child: "BasePlaylistItem") -> None:
        """Add a child item to this item.

        Args:
            child: The child item to add
        """
        self.children.append(child)

    def remove_child(self, child: "BasePlaylistItem") -> bool:
        """Remove a child item from this item.

        Args:
            child: The child item to remove

        Returns:
            True if the child was found and removed, False otherwise
        """
        if child in self.children:
            self.children.remove(child)
            return True
        return False

    def add_synced_platform(self, platform: str) -> None:
        """Add a platform to the list of synced platforms.

        Args:
            platform: Platform name to add
        """
        if platform not in self.synced_platforms:
            self.synced_platforms.append(platform)

    def remove_synced_platform(self, platform: str) -> None:
        """Remove a platform from the list of synced platforms.

        Args:
            platform: Platform name to remove
        """
        if platform in self.synced_platforms:
            self.synced_platforms.remove(platform)

    @abstractmethod
    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        pass


class PlatformIconsWidget(QWidget):
    """Widget to display platform icons horizontally."""

    def __init__(self, platforms: list[str], parent=None):
        """Initialize the platform icons widget.

        Args:
            platforms: List of platform names
            parent: Parent widget
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Load and add platform icons
        for platform in platforms:
            icon_path = get_resource_path(f"icons/{platform}.png")
            if icon_path.exists():
                label = QLabel()
                pixmap = QIcon(str(icon_path)).pixmap(16, 16)
                label.setPixmap(pixmap)
                layout.addWidget(label)


class BaseTrackItem(ITrackItem, ABC):
    """Base implementation of a track item.

    This class provides common functionality for all track items
    across different platforms.
    """

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        duration_ms: int | None = None,
        album: str | None = None,
        added_at: datetime | None = None,
        album_id: int | None = None,
        has_image: bool = False,
        platforms: list[str] | None = None,
    ):
        """Initialize a base track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            duration_ms: Duration in milliseconds
            album: Album name
            added_at: When the track was added to the playlist
            album_id: The database ID of the album, if available
            has_image: Whether this track has an image in the database
            platforms: List of platforms this track is available on
        """
        self.track_id = track_id
        self.title = title
        self.artist = artist
        self.duration_ms = duration_ms
        self.album = album
        self.added_at = added_at
        self.album_id = album_id
        self.has_image = has_image
        self.platforms = platforms or []
        self.quality = -1  # Default quality (-1 = not rated)

        # Cache for display data
        self._display_data_cache = None

    @property
    def duration_str(self) -> str:
        """Get a formatted string representation of the track duration.

        Returns:
            String representation of duration (MM:SS)
        """
        if not self.duration_ms:
            return "--:--"

        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def clear_display_cache(self) -> None:
        """Clear the display data cache to force regeneration."""
        if hasattr(self, "_display_data_cache"):
            delattr(self, "_display_data_cache")

    def set_platforms(self, platforms: list[str]) -> None:
        """Set the list of platforms this track is available on.

        Args:
            platforms: List of platform names
        """
        self.platforms = platforms.copy()
        self.clear_display_cache()

    def add_platform(self, platform: str) -> None:
        """Add a platform to the list of platforms this track is available on.

        Args:
            platform: Platform name to add
        """
        if platform not in self.platforms:
            self.platforms.append(platform)
            self.clear_display_cache()

    def remove_platform(self, platform: str) -> None:
        """Remove a platform from the list of platforms this track is available on.

        Args:
            platform: Platform name to remove
        """
        if platform in self.platforms:
            self.platforms.remove(platform)
            self.clear_display_cache()

    def get_platform_icons_widget(self) -> QWidget:
        """Get a widget displaying platform icons.

        Returns:
            Widget with platform icons
        """
        return PlatformIconsWidget(self.platforms)

    @abstractmethod
    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        pass
