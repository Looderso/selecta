"""YouTube data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict, cast


class YouTubeChannelDict(TypedDict, total=False):
    """TypedDict for YouTube channel data."""

    id: str
    title: str
    description: str
    customUrl: str
    publishedAt: str
    thumbnails: dict[str, dict[str, Any]]


class YouTubeVideoSnippetDict(TypedDict, total=False):
    """TypedDict for YouTube video snippet data."""

    publishedAt: str
    channelId: str
    title: str
    description: str
    thumbnails: dict[str, dict[str, Any]]
    channelTitle: str
    tags: list[str]
    categoryId: str
    liveBroadcastContent: str
    defaultLanguage: str
    localized: dict[str, str]
    defaultAudioLanguage: str


class YouTubeVideoContentDetailsDict(TypedDict, total=False):
    """TypedDict for YouTube video content details."""

    duration: str
    dimension: str
    definition: str
    caption: str
    licensedContent: bool
    contentRating: dict[str, Any]
    projection: str


class YouTubeVideoStatisticsDict(TypedDict, total=False):
    """TypedDict for YouTube video statistics."""

    viewCount: str
    likeCount: str
    favoriteCount: str
    commentCount: str


class YouTubeVideoDict(TypedDict, total=False):
    """TypedDict for YouTube video data."""

    kind: str
    etag: str
    id: str
    snippet: YouTubeVideoSnippetDict
    contentDetails: YouTubeVideoContentDetailsDict
    statistics: YouTubeVideoStatisticsDict
    videoId: str  # For playlist items


class YouTubePlaylistItemDict(TypedDict, total=False):
    """TypedDict for YouTube playlist item data."""

    kind: str
    etag: str
    id: str
    snippet: dict[str, Any]
    contentDetails: dict[str, Any]
    status: dict[str, Any]


class YouTubePlaylistItemsResponseDict(TypedDict, total=False):
    """TypedDict for YouTube playlist items response."""

    kind: str
    etag: str
    nextPageToken: str
    prevPageToken: str
    pageInfo: dict[str, Any]
    items: list[YouTubePlaylistItemDict]


class YouTubePlaylistSnippetDict(TypedDict, total=False):
    """TypedDict for YouTube playlist snippet data."""

    publishedAt: str
    channelId: str
    title: str
    description: str
    thumbnails: dict[str, dict[str, Any]]
    channelTitle: str
    localized: dict[str, str]


class YouTubePlaylistContentDetailsDict(TypedDict, total=False):
    """TypedDict for YouTube playlist content details."""

    itemCount: int


class YouTubePlaylistDict(TypedDict, total=False):
    """TypedDict for YouTube playlist data."""

    kind: str
    etag: str
    id: str
    snippet: YouTubePlaylistSnippetDict
    contentDetails: YouTubePlaylistContentDetailsDict
    status: dict[str, Any]


class YouTubePlaylistsResponseDict(TypedDict, total=False):
    """TypedDict for YouTube playlists response."""

    kind: str
    etag: str
    nextPageToken: str
    prevPageToken: str
    pageInfo: dict[str, Any]
    items: list[YouTubePlaylistDict]


@dataclass
class YouTubeVideo:
    """Representation of a YouTube video."""

    id: str
    title: str
    channel_id: str
    channel_title: str
    description: str = ""
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    like_count: int | None = None
    added_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert this video to a dictionary representation.

        Returns:
            Dictionary representation of the video
        """
        result = {
            "id": self.id,
            "title": self.title,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "description": self.description,
        }

        # Add optional fields if they exist
        if self.duration_seconds is not None:
            result["duration_seconds"] = self.duration_seconds
        if self.thumbnail_url:
            result["thumbnail_url"] = self.thumbnail_url
        if self.published_at:
            result["published_at"] = self.published_at.isoformat()
        if self.view_count is not None:
            result["view_count"] = self.view_count
        if self.like_count is not None:
            result["like_count"] = self.like_count
        if self.added_at:
            result["added_at"] = self.added_at.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "YouTubeVideo":
        """Create a YouTubeVideo from a dictionary.

        Args:
            data: Dictionary with video data

        Returns:
            YouTubeVideo instance
        """
        # Handle date fields
        published_at = None
        added_at = None

        if "published_at" in data and data["published_at"]:
            from contextlib import suppress

            with suppress(ValueError, TypeError):
                published_at = datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))

        if "added_at" in data and data["added_at"]:
            from contextlib import suppress

            with suppress(ValueError, TypeError):
                added_at = datetime.fromisoformat(data["added_at"].replace("Z", "+00:00"))

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            channel_id=data.get("channel_id", ""),
            channel_title=data.get("channel_title", ""),
            description=data.get("description", ""),
            duration_seconds=data.get("duration_seconds"),
            thumbnail_url=data.get("thumbnail_url"),
            published_at=published_at,
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            added_at=added_at,
        )

    @classmethod
    def from_youtube_dict(
        cls, video_dict: YouTubeVideoDict | dict[str, Any], added_at: datetime | None = None
    ) -> "YouTubeVideo":
        """Create a YouTubeVideo from a YouTube API response dictionary.

        Args:
            video_dict: YouTube video dictionary from the API
            added_at: When the video was added to a playlist (if applicable)

        Returns:
            YouTubeVideo instance
        """
        # For playlist items, video ID might be nested
        video_id = video_dict.get("id", "")
        if isinstance(video_id, dict) and "videoId" in video_id:
            video_id = video_id["videoId"]
        elif "videoId" in video_dict:
            video_id = video_dict["videoId"]

        # Get video snippet
        snippet = video_dict.get("snippet", {})
        
        # Get thumbnail URL (prefer high resolution if available)
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = None
        for size in ["maxres", "high", "medium", "default"]:
            if size in thumbnails and "url" in thumbnails[size]:
                thumbnail_url = thumbnails[size]["url"]
                break

        # Parse published date
        published_at = None
        if "publishedAt" in snippet:
            try:
                published_at_str = snippet["publishedAt"]
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                published_at = None

        # Get content details (duration, etc.)
        content_details = video_dict.get("contentDetails", {})
        duration_seconds = None
        if "duration" in content_details:
            duration_str = content_details["duration"]
            duration_seconds = _parse_iso8601_duration(duration_str)

        # Get statistics if available
        statistics = video_dict.get("statistics", {})
        view_count = None
        like_count = None
        
        if "viewCount" in statistics:
            try:
                view_count = int(statistics["viewCount"])
            except (ValueError, TypeError):
                pass
                
        if "likeCount" in statistics:
            try:
                like_count = int(statistics["likeCount"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=video_id,
            title=snippet.get("title", ""),
            channel_id=snippet.get("channelId", ""),
            channel_title=snippet.get("channelTitle", ""),
            description=snippet.get("description", ""),
            thumbnail_url=thumbnail_url,
            published_at=published_at,
            duration_seconds=duration_seconds,
            view_count=view_count,
            like_count=like_count,
            added_at=added_at,
        )


@dataclass
class YouTubePlaylist:
    """Representation of a YouTube playlist."""

    id: str
    title: str
    channel_id: str
    channel_title: str
    video_count: int
    description: str = ""
    privacy_status: str = "public"
    thumbnail_url: str | None = None
    published_at: datetime | None = None

    @classmethod
    def from_youtube_dict(
        cls, playlist_dict: YouTubePlaylistDict | dict[str, Any]
    ) -> "YouTubePlaylist":
        """Create a YouTubePlaylist from a YouTube API response dictionary.

        Args:
            playlist_dict: YouTube playlist dictionary from the API

        Returns:
            YouTubePlaylist instance
        """
        # Get playlist snippet
        snippet = playlist_dict.get("snippet", {})
        
        # Get thumbnail URL (prefer high resolution if available)
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = None
        for size in ["maxres", "high", "medium", "default"]:
            if size in thumbnails and "url" in thumbnails[size]:
                thumbnail_url = thumbnails[size]["url"]
                break

        # Parse published date
        published_at = None
        if "publishedAt" in snippet:
            try:
                published_at_str = snippet["publishedAt"]
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                published_at = None

        # Get content details
        content_details = playlist_dict.get("contentDetails", {})
        video_count = content_details.get("itemCount", 0)

        # Get privacy status
        status = playlist_dict.get("status", {})
        privacy_status = status.get("privacyStatus", "public")

        return cls(
            id=playlist_dict.get("id", ""),
            title=snippet.get("title", ""),
            channel_id=snippet.get("channelId", ""),
            channel_title=snippet.get("channelTitle", ""),
            description=snippet.get("description", ""),
            video_count=video_count,
            privacy_status=privacy_status,
            thumbnail_url=thumbnail_url,
            published_at=published_at,
        )


def _parse_iso8601_duration(duration_str: str) -> int | None:
    """Parse ISO 8601 duration string (like PT1H30M15S) to seconds.

    Args:
        duration_str: ISO 8601 duration string

    Returns:
        Duration in seconds or None if parsing fails
    """
    import re
    
    if not duration_str or not duration_str.startswith("PT"):
        return None
        
    try:
        # Remove the PT prefix
        duration_str = duration_str[2:]
        
        # Use regex to extract hours, minutes, seconds
        hours = re.search(r'(\d+)H', duration_str)
        minutes = re.search(r'(\d+)M', duration_str)
        seconds = re.search(r'(\d+)S', duration_str)
        
        # Convert to seconds
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
            
        return total_seconds
    except Exception:
        return None