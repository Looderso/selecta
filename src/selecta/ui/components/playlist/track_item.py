from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class TrackItem(ABC):
    """Base class for representing a track in a playlist."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        duration_ms: int | None = None,
        album: str | None = None,
        added_at: datetime | None = None,
    ):
        """Initialize a track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            duration_ms: Duration in milliseconds
            album: Album name
            added_at: When the track was added to the playlist
        """
        self.track_id = track_id
        self.title = title
        self.artist = artist
        self.duration_ms = duration_ms
        self.album = album
        self.added_at = added_at

    @property
    def duration_str(self) -> str:
        """Get a formatted string representation of the track duration.

        Returns:
            String representation of duration (MM:SS)
        """
        if not self.duration_ms:
            return "--:--"

        total_seconds = self.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @abstractmethod
    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        pass
