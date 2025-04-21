"""YouTube track (video) item for display in the UI."""

from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.base_items import BaseTrackItem


class YouTubeTrackItem(BaseTrackItem):
    """Represents a YouTube video in the UI."""

    def __init__(
        self,
        id: str,
        title: str,
        artist: str,
        duration: int = 0,
        thumbnail_url: str | None = None,
        added_at: datetime | None = None,
        album_id: int | None = None,
        has_image: bool = False,
    ) -> None:
        """Initialize a YouTube track item.

        Args:
            id: YouTube video ID
            title: Video title
            artist: Channel name
            duration: Duration in seconds
            thumbnail_url: URL of the video thumbnail
            added_at: When the track was added
            album_id: ID of the album in the database
            has_image: Whether this track has an image
        """
        # Convert duration from seconds to milliseconds for the parent class
        duration_ms = duration * 1000 if duration else 0

        # Initialize the base class
        super().__init__(
            track_id=id,
            title=title,
            artist=artist,
            duration_ms=duration_ms,
            album=None,  # YouTube videos don't have albums
            added_at=added_at,
            album_id=album_id,
            has_image=has_image,
            platforms=["youtube"],
        )
        # Store the YouTube-specific data
        self.video_id = id
        self.channel = artist
        self.duration_seconds = duration
        self._thumbnail_url = thumbnail_url

    @property
    def thumbnail_url(self) -> str | None:
        """Get the thumbnail URL for this video.

        Returns:
            Thumbnail URL or None if not available
        """
        return self._thumbnail_url

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Check for cached data
        if hasattr(self, "_display_data_cache") and self._display_data_cache is not None:
            return self._display_data_cache

        # YouTube video URL
        video_url = f"https://www.youtube.com/watch?v={self.video_id}" if self.video_id else ""

        # Start with the base class data then add YouTube-specific fields
        display_data = {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": "",  # YouTube videos don't have albums
            "duration": self.duration_str,
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            # Platform information
            "platforms": self.platforms,
            "platforms_tooltip": "Available on YouTube",
            # YouTube-specific fields
            "video_id": self.video_id,
            "video_url": video_url,
            "channel": self.channel,
            "thumbnail_url": self.thumbnail_url,
            # Album image fields
            "has_db_image": self.has_image,
            "album_id": self.album_id,
        }

        # Cache the display data
        self._display_data_cache = display_data

        return display_data
