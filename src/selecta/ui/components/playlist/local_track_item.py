# src/selecta/ui/components/playlist/local_track_item.py
from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.track_item import TrackItem


class LocalTrackItem(TrackItem):
    """Implementation of TrackItem for local database tracks."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        duration_ms: int | None = None,
        album: str | None = None,
        added_at: datetime | None = None,
        local_path: str | None = None,
        genre: str | None = None,
    ):
        """Initialize a local track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            duration_ms: Duration in milliseconds
            album: Album name
            added_at: When the track was added to the playlist
            local_path: Path to the local audio file
            genre: Track genre
        """
        super().__init__(track_id, title, artist, duration_ms, album, added_at)
        self.local_path = local_path
        self.genre = genre

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        return {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "genre": self.genre or "",
            "local_path": self.local_path or "",
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
        }
