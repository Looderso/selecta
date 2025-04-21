# src/selecta/ui/components/playlist/spotify/spotify_playlist_item.py
from typing import Any

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class SpotifyPlaylistItem(PlaylistItem):
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
        super().__init__(name, item_id, None)  # Spotify doesn't have parent playlists
        self.owner = owner
        self.description = description
        self.is_collaborative = is_collaborative
        self.is_public = is_public
        self.track_count = track_count
        self.images = images or []
        self.is_imported = is_imported

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        # Use Spotify icon
        return QIcon("resources/icons/spotify.png")

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            Always False for Spotify playlists (Spotify doesn't have folders)
        """
        return False

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

    def get_platform_icons(self) -> list[str]:
        """Get list of platform names for displaying sync icons.

        For Spotify playlists, we only return "library" if the playlist
        has been imported to the local library.

        Returns:
            List of platform names that this playlist is synced with
        """
        if self.is_imported:
            return ["library"]
        return []
