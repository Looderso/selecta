import time
from datetime import datetime
from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.playlist.track_item import TrackItem


class PlatformIconsWidget(QWidget):
    """Widget to display platform icons horizontally."""

    def __init__(self, platforms: list[str], parent=None):
        """Initialize the platform icons widget.

        Args:
            platforms: List of platform names
            parent: Parent widget
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Load and add platform icons
        for platform in platforms:
            icon_path = get_resource_path(f"icons/{platform}.png")
            if icon_path.exists():
                label = QLabel()
                pixmap = QPixmap(str(icon_path))
                # Scale pixmap to a reasonable size
                pixmap = pixmap.scaled(
                    16,
                    16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(pixmap)
                layout.addWidget(label)


class LibraryTrackItem(TrackItem):
    """Implementation of TrackItem for library database tracks."""

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
        bpm: float | None = None,
        tags: list[str] | None = None,
        platform_info: list[dict] | None = None,
        quality: int = -1,
        has_image: bool = False,
        in_wantlist: bool = False,
        in_collection: bool = False,
    ):
        """Initialize a library track item.

        Args:
            track_id: The unique identifier for the track
            title: Track title
            artist: Track artist
            duration_ms: Duration in milliseconds
            album: Album name
            added_at: When the track was added to the playlist
            local_path: Path to the local audio file
            genre: Track genre
            bpm: Beats per minute
            tags: List of tags
            platform_info: List of platform information dictionaries
            quality: Track quality rating (-1=not rated, 1-5=star rating)
            has_image: Whether this track has an image in the database
            in_wantlist: Whether this track is in the Discogs wantlist
            in_collection: Whether this track is in the Discogs collection
        """
        super().__init__(
            track_id,
            title,
            artist,
            duration_ms,
            album,
            added_at,
            album_id=None,
            has_image=has_image,
        )
        self.local_path = local_path
        self.genre = genre
        self.bpm = bpm
        self.tags = tags or []
        self.platform_info = platform_info or []  # [{'platform': 'spotify', 'id': '...', ...}, ...]
        self.quality = quality
        self.in_wantlist = in_wantlist
        self.in_collection = in_collection

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Very aggressive caching strategy - always use cached data if available
        # The cache will be explicitly cleared when data changes
        if hasattr(self, "_display_data_cache"):
            # Just return the cached data immediately without any timing checks
            # This eliminates all unnecessary recalculations during UI painting
            return self._display_data_cache

        # Count display data calls for debugging if needed
        if hasattr(self, "_display_data_call_count"):
            self._display_data_call_count += 1
        else:
            self._display_data_call_count = 1

        # Only log extremely excessive calls, to reduce debug noise
        if self._display_data_call_count % 1000 == 0:
            logger.debug(
                f"to_display_data called {self._display_data_call_count} times "
                f"for track {self.track_id}"
            )

        # Get platform icons and prepare tooltip
        platforms = []
        platform_tooltips = []

        # Check which platforms this track is available on
        # Handle both dict and TrackPlatformInfo objects
        has_spotify = False
        has_rekordbox = False
        has_discogs = False
        has_youtube = False

        # First check platform_info if available
        if hasattr(self, "platform_info") and self.platform_info:
            for info in self.platform_info:
                # Handle both dict and TrackPlatformInfo objects
                if hasattr(info, "platform"):
                    # It's a TrackPlatformInfo object
                    platform_name = info.platform
                elif isinstance(info, dict) and "platform" in info:
                    # It's a dictionary
                    platform_name = info.get("platform", "")
                else:
                    # Unknown format
                    continue

                if platform_name == "spotify":
                    has_spotify = True
                elif platform_name == "rekordbox":
                    has_rekordbox = True
                elif platform_name == "discogs":
                    has_discogs = True
                elif platform_name == "youtube":
                    has_youtube = True

        # Also check if we have a platforms list attribute (added by the table model)
        if hasattr(self, "platforms") and self.platforms:
            for platform in self.platforms:
                if platform == "spotify":
                    has_spotify = True
                elif platform == "rekordbox":
                    has_rekordbox = True
                elif platform == "discogs":
                    has_discogs = True
                elif platform == "youtube":
                    has_youtube = True
                elif platform == "wantlist":
                    self.in_wantlist = True
                elif platform == "collection":
                    self.in_collection = True

        # Build platform list and tooltips
        if has_spotify:
            platforms.append("spotify")
            platform_tooltips.append("Available on Spotify")
        if has_rekordbox:
            platforms.append("rekordbox")
            platform_tooltips.append("Available in Rekordbox")
        if has_discogs:
            platforms.append("discogs")
            platform_tooltips.append("Available on Discogs")
        if has_youtube:
            platforms.append("youtube")
            platform_tooltips.append("Available on YouTube")

        # Add wantlist and collection status
        if self.in_wantlist:
            platforms.append("wantlist")
            platform_tooltips.append("In Discogs Wantlist")

        if self.in_collection:
            platforms.append("collection")
            platform_tooltips.append("In Discogs Collection")

        # Format BPM value - ensuring it's properly formatted
        bpm_str = ""
        if self.bpm is not None:
            try:
                if isinstance(self.bpm, str) and self.bpm.strip():
                    # Convert string BPM to float if possible
                    try:
                        bpm_float = float(self.bpm)
                        bpm_str = f"{bpm_float:.1f}"
                    except ValueError:
                        bpm_str = self.bpm
                elif isinstance(self.bpm, int | float) and self.bpm > 0:
                    bpm_str = f"{self.bpm:.1f}"
            except (ValueError, TypeError):
                pass

        # Format genre - ensure it's a string
        genre_str = ""
        if self.genre:
            genre_str = ", ".join(self.genre) if isinstance(self.genre, list) else str(self.genre)

        # Format tags
        tags_str = ""
        if self.tags:
            if isinstance(self.tags, list):
                tags_str = ", ".join(self.tags)
            elif isinstance(self.tags, str):
                # Handle tags as a comma-separated string
                tags_str = self.tags
            else:
                tags_str = str(self.tags)

        # Map quality rating to a user-friendly string for tooltip
        quality_map = {-1: "Not Rated", 1: "Very Poor", 2: "Poor", 3: "OK", 4: "Good", 5: "Great"}
        quality_str = quality_map.get(self.quality, "Not Rated")

        # Debug log - but only once per track to avoid spam
        # Use current time to decide when to log again
        current_time = time.time()
        last_log_time = getattr(self, "_last_cache_log_time", 0)

        if current_time - last_log_time > 120:  # Log at most once every 2 minutes per track
            if bpm_str or genre_str:
                logger.debug(
                    f"Display data for track {self.track_id}: BPM={bpm_str}, Genre={genre_str}"
                )
            self._last_cache_log_time = current_time

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
            "platforms": platforms,
            "platforms_tooltip": ", ".join(platform_tooltips),
            "platform_info": self.platform_info,
            "in_wantlist": self.in_wantlist,
            "in_collection": self.in_collection,
        }

        # Cache the result - we'll use permanent caching with explicit invalidation
        # rather than time-based expiry
        self._display_data_cache = display_data

        return display_data

    def clear_display_cache(self) -> None:
        """Clear the display data cache to force regeneration."""
        if hasattr(self, "_display_data_cache"):
            delattr(self, "_display_data_cache")

        # Clean up any other cache-related attributes
        for attr in [
            "_logged_display_data",
            "_display_cache_time",
            "_last_cache_log_time",
            "_display_data_call_count",
        ]:
            if hasattr(self, attr):
                delattr(self, attr)

        # Log the cache clearing for debugging
        logger.debug(f"Cleared display cache for track {self.track_id}")

    def _get_platform_icons(self, platforms: list[str]) -> QWidget:
        """Get icons for platforms.

        Args:
            platforms: List of platform names

        Returns:
            Widget containing platform icons
        """
        return PlatformIconsWidget(platforms)
