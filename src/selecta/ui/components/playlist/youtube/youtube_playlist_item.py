"""YouTube playlist item for display in the UI."""

from PyQt6.QtGui import QIcon

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class YouTubePlaylistItem(PlaylistItem):
    """Represents a YouTube playlist in the UI."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        track_count: int = 0,
        thumbnail_url: str | None = None,
    ) -> None:
        """Initialize a YouTube playlist item.

        Args:
            id: YouTube playlist ID
            title: Playlist title
            description: Playlist description
            track_count: Number of tracks in the playlist
            thumbnail_url: URL of the playlist thumbnail
        """
        super().__init__(title, id)
        self._description = description
        self._track_count = track_count
        self._platform = "youtube"
        self._thumbnail_url = thumbnail_url
        
        # Make track_count accessible as an attribute to match the interface expected by PlaylistTreeModel
        self.track_count = track_count
        self.description = description

    @property
    def thumbnail_url(self) -> str | None:
        """Get the thumbnail URL for this playlist.

        Returns:
            Thumbnail URL or None if not available
        """
        return self._thumbnail_url
        
    def get_icon(self) -> QIcon:
        """Get the icon for this playlist.
        
        Returns:
            YouTube playlist icon
        """
        # Use a generic audio icon since we don't have YouTube-specific icon yet
        return QIcon.fromTheme("audio-x-generic")
        
    def is_folder(self) -> bool:
        """Check if this item is a folder.
        
        Returns:
            False as YouTube playlists are not folders
        """
        return False
