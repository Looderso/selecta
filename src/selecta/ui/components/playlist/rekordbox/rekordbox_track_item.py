# src/selecta/ui/components/playlist/rekordbox/rekordbox_track_item.py
from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.track_item import TrackItem


class RekordboxTrackItem(TrackItem):
    """Implementation of TrackItem for Rekordbox tracks."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        album: str | None = None,
        duration_ms: int | None = None,
        added_at: datetime | None = None,
        bpm: float | None = None,
        key: str | None = None,
        path: str | None = None,
        rating: int | None = None,
        created_at: datetime | None = None,
    ):
        """Initialize a Rekordbox track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            album: Album name
            duration_ms: Duration in milliseconds
            added_at: When the track was added to the playlist
            bpm: Beats per minute
            key: Musical key
            path: File path to the track
            rating: Track rating (0-5)
            created_at: When the track was created
        """
        super().__init__(track_id, title, artist, duration_ms, album, added_at)
        self.bpm = bpm
        self.key = key
        self.path = path
        self.rating = rating
        self.created_at = created_at

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Format BPM value
        bpm_str = f"{self.bpm:.1f}" if self.bpm is not None else ""

        # Format rating (convert to stars)
        rating_str = "★" * self.rating if self.rating else ""

        return {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "bpm": bpm_str,
            "key": self.key or "",
            "rating": rating_str,
            "path": self.path or "",
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
            # Add platform-specific fields
            "platforms": ["rekordbox"],  # For platform icons display
            "platforms_tooltip": "Available in Rekordbox",
        }
