"""Discogs data models."""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DiscogsRelease:
    """Representation of a Discogs release."""

    id: int
    title: str
    artist: str
    year: int | None = None
    genre: list[str] | None = None
    format: list[str] | None = None
    label: str | None = None
    catno: str | None = None  # Catalog number
    country: str | None = None
    thumb_url: str | None = None  # Small image URL
    cover_url: str | None = None  # Full-size image URL
    uri: str | None = None  # Discogs URL

    @classmethod
    def from_discogs_object(cls, release_obj: Any) -> "DiscogsRelease":
        """Create a DiscogsRelease from a Discogs API release object.

        Args:
            release_obj: Discogs release object from the API

        Returns:
            DiscogsRelease instance
        """
        # Get basic fields
        release_id = getattr(release_obj, "id", None)
        title = getattr(release_obj, "title", "")

        # Handle artist differently based on object type
        if hasattr(release_obj, "artists"):
            # For full release objects
            artist_names = [artist.name for artist in release_obj.artists]
            artist = ", ".join(artist_names)
        elif hasattr(release_obj, "artist"):
            # For search results
            artist = release_obj.artist
        else:
            artist = "Unknown Artist"

        # Get year - different depending on whether it's a search result or release
        year = getattr(release_obj, "year", None)

        # Get other fields
        formats = []
        if hasattr(release_obj, "formats"):
            for fmt in release_obj.formats:
                if isinstance(fmt, dict) and "name" in fmt:
                    formats.append(fmt["name"])
                elif hasattr(fmt, "name"):
                    formats.append(fmt.name)

        # Get genres if available
        genres = getattr(release_obj, "genres", [])
        if not genres:
            genres = getattr(release_obj, "genre", [])

        # Get label info
        label = None
        catno = None
        # TODO make method for this kind of stuff
        if hasattr(release_obj, "labels") and release_obj.labels:
            if isinstance(release_obj.labels[0], dict):
                label = release_obj.labels[0].get("name")
                catno = release_obj.labels[0].get("catno")
            else:
                label = getattr(release_obj.labels[0], "name", None)
                catno = getattr(release_obj.labels[0], "catno", None)

        # Get country
        country = getattr(release_obj, "country", None)

        # Get image URLs
        thumb_url = None
        cover_url = None
        if hasattr(release_obj, "thumb"):
            thumb_url = release_obj.thumb
        if hasattr(release_obj, "images") and release_obj.images:
            if isinstance(release_obj.images[0], dict):
                cover_url = release_obj.images[0].get("uri")
            else:
                cover_url = getattr(release_obj.images[0], "uri", None)

        # Get URI
        uri = getattr(release_obj, "uri", None)
        if not uri and release_id:
            uri = f"https://www.discogs.com/release/{release_id}"

        return cls(
            id=release_id,
            title=title,
            artist=artist,
            year=year,
            genre=genres,
            format=formats,
            label=label,
            catno=catno,
            country=country,
            thumb_url=thumb_url,
            cover_url=cover_url,
            uri=uri,
        )


@dataclass
class DiscogsVinyl:
    """Representation of a vinyl record from Discogs collection or wantlist."""

    release: DiscogsRelease
    is_owned: bool = False
    is_wanted: bool = False
    date_added: datetime | None = None
    rating: int | None = None  # 1-5 stars
    notes: str | None = None

    @classmethod
    def from_discogs_object(
        cls, release_obj: Any, is_owned: bool = False, is_wanted: bool = False
    ) -> "DiscogsVinyl":
        """Create a DiscogsVinyl from a Discogs API release object.

        Args:
            release_obj: Discogs release object from the API
            is_owned: Whether this vinyl is in the user's collection
            is_wanted: Whether this vinyl is in the user's wantlist

        Returns:
            DiscogsVinyl instance
        """
        # Convert the release object to our model
        release = DiscogsRelease.from_discogs_object(release_obj)

        # Get collection-specific metadata
        date_added = None
        rating = None
        notes = None

        # Try to get date_added
        if hasattr(release_obj, "date_added"):
            with contextlib.suppress(ValueError, AttributeError):
                date_added = datetime.fromisoformat(release_obj.date_added.replace("Z", "+00:00"))

        # Try to get rating
        if hasattr(release_obj, "rating"):
            rating = getattr(release_obj, "rating", None)

        # Try to get notes
        if hasattr(release_obj, "notes"):
            notes = getattr(release_obj, "notes", None)

        return cls(
            release=release,
            is_owned=is_owned,
            is_wanted=is_wanted,
            date_added=date_added,
            rating=rating,
            notes=notes,
        )
