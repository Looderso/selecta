"""YouTube playlist item for display in the UI."""

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
        super().__init__(id, title, description, track_count)
        self._platform = "youtube"
        self._thumbnail_url = thumbnail_url

    @property
    def thumbnail_url(self) -> str | None:
        """Get the thumbnail URL for this playlist.

        Returns:
            Thumbnail URL or None if not available
        """
        return self._thumbnail_url
