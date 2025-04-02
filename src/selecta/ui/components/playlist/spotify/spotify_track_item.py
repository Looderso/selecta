# src/selecta/ui/components/playlist/spotify/spotify_track_item.py
from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.track_item import TrackItem


class SpotifyTrackItem(TrackItem):
    """Implementation of TrackItem for Spotify tracks."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        album: str | None = None,
        duration_ms: int | None = None,
        added_at: datetime | None = None,
        uri: str | None = None,
        popularity: int | None = None,
        explicit: bool = False,
        preview_url: str | None = None,
        album_id: int | None = None,
        has_image: bool = False,
    ):
        """Initialize a Spotify track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist(s)
            album: Album name
            duration_ms: Duration in milliseconds
            added_at: When the track was added to the playlist
            uri: Spotify URI for the track
            popularity: Popularity score (0-100)
            explicit: Whether the track has explicit content
            preview_url: URL to a 30-second preview
            album_id: The database ID of the album, if available
            has_image: Whether this track has an image in the database
        """
        super().__init__(track_id, title, artist, duration_ms, album, added_at, album_id, has_image)
        self.uri = uri
        self.popularity = popularity
        self.explicit = explicit
        self.preview_url = preview_url

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Format popularity as stars (0-5)
        popularity_stars = ""
        if self.popularity is not None:
            # Convert 0-100 to 0-5 stars
            stars = round(self.popularity / 20)
            popularity_stars = "★" * stars

        # Prepare image data for the track
        has_db_image = False
        if self.has_image:
            has_db_image = True

        return {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            "popularity": popularity_stars,
            "explicit": "[E]" if self.explicit else "",
            "preview": "🔊" if self.preview_url else "",
            "uri": self.uri or "",
            # Add platform-specific fields
            "platforms": ["spotify"],  # For platform icons display
            "platforms_tooltip": "Available on Spotify",
            # Include the full URI and preview URL for potential use
            "spotify_uri": self.uri,
            "preview_url": self.preview_url,
            # Add database image fields
            "has_db_image": has_db_image,
            "album_id": self.album_id,
        }
