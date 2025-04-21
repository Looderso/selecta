# src/selecta/ui/components/playlist/discogs/discogs_track_item.py
from datetime import datetime
from typing import Any

from selecta.ui.components.playlist.base_items import BaseTrackItem


class DiscogsTrackItem(BaseTrackItem):
    """Implementation of TrackItem for Discogs releases."""

    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        album: str | None = None,
        duration_ms: int | None = None,
        added_at: datetime | None = None,
        year: int | None = None,
        genre: str | None = None,
        format: str | None = None,
        label: str | None = None,
        catno: str | None = None,
        country: str | None = None,
        discogs_id: int | None = None,
        discogs_uri: str | None = None,
        thumb_url: str | None = None,
        cover_url: str | None = None,
        is_owned: bool = False,
        is_wanted: bool = False,
        notes: str | None = None,
    ):
        """Initialize a Discogs track item.

        Args:
            track_id: The unique identifier for the track
            title: Release title
            artist: Release artist
            album: Album name (same as title for releases)
            duration_ms: Duration (not typically available from Discogs)
            added_at: When the release was added to collection/wantlist
            year: Release year
            genre: Primary genre
            format: Release format (e.g., "Vinyl, LP, Album")
            label: Record label
            catno: Catalog number
            country: Country of release
            discogs_id: Discogs release ID
            discogs_uri: Discogs URI for the release
            thumb_url: URL to thumbnail image
            cover_url: URL to full-size cover image
            is_owned: Whether the release is in the user's collection
            is_wanted: Whether the release is in the user's wantlist
            notes: User notes about the release
        """
        # Initialize with base class
        super().__init__(
            track_id=track_id,
            title=title,
            artist=artist,
            duration_ms=duration_ms,
            album=album,
            added_at=added_at,
            platforms=["discogs"],
        )

        # Discogs-specific fields
        self.year = year
        self.genre = genre
        self.format = format
        self.label = label
        self.catno = catno
        self.country = country
        self.discogs_id = discogs_id
        self.discogs_uri = discogs_uri
        self.thumb_url = thumb_url
        self.cover_url = cover_url
        self.is_owned = is_owned
        self.is_wanted = is_wanted
        self.notes = notes

    def to_display_data(self) -> dict[str, Any]:
        """Convert the track to a dictionary for display in the UI.

        Returns:
            Dictionary with track data
        """
        # Check for cached data
        if hasattr(self, "_display_data_cache") and self._display_data_cache is not None:
            return self._display_data_cache

        # Create status indicators for owned/wanted
        status = ""
        if self.is_owned:
            status = "✓ Owned"
        elif self.is_wanted:
            status = "⭐ Wanted"

        # Create display data
        display_data = {
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "duration": self.duration_str,
            "year": str(self.year) if self.year else "",
            "genre": self.genre or "",
            "format": self.format or "",
            "label": self.label or "",
            "catno": self.catno or "",
            "country": self.country or "",
            "added_at": self.added_at.strftime("%Y-%m-%d") if self.added_at else "",
            "status": status,
            "notes": self.notes or "",
            # Add platform-specific fields
            "platforms": self.platforms,
            "platforms_tooltip": "Available on Discogs",
            # Include URLs for potential use
            "thumb_url": self.thumb_url,
            "cover_url": self.cover_url,
            "discogs_uri": self.discogs_uri,
        }

        # Cache the display data
        self._display_data_cache = display_data

        return display_data
