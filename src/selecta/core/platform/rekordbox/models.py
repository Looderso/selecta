"""Rekordbox data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Protocol,
    TypeGuard,
    runtime_checkable,
)


@runtime_checkable
class RekordboxArtist(Protocol):
    """Protocol for Rekordbox artist objects."""

    ID: int
    Name: str


@runtime_checkable
class RekordboxAlbum(Protocol):
    """Protocol for Rekordbox album objects."""

    ID: int
    Name: str


@runtime_checkable
class RekordboxGenre(Protocol):
    """Protocol for Rekordbox genre objects."""

    ID: int
    Name: str


@runtime_checkable
class RekordboxKey(Protocol):
    """Protocol for Rekordbox key objects."""

    ID: int
    ScaleName: str


@runtime_checkable
class RekordboxContent(Protocol):
    """Protocol for Rekordbox content (track) objects."""

    ID: int
    Title: str
    Artist: RekordboxArtist | None
    Album: RekordboxAlbum | None
    Genre: RekordboxGenre | None
    Duration: int
    BPM: float | None
    Key: RekordboxKey | None
    FolderPath: str | None
    Rating: int | None
    DateCreated: str | datetime | None


@runtime_checkable
class RekordboxPlaylistItem(Protocol):
    """Protocol for Rekordbox playlist objects."""

    ID: str
    Name: str
    Attribute: int
    ParentID: str
    Seq: int
    created_at: datetime | None
    updated_at: datetime | None


def is_rekordbox_artist(obj: Any) -> TypeGuard[RekordboxArtist]:
    """Check if an object is a Rekordbox artist.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return isinstance(obj, object) and hasattr(obj, "ID") and hasattr(obj, "Name")


def is_rekordbox_album(obj: Any) -> TypeGuard[RekordboxAlbum]:
    """Check if an object is a Rekordbox album.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return isinstance(obj, object) and hasattr(obj, "ID") and hasattr(obj, "Name")


def is_rekordbox_genre(obj: Any) -> TypeGuard[RekordboxGenre]:
    """Check if an object is a Rekordbox genre.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return isinstance(obj, object) and hasattr(obj, "ID") and hasattr(obj, "Name")


def is_rekordbox_key(obj: Any) -> TypeGuard[RekordboxKey]:
    """Check if an object is a Rekordbox key.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return isinstance(obj, object) and hasattr(obj, "ID") and hasattr(obj, "ScaleName")


def is_rekordbox_content(obj: Any) -> TypeGuard[RekordboxContent]:
    """Check if an object is a Rekordbox content.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return isinstance(obj, object) and hasattr(obj, "ID") and hasattr(obj, "Title")


def is_rekordbox_playlist(obj: Any) -> TypeGuard[RekordboxPlaylistItem]:
    """Check if an object is a Rekordbox playlist.

    Args:
        obj: Object to check

    Returns:
        True if the object has the necessary attributes
    """
    return (
        isinstance(obj, object)
        and hasattr(obj, "ID")
        and hasattr(obj, "Name")
        and hasattr(obj, "Attribute")
    )


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

    def to_dict(self) -> dict[str, Any]:
        """Convert track to dictionary for serialization.

        Returns:
            Dictionary representation of the track
        """
        return {
            "id": self.id,
            "title": self.title,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "genre": self.genre,
            "duration_ms": self.duration_ms,
            "bpm": self.bpm,
            "key": self.key,
            "folder_path": self.folder_path,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_rekordbox_content(cls, content: Any) -> "RekordboxTrack":
        """Create a RekordboxTrack from a DjmdContent object.

        Args:
            content: DjmdContent object from pyrekordbox

        Returns:
            RekordboxTrack instance
        """
        if not is_rekordbox_content(content):
            raise ValueError("Invalid Rekordbox content object")

        # Extract basic information
        track_id: int = getattr(content, "ID", 0)
        title: str = getattr(content, "Title", "")

        # Get artist
        artist_name: str = "Unknown Artist"
        if content.Artist is not None and is_rekordbox_artist(content.Artist):
            artist_name = content.Artist.Name

        # Get album
        album_name: str | None = None
        if content.Album is not None and is_rekordbox_album(content.Album):
            album_name = content.Album.Name

        # Get genre
        genre: str | None = None
        if content.Genre is not None and is_rekordbox_genre(content.Genre):
            genre = content.Genre.Name

        # Get duration
        duration_ms: int | None = getattr(content, "Duration", 0)
        if duration_ms and duration_ms < 10000:
            # TODO Check me
            duration_ms = int(duration_ms * 1000)

        # Get other track details
        bpm: float | None = getattr(content, "BPM", None)

        # Get key
        key: str | None = None
        if content.Key is not None and is_rekordbox_key(content.Key):
            key = content.Key.ScaleName

        # Get path and rating
        folder_path: str | None = getattr(content, "FolderPath", None)
        rating: int | None = getattr(content, "Rating", None)

        # Get created date
        date_created = getattr(content, "DateCreated", None)
        created_at: datetime | None = None

        if isinstance(date_created, datetime):
            created_at = date_created
        elif isinstance(date_created, str):
            try:
                created_at = datetime.fromisoformat(date_created)
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
        if not is_rekordbox_playlist(playlist):
            raise ValueError("Invalid Rekordbox playlist object")

        playlist_id: str = getattr(playlist, "ID", "")
        name: str = getattr(playlist, "Name", "")

        # Check if attribute is a bool or needs conversion
        # Some versions return an integer for is_folder where 1 means folder
        attribute: int = getattr(playlist, "Attribute", 0)
        is_folder: bool = bool(attribute == 1)

        parent_id: str = getattr(playlist, "ParentID", "root")
        position: int = getattr(playlist, "Seq", 0)

        created_at: datetime | None = getattr(playlist, "created_at", None)
        updated_at: datetime | None = getattr(playlist, "updated_at", None)

        track_list: list[RekordboxTrack] = tracks if tracks is not None else []

        return cls(
            id=playlist_id,
            name=name,
            is_folder=is_folder,
            parent_id=parent_id,
            tracks=track_list,
            position=position,
            created_at=created_at,
            updated_at=updated_at,
        )
