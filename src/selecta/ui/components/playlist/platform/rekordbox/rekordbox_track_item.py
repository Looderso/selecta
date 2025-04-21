"""Rekordbox track item implementation.

This module provides the implementation of the track item for Rekordbox tracks,
extending the base track item with Rekordbox-specific functionality.
"""

from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.base_items import BaseTrackItem


class RekordboxTrackItem(BaseTrackItem):
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
        super().__init__(
            track_id=track_id,
            title=title,
            artist=artist,
            duration_ms=duration_ms,
            album=album,
            added_at=added_at,
            has_image=False,
            platforms=["rekordbox"],  # Always available on rekordbox
        )

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
        # Check if we already have cached display data
        if hasattr(self, "_display_data_cache") and self._display_data_cache is not None:
            return self._display_data_cache

        # Create display data dictionary
        display_data = {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "path": self.path or "",
            "bpm": f"{self.bpm:.1f}" if self.bpm is not None else "",
            "key": self.key or "",
            "rating": self.rating or 0,
            "platforms": ", ".join(self.platforms),
        }

        # Cache the result
        self._display_data_cache = display_data
        return display_data
