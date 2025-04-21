"""Rekordbox playlist item implementation.

This module provides the implementation of the playlist item for Rekordbox playlists,
extending the base playlist item with Rekordbox-specific functionality.
"""

from typing import Any

from PyQt6.QtGui import QIcon

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.base_items import BasePlaylistItem


class RekordboxPlaylistItem(BasePlaylistItem):
    """Implementation of PlaylistItem for Rekordbox playlists."""

    def __init__(
        self,
        name: str,
        item_id: Any,
        parent_id: Any | None = None,
        is_folder_flag: bool = False,
        track_count: int = 0,
        is_imported: bool = False,
    ):
        """Initialize a Rekordbox playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            track_count: Number of tracks in the playlist
            is_imported: Whether this playlist has been imported to the library
        """
        # If is_imported is True, add "library" to synced_platforms list
        synced_platforms = ["library"] if is_imported else []

        super().__init__(
            name=name,
            item_id=item_id,
            parent_id=parent_id,
            is_folder_flag=is_folder_flag,
            track_count=track_count,
            synced_platforms=synced_platforms,
        )

        self._imported_flag = is_imported

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        else:
            # Use the Rekordbox icon
            icon_path = get_resource_path("icons/1x/rekordbox.png")
            return QIcon(str(icon_path))

    def is_imported(self) -> bool:
        """Check if this playlist has been imported to the library.

        Returns:
            True if imported, False otherwise
        """
        return self._imported_flag
