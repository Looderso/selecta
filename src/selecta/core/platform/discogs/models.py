"""Discogs data models."""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Protocol,
    TypeGuard,
    TypeVar,
    cast,
    runtime_checkable,
)

T = TypeVar("T")


def safe_get_attr(obj: Any, attr_name: str, default: T | None = None) -> T | None:
    """Safely get an attribute from an object.

    Args:
        obj: Object to get attribute from
        attr_name: Name of the attribute
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    return getattr(obj, attr_name, default)


@runtime_checkable
class HasNameAttribute(Protocol):
    """Protocol for objects with a name attribute."""

    name: str


def has_name_attribute(obj: Any) -> TypeGuard[HasNameAttribute]:
    """Check if an object has a name attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a name attribute
    """
    return hasattr(obj, "name")


@runtime_checkable
class HasArtist(Protocol):
    """Protocol for objects with an artist attribute."""

    artist: str


@runtime_checkable
class HasDateAdded(Protocol):
    """Protocol for objects with a date_added attribute."""

    date_added: str


def extract_list_attr(obj: Any, attr_name: str, key_name: str = "name") -> list[str]:
    """Extract a list of attributes from an object.

    Args:
        obj: Object to extract from
        attr_name: Name of the list attribute
        key_name: Name of the key to extract from each item

    Returns:
        List of extracted values
    """
    result: list[str] = []
    attr_list: list[Any] = safe_get_attr(obj, attr_name, []) or []

    if not attr_list:
        return result

    for item in attr_list:
        if isinstance(item, dict) and key_name in item:
            result.append(cast(str, item[key_name]))
        elif has_name_attribute(item):
            result.append(item.name)

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
    attr_list: list[Any] = safe_get_attr(obj, attr_name, []) or []
    if not attr_list:
        return None

    try:
        first_item = attr_list[0]
        if isinstance(first_item, dict):
            return cast(str | None, first_item.get(key_name))
        return cast(str | None, safe_get_attr(first_item, key_name))
    except (IndexError, TypeError):
        return None


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
    def from_discogs_dict(cls, release_dict: dict[str, Any]) -> "DiscogsRelease":
        """Create a DiscogsRelease from a Discogs API response dictionary.

        Args:
            release_dict: Dictionary with release data from the Discogs API

        Returns:
            DiscogsRelease instance
        """
        # Extract ID
        release_id: int = cast(int, release_dict.get("id"))
        if not release_id:
            raise ValueError("No release_id in data")

        # Extract title
        title: str = cast(str, release_dict.get("title", ""))

        # Extract artist
        artist: str = "Unknown Artist"
        artist_data: list[dict[str, Any]] = cast(
            list[dict[str, Any]], release_dict.get("artists", []) or []
        )
        if artist_data:
            artist_names = [a.get("name", "") for a in artist_data if isinstance(a, dict)]
            artist = ", ".join(filter(None, artist_names))

        # Extract year
        year: int | None = cast(int | None, release_dict.get("year"))

        # Extract formats
        formats: list[str] = []
        format_data: list[dict[str, Any]] = cast(
            list[dict[str, Any]], release_dict.get("formats", []) or []
        )
        if format_data:
            for fmt in format_data:
                if isinstance(fmt, dict) and "name" in fmt:
                    formats.append(cast(str, fmt["name"]))

        # Extract genres
        genres: list[str] = cast(list[str], release_dict.get("genres", []) or [])
        if not genres:
            genres = cast(list[str], release_dict.get("genre", []) or [])

        # Extract label and catalog number
        label: str | None = None
        catno: str | None = None
        label_data: list[dict[str, Any]] = cast(
            list[dict[str, Any]], release_dict.get("labels", []) or []
        )
        if label_data and isinstance(label_data, list) and label_data:
            try:
                first_label = label_data[0]
                if isinstance(first_label, dict):
                    label = cast(str | None, first_label.get("name"))
                    catno = cast(str | None, first_label.get("catno"))
            except (IndexError, TypeError):
                pass

        # Extract country
        country: str | None = cast(str | None, release_dict.get("country"))

        # Extract images
        thumb_url: str | None = cast(str | None, release_dict.get("thumb"))
        cover_url: str | None = cast(str | None, release_dict.get("cover_image"))

        # Extract URI
        uri: str | None = cast(str | None, release_dict.get("resource_url"))
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

    @classmethod
    def from_discogs_object(cls, release_obj: Any) -> "DiscogsRelease":
        """Create a DiscogsRelease from a Discogs API release object.

        Args:
            release_obj: Discogs release object from the API

        Returns:
            DiscogsRelease instance
        """
        # Get basic fields
        release_id: int = cast(int, safe_get_attr(release_obj, "id"))
        if not release_id:
            raise ValueError("No release_id")
        title: str = cast(str, safe_get_attr(release_obj, "title", ""))

        # Handle artist
        artist: str = "Unknown Artist"

        # Use protocol for HasArtist
        def has_artist(obj: Any) -> TypeGuard["HasArtist"]:
            return hasattr(obj, "artist")

        if hasattr(release_obj, "artists"):
            artist_names = extract_list_attr(release_obj, "artists")
            if artist_names:
                artist = ", ".join(artist_names)
        elif has_artist(release_obj):
            artist = release_obj.artist

        # Get year
        year: int | None = cast(int | None, safe_get_attr(release_obj, "year"))

        # Get formats
        formats: list[str] = extract_list_attr(release_obj, "formats")

        # Get genres
        genres: list[str] = cast(list[str], safe_get_attr(release_obj, "genres", []) or [])
        if not genres:
            genres = cast(list[str], safe_get_attr(release_obj, "genre", []) or [])

        # Get label and catalog number
        label: str | None = extract_first_item(release_obj, "labels")
        catno: str | None = extract_first_item(release_obj, "labels", "catno")

        # Get country
        country: str | None = cast(str | None, safe_get_attr(release_obj, "country"))

        # Get image URLs
        thumb_url: str | None = cast(str | None, safe_get_attr(release_obj, "thumb"))
        cover_url: str | None = extract_first_item(release_obj, "images", "uri")

        # Get URI
        uri: str | None = cast(str | None, safe_get_attr(release_obj, "uri"))
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

        # Use protocol for objects with date_added
        def has_date_added(obj: Any) -> TypeGuard[HasDateAdded]:
            return hasattr(obj, "date_added")

        # Get collection-specific metadata
        date_added: datetime | None = None
        if has_date_added(release_obj):
            with contextlib.suppress(ValueError, AttributeError):
                date_str = cast(str, safe_get_attr(release_obj, "date_added", ""))
                if date_str:
                    date_str = date_str.replace("Z", "+00:00")
                    date_added = datetime.fromisoformat(date_str)

        # Get rating and notes
        rating: int | None = cast(int | None, safe_get_attr(release_obj, "rating"))
        notes: str | None = cast(str | None, safe_get_attr(release_obj, "notes"))

        return cls(
            release=release,
            is_owned=is_owned,
            is_wanted=is_wanted,
            date_added=date_added,
            rating=rating,
            notes=notes,
        )

    @classmethod
    def from_discogs_dict(
        cls, release_dict: dict[str, Any], is_owned: bool = False, is_wanted: bool = False
    ) -> "DiscogsVinyl":
        """Create a DiscogsVinyl from a Discogs API response dictionary.

        Args:
            release_dict: Dictionary with release data from the Discogs API
            is_owned: Whether this vinyl is in the user's collection
            is_wanted: Whether this vinyl is in the user's wantlist

        Returns:
            DiscogsVinyl instance
        """
        # Convert the release dictionary to our release model
        release = DiscogsRelease.from_discogs_dict(release_dict)

        # Extract collection/wantlist specific metadata
        date_added = None
        if "date_added" in release_dict:
            try:
                from datetime import datetime

                date_added = datetime.fromisoformat(
                    release_dict["date_added"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Get rating and notes
        rating = release_dict.get("rating")
        notes = release_dict.get("notes")

        return cls(
            release=release,
            is_owned=is_owned,
            is_wanted=is_wanted,
            date_added=date_added,
            rating=rating,
            notes=notes,
        )
