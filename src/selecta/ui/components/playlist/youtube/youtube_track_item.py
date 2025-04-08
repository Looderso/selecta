"""YouTube track (video) item for display in the UI."""

from selecta.ui.components.playlist.track_item import TrackItem


class YouTubeTrackItem(TrackItem):
    """Represents a YouTube video in the UI."""

    def __init__(
        self,
        id: str,
        title: str,
        artist: str,
        duration: int = 0,
        thumbnail_url: str | None = None,
    ) -> None:
        """Initialize a YouTube track item.

        Args:
            id: YouTube video ID
            title: Video title
            artist: Channel name
            duration: Duration in seconds
            thumbnail_url: URL of the video thumbnail
        """
        super().__init__(id, title, artist, "", 0, duration)
        self._platform = "youtube"
        self._thumbnail_url = thumbnail_url

    @property
    def thumbnail_url(self) -> str | None:
        """Get the thumbnail URL for this video.

        Returns:
            Thumbnail URL or None if not available
        """
        return self._thumbnail_url