"""Implementation of PlaylistItem for library database playlists.

This module provides the LibraryPlaylistItem class which extends the BasePlaylistItem
to provide playlist functionality specific to the local library database.
"""

from typing import Any

from PyQt6.QtGui import QIcon

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.base_items import BasePlaylistItem


class LibraryPlaylistItem(BasePlaylistItem):
    """Implementation of PlaylistItem for library database playlists."""

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
            source_platform: The source platform if imported
            platform_id: The platform-specific ID if imported
            is_collection: Whether this is the special Collection playlist
            synced_platforms: List of platforms this playlist is synced with
        """
        synced_platforms_list = synced_platforms or []

        # If this was imported from a platform, add that platform to synced_platforms
        if source_platform and source_platform not in synced_platforms_list:
            synced_platforms_list.append(source_platform)

        super().__init__(
            name=name,
            item_id=item_id,
            parent_id=parent_id,
            is_folder_flag=is_folder_flag,
            track_count=track_count,
            synced_platforms=synced_platforms_list,
        )

        self.description = description
        self.source_platform = source_platform
        self.platform_id = platform_id
        self.is_collection = is_collection

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        elif self.is_collection:
            # Special icon for the Collection playlist
            icon_path = get_resource_path("icons/1x/collection.png")
            return QIcon(str(icon_path))
        else:
            # Regular playlist icon
            return QIcon.fromTheme("audio-x-generic")

    def is_imported(self) -> bool:
        """Check if this playlist was imported from an external platform.

        Returns:
            True if imported, False if local
        """
        return self.source_platform is not None and self.platform_id is not None
