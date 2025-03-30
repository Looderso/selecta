# src/selecta/ui/components/playlist/spotify/spotify_playlist_data_provider.py
"""Spotify playlist data provider implementation."""

from typing import Any

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.spotify.spotify_playlist_item import SpotifyPlaylistItem
from selecta.ui.components.playlist.spotify.spotify_track_item import SpotifyTrackItem
from selecta.ui.components.playlist.track_item import TrackItem


class SpotifyPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for Spotify playlists."""

    def __init__(self, client: SpotifyClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Spotify playlist data provider.

        Args:
            client: Optional SpotifyClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Spotify client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("spotify", settings_repo)
            if not isinstance(client_instance, SpotifyClient):
                raise ValueError("Could not create Spotify client")
            self.client = client_instance
        else:
            self.client = client

        # Initialize the abstract provider
        super().__init__(self.client, cache_timeout)

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from Spotify API.

        Returns:
            List of playlist items
        """
        if not self._ensure_authenticated():
            return []

        # Get all playlists from Spotify
        spotify_playlists = self.client.get_playlists()
        playlist_items = []

        for sp_playlist in spotify_playlists:
            # Convert to PlaylistItem
            playlist_items.append(
                SpotifyPlaylistItem(
                    name=sp_playlist["name"],
                    item_id=sp_playlist["id"],
                    owner=sp_playlist["owner"]["display_name"],
                    description=sp_playlist.get("description", ""),
                    is_collaborative=sp_playlist.get("collaborative", False),
                    is_public=sp_playlist.get("public", True),
                    track_count=sp_playlist["tracks"]["total"],
                    images=sp_playlist.get("images", []),
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from Spotify API.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self._ensure_authenticated():
            return []

        # Get the tracks from Spotify
        spotify_tracks = self.client.get_playlist_tracks(str(playlist_id))

        # Convert tracks to TrackItem objects
        track_items = []
        for sp_track in spotify_tracks:
            # Convert to TrackItem
            track_items.append(
                SpotifyTrackItem(
                    track_id=sp_track.id,
                    title=sp_track.name,
                    artist=", ".join(sp_track.artist_names),
                    album=sp_track.album_name,
                    duration_ms=sp_track.duration_ms,
                    added_at=sp_track.added_at,
                    uri=sp_track.uri,
                    popularity=sp_track.popularity,
                    explicit=sp_track.explicit,  # type: ignore
                    preview_url=sp_track.preview_url,
                )
            )

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Spotify"
