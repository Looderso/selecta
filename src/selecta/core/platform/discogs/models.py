"""Discogs data models."""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


def safe_get_attr(obj: Any, attr_name: str, default: T = None) -> T:
    """Safely get an attribute from an object.

    Args:
        obj: Object to get attribute from
        attr_name: Name of the attribute
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    return getattr(obj, attr_name, default)


def extract_list_attr(obj: Any, attr_name: str, key_name: str = "name") -> list[str]:
    """Extract a list of attributes from an object.

    Args:
        obj: Object to extract from
        attr_name: Name of the list attribute
        key_name: Name of the key to extract from each item

    Returns:
        List of extracted values
    """
    result = []
    attr_list = safe_get_attr(obj, attr_name, [])

    if not attr_list:
        return result

    for item in attr_list:
        if isinstance(item, dict) and key_name in item:
            result.append(item[key_name])
        elif hasattr(item, key_name):
            result.append(getattr(item, key_name))

    return result


def extract_first_item(obj: Any, attr_name: str, key_name: str = "name") -> str | None:
    """Extract first item from a list attribute.

    Args:
        obj: Object to extract from
        attr_name: Name of the list attribute
        key_name: Name of the key to extract

    Returns:
        Extracted value or None
    """
    attr_list = safe_get_attr(obj, attr_name, [])
    if not attr_list:
        return None

    first_item = attr_list[0]
    if isinstance(first_item, dict):
        return first_item.get(key_name)
    return safe_get_attr(first_item, key_name)


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
        release_id = safe_get_attr(release_obj, "id")
        if not release_id:
            raise ValueError("No release_id")
        title = safe_get_attr(release_obj, "title", "")

        # Handle artist
        artist = "Unknown Artist"
        if hasattr(release_obj, "artists"):
            artist_names = extract_list_attr(release_obj, "artists")
            artist = ", ".join(artist_names)
        elif hasattr(release_obj, "artist"):
            artist = release_obj.artist

        # Get year
        year = safe_get_attr(release_obj, "year")

        # Get formats
        formats = extract_list_attr(release_obj, "formats")

        # Get genres
        genres = safe_get_attr(release_obj, "genres", [])
        if not genres:
            genres = safe_get_attr(release_obj, "genre", [])

        # Get label and catalog number
        label = extract_first_item(release_obj, "labels")
        catno = extract_first_item(release_obj, "labels", "catno")

        # Get country
        country = safe_get_attr(release_obj, "country")

        # Get image URLs
        thumb_url = safe_get_attr(release_obj, "thumb")
        cover_url = extract_first_item(release_obj, "images", "uri")

        # Get URI
        uri = safe_get_attr(release_obj, "uri")
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
        if hasattr(release_obj, "date_added"):
            with contextlib.suppress(ValueError, AttributeError):
                date_added = datetime.fromisoformat(
                    safe_get_attr(release_obj, "date_added", "").replace("Z", "+00:00")
                )

        # Get rating and notes
        rating = safe_get_attr(release_obj, "rating")
        notes = safe_get_attr(release_obj, "notes")

        return cls(
            release=release,
            is_owned=is_owned,
            is_wanted=is_wanted,
            date_added=date_added,
            rating=rating,
            notes=notes,
        )
