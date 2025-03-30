"""Rekordbox data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class RekordboxTrack:
    """Representation of a Rekordbox track."""

    id: int
    title: str
    artist_name: str
    album_name: str | None = None
    genre: str | None = None
    duration_ms: int | None = None
    bpm: float | None = None
    key: str | None = None
    folder_path: str | None = None
    rating: int | None = None
    created_at: datetime | None = None

    @classmethod
    def from_rekordbox_content(cls, content: Any) -> "RekordboxTrack":
        """Create a RekordboxTrack from a DjmdContent object.

        Args:
            content: DjmdContent object from pyrekordbox

        Returns:
            RekordboxTrack instance
        """
        # Extract basic information
        track_id = getattr(content, "ID", 0)
        title = getattr(content, "Title", "")

        # Get artist
        artist_name = "Unknown Artist"
        if hasattr(content, "Artist") and content.Artist is not None:
            artist_name = content.Artist.Name

        # Get album
        album_name = None
        if hasattr(content, "Album") and content.Album is not None:
            album_name = content.Album.Name

        # Get genre
        genre = None
        if hasattr(content, "Genre") and content.Genre is not None:
            genre = content.Genre.Name

        # Get duration
        duration_ms = getattr(content, "Duration", 0)
        if duration_ms and duration_ms < 10000:
            # TODO Check me
            duration_ms = int(duration_ms * 1000)

        # Get other track details
        bpm = getattr(content, "BPM", None)

        # Get key
        key = None
        if hasattr(content, "Key") and content.Key is not None:
            key = content.Key.ScaleName

        # Get path and rating
        folder_path = getattr(content, "FolderPath", None)
        rating = getattr(content, "Rating", None)

        # Get created date
        created_at = getattr(content, "DateCreated", None)
        if created_at and not isinstance(created_at, datetime) and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None

        return cls(
            id=track_id,
            title=title,
            artist_name=artist_name,
            album_name=album_name,
            genre=genre,
            duration_ms=duration_ms,
            bpm=bpm,
            key=key,
            folder_path=folder_path,
            rating=rating,
            created_at=created_at,
        )


@dataclass
class RekordboxPlaylist:
    """Representation of a Rekordbox playlist."""

    id: str
    name: str
    is_folder: bool
    parent_id: str
    tracks: list[RekordboxTrack]
    position: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_rekordbox_playlist(
        cls, playlist: Any, tracks: list[RekordboxTrack]
    ) -> "RekordboxPlaylist":
        """Create a RekordboxPlaylist from a DjmdPlaylist object.

        Args:
            playlist: DjmdPlaylist object from pyrekordbox
            tracks: List of RekordboxTrack instances in the playlist

        Returns:
            RekordboxPlaylist instance
        """
        playlist_id = getattr(playlist, "ID", "")
        name = getattr(playlist, "Name", "")
        # Check if attribute is a bool or needs conversion
        # Some versions return an integer for is_folder where 1 means folder
        attribute = getattr(playlist, "Attribute", 0)
        is_folder = bool(attribute == 1)

        parent_id = getattr(playlist, "ParentID", "root")
        position = getattr(playlist, "Seq", 0)

        created_at = getattr(playlist, "created_at", None)
        updated_at = getattr(playlist, "updated_at", None)

        if tracks is None:
            tracks = []

        return cls(
            id=playlist_id,
            name=name,
            is_folder=is_folder,
            parent_id=parent_id,
            tracks=tracks,
            position=position,
            created_at=created_at,
            updated_at=updated_at,
        )
