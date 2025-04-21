"""YouTube playlist item implementation.

This module provides the implementation of the playlist item for YouTube playlists,
extending the base playlist item with YouTube-specific functionality.
"""

from PyQt6.QtGui import QIcon

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.base_items import BasePlaylistItem


class YouTubePlaylistItem(BasePlaylistItem):
    """Implementation of PlaylistItem for YouTube playlists."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        track_count: int = 0,
        thumbnail_url: str | None = None,
        is_imported: bool = False,
    ):
        """Initialize a YouTube playlist item.

        Args:
            id: YouTube playlist ID
            title: Playlist title
            description: Playlist description
            track_count: Number of tracks in the playlist
            thumbnail_url: URL of the playlist thumbnail
            is_imported: Whether this playlist has been imported to the library
        """
        # If is_imported is True, add "library" to synced_platforms list
        synced_platforms = ["library"] if is_imported else []

        # Initialize with base class
        super().__init__(
            name=title,
            item_id=id,
            parent_id=None,  # YouTube doesn't have parent playlists
            is_folder_flag=False,  # YouTube doesn't have folders
            track_count=track_count,
            synced_platforms=synced_platforms,
        )

        # Store YouTube-specific attributes
        self.description = description
        self.thumbnail_url = thumbnail_url
        self._imported_flag = is_imported

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        # Use the YouTube icon
        icon_path = get_resource_path("icons/1x/youtube.png")
        return QIcon(str(icon_path))

    def is_imported(self) -> bool:
        """Check if this playlist has been imported to the library.

        Returns:
            True if imported, False otherwise
        """
        return self._imported_flag
