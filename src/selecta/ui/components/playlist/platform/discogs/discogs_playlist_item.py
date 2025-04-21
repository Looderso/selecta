# src/selecta/ui/components/playlist/discogs/discogs_playlist_item.py
from typing import Any, Literal

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.base_items import BasePlaylistItem


class DiscogsPlaylistItem(BasePlaylistItem):
    """Implementation of PlaylistItem for Discogs collection and wantlist."""

    def __init__(
        self,
        name: str,
        item_id: Any,
        parent_id: Any | None = None,
        is_folder_flag: bool = False,
        track_count: int = 0,
        list_type: Literal["collection", "wantlist", "root"] | None = None,
        synced_platforms: list[str] | None = None,
    ):
        """Initialize a Discogs playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            track_count: Number of tracks in the playlist
            list_type: Type of list ('collection', 'wantlist', or 'root')
            synced_platforms: List of platforms this playlist is synced with
        """
        # Initialize with base class
        super().__init__(
            name=name,
            item_id=item_id,
            parent_id=parent_id,
            is_folder_flag=is_folder_flag,
            track_count=track_count,
            synced_platforms=synced_platforms,
        )
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
