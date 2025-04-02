from datetime import datetime
from typing import Any

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
        bpm: float | None = None,
        tags: list[str] | None = None,
        platform_info: list[dict] | None = None,
        quality: int = -1,
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
            bpm: Beats per minute
            tags: List of tags
            platform_info: List of platform information dictionaries
            quality: Track quality rating (-1=not rated, 1-5=star rating)
        """
        super().__init__(track_id, title, artist, duration_ms, album, added_at)
        self.local_path = local_path
        self.genre = genre
        self.bpm = bpm
        self.tags = tags or []
        self.platform_info = platform_info or []  # [{'platform': 'spotify', 'id': '...', ...}, ...]
        self.quality = quality

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Get platform icons and prepare tooltip
        platforms = []
        platform_tooltips = []

        # Check which platforms this track is available on
        has_spotify = any(info.get("platform") == "spotify" for info in self.platform_info)
        has_rekordbox = any(info.get("platform") == "rekordbox" for info in self.platform_info)
        has_discogs = any(info.get("platform") == "discogs" for info in self.platform_info)

        if has_spotify:
            platforms.append("spotify")
            platform_tooltips.append("Available on Spotify")
        if has_rekordbox:
            platforms.append("rekordbox")
            platform_tooltips.append("Available in Rekordbox")
        if has_discogs:
            platforms.append("discogs")
            platform_tooltips.append("Available on Discogs")

        # Format BPM value
        bpm_str = f"{self.bpm:.1f}" if self.bpm is not None else ""

        # Format tags
        tags_str = ", ".join(self.tags) if self.tags else ""

        # Map quality rating to a user-friendly string for tooltip
        quality_map = {-1: "Not Rated", 1: "Very Poor", 2: "Poor", 3: "OK", 4: "Good", 5: "Great"}
        quality_str = quality_map.get(self.quality, "Not Rated")

        return {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "genre": self.genre or "",
            "bpm": bpm_str,
            "tags": tags_str,
            "quality": self.quality,
            "quality_str": quality_str,
            "local_path": self.local_path or "",
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            "platforms": platforms,
            "platforms_tooltip": ", ".join(platform_tooltips),
            "platform_info": self.platform_info,
        }

    def _get_platform_icons(self, platforms: list[str]) -> QWidget:
        """Get icons for platforms.

        Args:
            platforms: List of platform names

        Returns:
            Widget containing platform icons
        """
        return PlatformIconsWidget(platforms)
