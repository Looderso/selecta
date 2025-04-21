"""Helper functions for search components."""

from typing import Any, TypeVar, cast

T = TypeVar("T")


def get_largest_image_url(images: list[dict[str, Any]]) -> str | None:
    """Get the URL of the largest image from a list of images.

    Args:
        images: List of image dictionaries, each containing 'url', 'width', and 'height'

    Returns:
        URL of the largest image, or None if no images are available
    """
    if not images:
        return None

    # Find largest image by width
    sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)

    # Return URL of largest image
    return sorted_images[0].get("url")


def ensure_str(value: Any) -> str:
    """Ensure a value is a string.

    Args:
        value: Any value

    Returns:
        String representation of the value, or empty string if value is None
    """
    if value is None:
        return ""
    if isinstance(value, str | int | float | bool):
        return str(value)
    if isinstance(value, list):
        return ", ".join(ensure_str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {ensure_str(v)}" for k, v in value.items())
    return str(value)


def extract_artist_names(track_data: dict[str, Any]) -> str:
    """Extract artist names from track data.

    Handles different formats of artist data in various platforms.

    Args:
        track_data: Track data dictionary

    Returns:
        Comma-separated string of artist names
    """
    # Handle Spotify-style artist list
    if "artists" in track_data and isinstance(track_data["artists"], list):
        artists = track_data["artists"]
        if artists and isinstance(artists[0], dict) and "name" in artists[0]:
            return ", ".join(a.get("name", "") for a in artists if a.get("name"))

    # Handle YouTube-style channel title
    if "snippet" in track_data and "channelTitle" in track_data["snippet"]:
        return cast(str, track_data["snippet"]["channelTitle"])

    # Handle artist_name field (some internal formats)
    if "artist_name" in track_data:
        return ensure_str(track_data["artist_name"])

    # Handle artist field
    if "artist" in track_data:
        return ensure_str(track_data["artist"])

    # Handle Discogs-style data
    if "basic_information" in track_data:
        basic_info = track_data["basic_information"]
        if "artists" in basic_info and isinstance(basic_info["artists"], list):
            return ", ".join(a.get("name", "") for a in basic_info["artists"] if a.get("name"))

    # Default empty if no artist found
    return ""


def extract_title(track_data: dict[str, Any]) -> str:
    """Extract title from track data.

    Handles different formats of title data in various platforms.

    Args:
        track_data: Track data dictionary

    Returns:
        Title string
    """
    # Handle Spotify-style name field
    if "name" in track_data:
        return ensure_str(track_data["name"])

    # Handle YouTube-style snippet title
    if "snippet" in track_data and "title" in track_data["snippet"]:
        return ensure_str(track_data["snippet"]["title"])

    # Handle title field
    if "title" in track_data:
        return ensure_str(track_data["title"])

    # Handle Discogs-style data
    if "basic_information" in track_data and "title" in track_data["basic_information"]:
        return ensure_str(track_data["basic_information"]["title"])

    # Default empty if no title found
    return ""
