# src/selecta/ui/components/playlist/discogs/discogs_playlist_item.py
from typing import Any, Literal

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class DiscogsPlaylistItem(PlaylistItem):
    """Implementation of PlaylistItem for Discogs collection and wantlist."""

    def __init__(
        self,
        name: str,
        item_id: Any,
        parent_id: Any | None = None,
        is_folder_flag: bool = False,
        track_count: int = 0,
        list_type: Literal["collection", "wantlist", "root"] | None = None,
    ):
        """Initialize a Discogs playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            track_count: Number of tracks in the playlist
            list_type: Type of list ('collection', 'wantlist', or 'root')
        """
        super().__init__(name, item_id, parent_id)
        self._is_folder = is_folder_flag
        self.track_count = track_count
        self.list_type = list_type

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        elif self.list_type == "collection":
            # Use a vinyl icon for collection if available
            return QIcon.fromTheme("media-optical")
        elif self.list_type == "wantlist":
            # Use a wishlist icon for wantlist if available
            return QIcon.fromTheme("emblem-favorite")
        else:
            # Default icon
            return QIcon.fromTheme("audio-x-generic")

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        return self._is_folder
