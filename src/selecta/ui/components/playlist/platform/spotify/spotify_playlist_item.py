"""Spotify playlist item implementation.

This module provides the implementation of the playlist item for Spotify playlists,
extending the base playlist item with Spotify-specific functionality.
"""

from typing import Any

from PyQt6.QtGui import QIcon

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.base_items import BasePlaylistItem


class SpotifyPlaylistItem(BasePlaylistItem):
    """Implementation of PlaylistItem for Spotify playlists."""

    def __init__(
        self,
        name: str,
        item_id: Any,
        owner: str,
        description: str = "",
        is_collaborative: bool = False,
        is_public: bool = True,
        track_count: int = 0,
        images: list[dict] | None = None,
        is_imported: bool = False,
    ):
        """Initialize a Spotify playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            owner: Owner of the playlist
            description: Playlist description
            is_collaborative: Whether this playlist is collaborative
            is_public: Whether this playlist is public
            track_count: Number of tracks in the playlist
            images: List of playlist cover images
            is_imported: Whether this playlist has been imported to the library
        """
        # Spotify doesn't support folders, so parent_id is always None
        # If playlist is imported, add "library" to synced_platforms list
        synced_platforms = ["library"] if is_imported else []

        super().__init__(
            name=name,
            item_id=item_id,
            parent_id=None,  # Spotify doesn't have parent playlists
            is_folder_flag=False,  # Spotify doesn't have folders
            track_count=track_count,
            synced_platforms=synced_platforms,
        )

        self.owner = owner
        self.description = description
        self.is_collaborative = is_collaborative
        self.is_public = is_public
        self.images = images or []
        self._imported_flag = is_imported  # Use a different name for the attribute

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        # Use Spotify icon
        icon_path = get_resource_path("icons/1x/spotify.png")
        return QIcon(str(icon_path))

    def is_imported(self) -> bool:
        """Check if this playlist has been imported to the library.

        Returns:
            True if imported, False otherwise
        """
        return self._imported_flag

    def get_image_url(self) -> str | None:
        """Get the URL of the playlist cover image.

        Returns:
            The URL of the image, or None if no image is available
        """
        if not self.images:
            return None

        # Get the smallest image that's at least 64px
        for image in sorted(self.images, key=lambda x: x.get("width", 0)):
            if image.get("width", 0) >= 64:
                return image.get("url")

        # If no suitable image found, return the first one
        return self.images[0].get("url") if self.images else None
