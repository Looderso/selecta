from typing import Any

from PyQt6.QtGui import QIcon

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.playlist_item import PlaylistItem


class LibraryPlaylistItem(PlaylistItem):
    """Implementation of PlaylistItem for library database playlists."""

    # Cache icons for better performance
    _platform_icons: dict[str, QIcon] = {}

    @classmethod
    def _get_platform_icon(cls, platform_name: str) -> QIcon:
        """Get cached platform icon.

        Args:
            platform_name: Name of the platform ('spotify', 'rekordbox', etc.)

        Returns:
            QIcon for the platform
        """
        if platform_name not in cls._platform_icons:
            icon_path = get_resource_path(f"icons/1x/{platform_name}.png")
            cls._platform_icons[platform_name] = QIcon(str(icon_path))
        return cls._platform_icons[platform_name]

    def __init__(
        self,
        name: str,
        item_id: Any,
        parent_id: Any | None = None,
        is_folder_flag: bool = False,
        description: str | None = None,
        track_count: int = 0,
        source_platform: str | None = None,
        platform_id: str | None = None,
        is_collection: bool = False,
        synced_platforms: list[str] | None = None,
    ):
        """Initialize a library playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            description: Optional description of the playlist
            track_count: Number of tracks in the playlist
            source_platform: The source platform if imported ('spotify', 'rekordbox', etc.)
            platform_id: The platform-specific ID if imported
            is_collection: Whether this is the special Collection playlist
            synced_platforms: List of platforms this playlist is synced with
        """
        super().__init__(name, item_id, parent_id)
        self._is_folder = is_folder_flag
        self.description = description
        self.track_count = track_count
        self.source_platform = source_platform
        self.platform_id = platform_id
        self.is_collection = is_collection
        self.synced_platforms = synced_platforms or []

        # If this was imported from a platform, add that platform to synced_platforms
        if self.source_platform and self.source_platform not in self.synced_platforms:
            self.synced_platforms.append(self.source_platform)

    def get_icon(self) -> QIcon:
        """Get the primary icon for this item.

        Returns:
            QIcon appropriate for this type of item, or empty QIcon for alignment
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        elif self.is_collection:
            # Only the Collection playlist should have a left icon
            return self._get_platform_icon("collection")
        else:
            # All other playlists should not have a left icon
            # This ensures alignment of all playlist names
            return QIcon()

    def get_platform_icons(self) -> list[str]:
        """Get list of platform names for displaying sync icons.

        Returns:
            List of platform names that this playlist is synced with
        """
        return self.synced_platforms

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        return self._is_folder

    def is_imported(self) -> bool:
        """Check if this playlist was imported from an external platform.

        Returns:
            True if imported, False if local
        """
        return self.source_platform is not None and self.platform_id is not None

    def add_synced_platform(self, platform: str) -> None:
        """Add a platform to the list of synced platforms.

        Args:
            platform: Platform name to add ('spotify', 'rekordbox', etc.)
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
