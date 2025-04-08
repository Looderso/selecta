"""YouTube track (video) item for display in the UI."""

from typing import Any

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
        # Convert duration from seconds to milliseconds for the parent class
        duration_ms = duration * 1000 if duration else 0
        super().__init__(id, title, artist, duration_ms, "")
        self._platform = "youtube"
        self._thumbnail_url = thumbnail_url
        
        # Store the YouTube-specific data
        self.video_id = id
        self.channel = artist
        self.duration_seconds = duration

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
        # Prepare image data for the track
        has_db_image = False
        if self.has_image:
            has_db_image = True
            
        # YouTube video URL
        video_url = f"https://www.youtube.com/watch?v={self.video_id}" if self.video_id else ""

        return {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": "",  # YouTube videos don't have albums
            "duration": self.duration_str,
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            # Add platform-specific fields
            "platforms": ["youtube"],  # For platform icons display
            "platforms_tooltip": "Available on YouTube",
            # Include the YouTube-specific fields
            "video_id": self.video_id,
            "video_url": video_url,
            "channel": self.channel,
            "thumbnail_url": self.thumbnail_url,
            # Add database image fields
            "has_db_image": has_db_image,
            "album_id": self.album_id,
        }
