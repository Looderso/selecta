from typing import Any

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class RekordboxPlaylistItem(PlaylistItem):
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
        super().__init__(name, item_id, parent_id)
        self._is_folder = is_folder_flag
        self.track_count = track_count
        self.is_imported = is_imported

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        else:
            # Use the Rekordbox icon
            return QIcon("resources/icons/rekordbox.png")

    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        return self._is_folder

    def get_platform_icons(self) -> list[str]:
        """Get list of platform names for displaying sync icons.

        For Rekordbox playlists, we only return "library" if the playlist
        has been imported to the local library.

        Returns:
            List of platform names that this playlist is synced with
        """
        if self.is_imported:
            return ["library"]
        return []
