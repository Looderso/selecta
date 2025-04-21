"""Implementation of TrackItem for library database tracks.

This module provides the LibraryTrackItem class which extends the BaseTrackItem
to provide track functionality specific to the local library database.
"""

from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.base_items import BaseTrackItem


class LibraryTrackItem(BaseTrackItem):
    """Implementation of TrackItem for library database tracks."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        duration_ms: int | None = None,
        album: str | None = None,
        added_at: datetime | None = None,
        album_id: int | None = None,
        has_image: bool = False,
        local_path: str | None = None,
        genre: str | None = None,
        bpm: float | None = None,
        tags: list[str] | None = None,
        platform_info: list[dict[str, Any]] | None = None,
        quality: int = -1,
        platforms: list[str] | None = None,
    ):
        """Initialize a library track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            duration_ms: Duration in milliseconds
            album: Album name
            added_at: When the track was added to the playlist
            album_id: The database ID of the album, if available
            has_image: Whether this track has an image in the database
            local_path: Path to the local audio file
            genre: Track genre
            bpm: Beats per minute
            tags: List of tags
            platform_info: List of platform information dictionaries
            quality: Track quality rating (-1=not rated, 1-5=star rating)
            platforms: List of platforms this track is available on
        """
        super().__init__(
            track_id=track_id,
            title=title,
            artist=artist,
            duration_ms=duration_ms,
            album=album,
            added_at=added_at,
            album_id=album_id,
            has_image=has_image,
            platforms=platforms,
        )

        self.local_path = local_path
        self.genre = genre
        self.bpm = bpm
        self.tags = tags or []
        self.platform_info = platform_info or []
        self.quality = quality

        # Parse platform information and fill the platforms list
        if not platforms and platform_info:
            derived_platforms = []
            for info in platform_info:
                if isinstance(info, dict) and "platform" in info:
                    platform = info["platform"]
                    if platform and platform not in derived_platforms:
                        derived_platforms.append(platform)

            if derived_platforms:
                self.platforms = derived_platforms

    def _format_bpm(self) -> str:
        """Format BPM to string representation.

        Returns:
            Formatted BPM string
        """
        if self.bpm is None:
            return ""

        try:
            if isinstance(self.bpm, int | float) and self.bpm > 0:
                return f"{self.bpm:.1f}"
            elif isinstance(self.bpm, str) and self.bpm.strip():
                return self.bpm
        except (ValueError, TypeError):
            pass

        return ""

    def _format_genre(self) -> str:
        """Format genre to string representation.

        Returns:
            Formatted genre string
        """
        if not self.genre:
            return ""

        if isinstance(self.genre, list):
            return ", ".join(self.genre)

        return str(self.genre)

    def _format_tags(self) -> str:
        """Format tags to string representation.

        Returns:
            Formatted tags string
        """
        if not self.tags:
            return ""

        if isinstance(self.tags, list):
            return ", ".join(self.tags)
        elif isinstance(self.tags, str):
            return self.tags

        return str(self.tags)

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Use cached data if available for better performance
        if hasattr(self, "_display_data_cache") and self._display_data_cache:
            return self._display_data_cache

        # Format BPM value
        bpm_str = self._format_bpm()

        # Format genre
        genre_str = self._format_genre()

        # Format tags
        tags_str = self._format_tags()

        # Map quality rating to a string
        quality_map = {-1: "Not Rated", 1: "Very Poor", 2: "Poor", 3: "OK", 4: "Good", 5: "Great"}
        quality_str = quality_map.get(self.quality, "Not Rated")

        # Create tooltip for platforms
        platform_tooltips = []
        for platform in self.platforms:
            platform_name = platform.capitalize()
            platform_tooltips.append(f"Available on {platform_name}")

        # Create the display data dictionary
        display_data = {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "genre": genre_str,
            "bpm": bpm_str,
            "tags": tags_str,
            "quality": self.quality,
            "quality_str": quality_str,
            "local_path": self.local_path or "",
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            "platforms": self.platforms,
            "platforms_tooltip": ", ".join(platform_tooltips),
            "platform_info": self.platform_info,
        }

        # Cache for future use
        self._display_data_cache = display_data

        return display_data
