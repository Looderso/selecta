# src/selecta/ui/components/playlist/spotify/spotify_playlist_data_provider.py
from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.spotify.spotify_playlist_item import SpotifyPlaylistItem
from selecta.ui.components.playlist.spotify.spotify_track_item import SpotifyTrackItem
from selecta.ui.components.playlist.track_item import TrackItem


class SpotifyPlaylistDataProvider(PlaylistDataProvider):
    """Data provider for Spotify playlists."""

    def __init__(self, client: SpotifyClient | None = None):
        """Initialize the Spotify playlist data provider.

        Args:
            client: Optional SpotifyClient instance
        """
        # Create or use the provided Spotify client
        if client is None:
            settings_repo = SettingsRepository()
            self.client = PlatformFactory.create("spotify", settings_repo)
            if not isinstance(self.client, SpotifyClient):
                raise ValueError("Could not create Spotify client")
        else:
            self.client = client

        # Check authentication
        if not self.client.is_authenticated():
            logger.warning("Spotify client is not authenticated")

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists from Spotify.

        Returns:
            List of playlist items
        """
        if not self.client.is_authenticated():
            logger.error("Spotify client is not authenticated")
            return []

        try:
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

        except Exception as e:
            logger.exception(f"Error getting Spotify playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self.client.is_authenticated():
            logger.error("Spotify client is not authenticated")
            return []

        try:
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
                        explicit=sp_track.explicit,
                        preview_url=sp_track.preview_url,
                    )
                )

            return track_items

        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Spotify"
