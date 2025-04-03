from typing import Any

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class LocalPlaylistItem(PlaylistItem):
    """Implementation of PlaylistItem for local database playlists."""

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
    ):
        """Initialize a local playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
            is_folder_flag: Whether this item is a folder
            description: Optional description of the playlist
            track_count: Number of tracks in the playlist
            source_platform: The source platform if imported ('spotify', 'rekordbox', etc.)
            platform_id: The platform-specific ID if imported
        """
        super().__init__(name, item_id, parent_id)
        self._is_folder = is_folder_flag
        self.description = description
        self.track_count = track_count
        self.source_platform = source_platform
        self.platform_id = platform_id

    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        if self.is_folder():
            return QIcon.fromTheme("folder")
        elif self.source_platform == "spotify":
            # Use spotify icon if available, otherwise fallback
            return QIcon("resources/icons/spotify.png")
        elif self.source_platform == "rekordbox":
            # Use rekordbox icon if available, otherwise fallback
            return QIcon("resources/icons/rekordbox.png")
        else:
            return QIcon.fromTheme("audio-x-generic")

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
