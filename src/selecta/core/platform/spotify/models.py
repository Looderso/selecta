"""Spotify data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict, cast


class SpotifyArtistDict(TypedDict, total=False):
    """TypedDict for Spotify artist data."""

    id: str
    name: str
    uri: str
    type: str
    href: str
    external_urls: dict[str, str]


class SpotifyAlbumDict(TypedDict, total=False):
    """TypedDict for Spotify album data."""

    id: str
    name: str
    uri: str
    type: str
    href: str
    images: list[dict[str, Any]]
    release_date: str
    artists: list[SpotifyArtistDict]
    external_urls: dict[str, str]


class SpotifyTrackDict(TypedDict, total=False):
    """TypedDict for Spotify track data."""

    id: str
    name: str
    uri: str
    href: str
    type: str
    duration_ms: int
    popularity: int
    explicit: bool
    preview_url: str
    artists: list[SpotifyArtistDict]
    album: SpotifyAlbumDict
    external_urls: dict[str, str]
    track: "SpotifyTrackDict"  # For playlist items
    added_at: str


class SpotifyTracksDict(TypedDict, total=False):
    """TypedDict for Spotify tracks container."""

    href: str
    total: int
    limit: int
    offset: int
    items: list[SpotifyTrackDict | dict[str, Any]]


class SpotifyUserDict(TypedDict, total=False):
    """TypedDict for Spotify user data."""

    id: str
    display_name: str
    uri: str
    href: str
    type: str
    external_urls: dict[str, str]


class SpotifyPlaylistDict(TypedDict, total=False):
    """TypedDict for Spotify playlist data."""

    id: str
    name: str
    description: str
    uri: str
    href: str
    type: str
    owner: SpotifyUserDict
    tracks: SpotifyTracksDict
    collaborative: bool
    public: bool
    snapshot_id: str
    images: list[dict[str, Any]]
    external_urls: dict[str, str]


class SpotifyAudioFeaturesDict(TypedDict, total=False):
    """TypedDict for Spotify audio features data."""

    id: str
    danceability: float
    energy: float
    key: int
    loudness: float
    mode: int
    speechiness: float
    acousticness: float
    instrumentalness: float
    liveness: float
    valence: float
    tempo: float
    duration_ms: int
    time_signature: int
    track_href: str
    analysis_url: str
    type: str


@dataclass
class SpotifyTrack:
    """Representation of a Spotify track."""

    id: str
    name: str
    uri: str
    artist_names: list[str]
    album_name: str
    album_id: str | None = None
    album_release_date: str | None = None
    duration_ms: int | None = None
    popularity: int | None = None
    explicit: bool | None = None
    preview_url: str | None = None
    added_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert this track to a dictionary representation.

        Returns:
            Dictionary representation of the track
        """
        result = {
            "id": self.id,
            "name": self.name,
            "uri": self.uri,
            "artist_names": self.artist_names,
            "album_name": self.album_name,
        }

        # Add optional fields if they exist
        if self.album_id:
            result["album_id"] = self.album_id
        if self.album_release_date:
            result["album_release_date"] = self.album_release_date
        if self.duration_ms:
            result["duration_ms"] = self.duration_ms
        if self.popularity:
            result["popularity"] = self.popularity
        if self.explicit is not None:
            result["explicit"] = self.explicit
        if self.preview_url:
            result["preview_url"] = self.preview_url
        if self.added_at:
            result["added_at"] = self.added_at.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpotifyTrack":
        """Create a SpotifyTrack from a dictionary.

        Args:
            data: Dictionary with track data

        Returns:
            SpotifyTrack instance
        """
        # Handle added_at if it's a string
        added_at = None
        if "added_at" in data and data["added_at"]:
            from contextlib import suppress

            with suppress(ValueError, TypeError):
                added_at = datetime.fromisoformat(data["added_at"].replace("Z", "+00:00"))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            uri=data.get("uri", ""),
            artist_names=data.get("artist_names", []),
            album_name=data.get("album_name", ""),
            album_id=data.get("album_id"),
            album_release_date=data.get("album_release_date"),
            duration_ms=data.get("duration_ms"),
            popularity=data.get("popularity"),
            explicit=data.get("explicit"),
            preview_url=data.get("preview_url"),
            added_at=added_at,
        )

    @classmethod
    def from_spotify_dict(
        cls, track_dict: SpotifyTrackDict | dict[str, Any], added_at: datetime | None = None
    ) -> "SpotifyTrack":
        """Create a SpotifyTrack from a Spotify API response dictionary.

        Args:
            track_dict: Spotify track dictionary from the API
            added_at: When the track was added to a playlist (if applicable)

        Returns:
            SpotifyTrack instance
        """
        # Handle both direct track objects and playlist track objects
        track_data: SpotifyTrackDict = cast(SpotifyTrackDict, track_dict.get("track", track_dict))

        # Get artist names
        artists: list[SpotifyArtistDict] = track_data.get("artists", [])
        artist_names: list[str] = [artist.get("name", "Unknown") for artist in artists]

        # Get album info
        album: SpotifyAlbumDict = track_data.get("album", {})
        album_name: str = album.get("name", "")
        album_id: str | None = album.get("id")
        album_release_date: str | None = album.get("release_date")

        # Handle the added_at date
        parsed_added_at: datetime | None = added_at
        if not parsed_added_at and "added_at" in track_dict:
            try:
                # Parse ISO 8601 date string
                added_at_str: str = cast(str, track_dict.get("added_at", ""))
                if added_at_str:
                    parsed_added_at = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                parsed_added_at = None

        return cls(
            id=track_data.get("id", ""),
            name=track_data.get("name", ""),
            uri=track_data.get("uri", ""),
            artist_names=artist_names,
            album_name=album_name,
            album_id=album_id,
            album_release_date=album_release_date,
            duration_ms=track_data.get("duration_ms"),
            popularity=track_data.get("popularity"),
            explicit=track_data.get("explicit"),
            preview_url=track_data.get("preview_url"),
            added_at=parsed_added_at,
        )


@dataclass
class SpotifyPlaylist:
    """Representation of a Spotify playlist."""

    id: str
    name: str
    description: str
    owner_id: str
    owner_name: str
    uri: str
    collaborative: bool
    public: bool
    tracks_count: int
    snapshot_id: str
    images: list[dict[str, Any]]

    @classmethod
    def from_spotify_dict(
        cls, playlist_dict: SpotifyPlaylistDict | dict[str, Any]
    ) -> "SpotifyPlaylist":
        """Create a SpotifyPlaylist from a Spotify API response dictionary.

        Args:
            playlist_dict: Spotify playlist dictionary from the API

        Returns:
            SpotifyPlaylist instance
        """
        # Get owner info
        owner: SpotifyUserDict = playlist_dict.get("owner", {})
        owner_id: str = owner.get("id", "")
        owner_name: str = owner.get("display_name", "")

        # Get tracks count
        tracks: SpotifyTracksDict = playlist_dict.get("tracks", {})
        tracks_count: int = tracks.get("total", 0)

        return cls(
            id=playlist_dict.get("id", ""),
            name=playlist_dict.get("name", ""),
            description=playlist_dict.get("description", ""),
            owner_id=owner_id,
            owner_name=owner_name,
            uri=playlist_dict.get("uri", ""),
            collaborative=playlist_dict.get("collaborative", False),
            public=playlist_dict.get("public", False),
            tracks_count=tracks_count,
            snapshot_id=playlist_dict.get("snapshot_id", ""),
            images=playlist_dict.get("images", []),
        )


@dataclass
class SpotifyAudioFeatures:
    """Audio features for a Spotify track."""

    track_id: str
    danceability: float
    energy: float
    key: int
    loudness: float
    mode: int
    speechiness: float
    acousticness: float
    instrumentalness: float
    liveness: float
    valence: float
    tempo: float
    duration_ms: int
    time_signature: int

    @classmethod
    def from_spotify_dict(
        cls, features_dict: SpotifyAudioFeaturesDict | dict[str, Any]
    ) -> "SpotifyAudioFeatures":
        """Create SpotifyAudioFeatures from a Spotify API response dictionary.

        Args:
            features_dict: Spotify audio features dictionary from the API

        Returns:
            SpotifyAudioFeatures instance
        """
        return cls(
            track_id=features_dict.get("id", ""),
            danceability=features_dict.get("danceability", 0.0),
            energy=features_dict.get("energy", 0.0),
            key=features_dict.get("key", 0),
            loudness=features_dict.get("loudness", 0.0),
            mode=features_dict.get("mode", 0),
            speechiness=features_dict.get("speechiness", 0.0),
            acousticness=features_dict.get("acousticness", 0.0),
            instrumentalness=features_dict.get("instrumentalness", 0.0),
            liveness=features_dict.get("liveness", 0.0),
            valence=features_dict.get("valence", 0.0),
            tempo=features_dict.get("tempo", 0.0),
            duration_ms=features_dict.get("duration_ms", 0),
            time_signature=features_dict.get("time_signature", 4),
        )
