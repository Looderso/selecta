"""Spotify data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SpotifyTrack:
    """Representation of a Spotify track."""

    id: str
    name: str
    uri: str
    artist_names: list[str]
    album_name: str
    album_id: str | None = None
    duration_ms: int | None = None
    popularity: int | None = None
    explicit: bool | None = None
    preview_url: str | None = None
    added_at: datetime | None = None

    @classmethod
    def from_spotify_dict(
        cls, track_dict: dict[str, Any], added_at: datetime | None = None
    ) -> "SpotifyTrack":
        """Create a SpotifyTrack from a Spotify API response dictionary.

        Args:
            track_dict: Spotify track dictionary from the API
            added_at: When the track was added to a playlist (if applicable)

        Returns:
            SpotifyTrack instance
        """
        # Handle both direct track objects and playlist track objects
        track = track_dict.get("track", track_dict)
        # Get artist names
        artist_names = [artist["name"] for artist in track.get("artists", [])]

        # Get album info
        album = track.get("album", {})
        album_name = album.get("name", "")
        album_id = album.get("id")

        # Handle the added_at date
        parsed_added_at = added_at
        if not parsed_added_at and "added_at" in track_dict:
            try:
                # Parse ISO 8601 date string
                parsed_added_at = datetime.fromisoformat(
                    track_dict["added_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                parsed_added_at = None

        return cls(
            id=track.get("id", ""),
            name=track.get("name", ""),
            uri=track.get("uri", ""),
            artist_names=artist_names,
            album_name=album_name,
            album_id=album_id,
            duration_ms=track.get("duration_ms"),
            popularity=track.get("popularity"),
            explicit=track.get("explicit"),
            preview_url=track.get("preview_url"),
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
    def from_spotify_dict(cls, playlist_dict: dict[str, Any]) -> "SpotifyPlaylist":
        """Create a SpotifyPlaylist from a Spotify API response dictionary.

        Args:
            playlist_dict: Spotify playlist dictionary from the API

        Returns:
            SpotifyPlaylist instance
        """
        # Get owner info
        owner = playlist_dict.get("owner", {})
        owner_id = owner.get("id", "")
        owner_name = owner.get("display_name", "")

        # Get tracks count
        tracks = playlist_dict.get("tracks", {})
        tracks_count = tracks.get("total", 0)

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
    def from_spotify_dict(cls, features_dict: dict[str, Any]) -> "SpotifyAudioFeatures":
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
