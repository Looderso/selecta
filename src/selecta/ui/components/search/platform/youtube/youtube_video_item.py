"""YouTube video item widget for search results."""

from typing import Any

from selecta.core.platform.youtube.models import _parse_iso8601_duration
from selecta.ui.components.search.base_search_result import BaseSearchResult
from selecta.ui.components.search.utils import extract_title


class YouTubeVideoItem(BaseSearchResult):
    """Widget to display a single YouTube video search result."""

    def __init__(self, video_data: dict[str, Any], parent=None):
        """Initialize the YouTube video item.

        Args:
            video_data: Dictionary with video data from YouTube API
            parent: Parent widget
        """
        super().__init__(video_data, parent)
        self.setObjectName("youtubeVideoItem")
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)

    def setup_content(self) -> None:
        """Set up the YouTube-specific content."""
        # Apply styling
        self.setStyleSheet("""
            #youtubeVideoItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #youtubeVideoItem:hover {
                background-color: #333333;
            }
            #videoTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #channelName {
                font-size: 12px;
                color: #B3B3B3;
            }
            #videoDuration {
                font-size: 11px;
                color: #999999;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #FFFFFF;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(51, 51, 51, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(51, 51, 51, 0.5);
            }
            QPushButton:disabled {
                border-color: #555;
                color: #555;
            }
        """)

        # Extract video info
        title = self.get_title()
        channel = self.get_artist()
        duration = self._get_duration_string()

        # Video title with elision
        self.title_label = self.create_elided_label(title, "videoTitle")
        self.text_layout.addWidget(self.title_label)

        # Channel name with elision
        self.channel_label = self.create_elided_label(channel, "channelName")
        self.text_layout.addWidget(self.channel_label)

        # Duration with elision
        if duration:
            self.duration_label = self.create_elided_label(f"Duration: {duration}", "videoDuration")
            self.text_layout.addWidget(self.duration_label)

    def get_title(self) -> str:
        """Get the title of the video.

        Returns:
            Title string
        """
        # Check for YouTube snippet title
        snippet = self.item_data.get("snippet", {})
        if snippet.get("title"):
            return snippet.get("title")

        # Fallback to generic title extraction
        return extract_title(self.item_data)

    def get_artist(self) -> str:
        """Get the channel name of the video.

        Returns:
            Channel name string
        """
        # Check for YouTube channel title
        snippet = self.item_data.get("snippet", {})
        return snippet.get("channelTitle", "")

    def get_image_url(self) -> str:
        """Get the thumbnail URL for the video.

        Returns:
            URL string or empty if not available
        """
        # Check for thumbnails in YouTube format
        snippet = self.item_data.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})

        # Try to get the highest quality thumbnail available
        for quality in ["high", "medium", "default"]:
            quality_data = thumbnails.get(quality, {})
            if quality_data.get("url"):
                return quality_data["url"]

        # Check for direct thumbnail_url field
        return self.item_data.get("thumbnail_url", "")

    def _get_duration_string(self) -> str:
        """Get the formatted duration string of the video.

        Returns:
            Duration string (e.g. "3:45") or empty if not available
        """
        # Check for contentDetails duration in ISO 8601 format
        content_details = self.item_data.get("contentDetails", {})
        duration_iso = content_details.get("duration")

        if duration_iso:
            # Parse ISO 8601 duration
            duration_seconds = _parse_iso8601_duration(duration_iso)

            if duration_seconds:
                # Format as minutes:seconds
                minutes, seconds = divmod(duration_seconds, 60)
                return f"{minutes}:{seconds:02d}"

        # Check for directly provided duration in seconds
        duration_seconds = self.item_data.get("duration_seconds")
        if duration_seconds:
            try:
                seconds = int(duration_seconds)
                minutes, seconds = divmod(seconds, 60)
                return f"{minutes}:{seconds:02d}"
            except (ValueError, TypeError):
                # Handle case where duration_seconds is not a valid integer
                pass

        return ""
