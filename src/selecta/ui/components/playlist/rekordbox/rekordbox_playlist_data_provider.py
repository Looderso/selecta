# src/selecta/ui/components/playlist/rekordbox/rekordbox_playlist_data_provider.py
"""Rekordbox playlist data provider implementation."""

from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_playlist_item import RekordboxPlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_track_item import RekordboxTrackItem
from selecta.ui.components.playlist.track_item import TrackItem


class RekordboxPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for Rekordbox playlists."""

    def __init__(self, client: RekordboxClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Rekordbox playlist data provider.

        Args:
            client: Optional RekordboxClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Rekordbox client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("rekordbox", settings_repo)
            if not isinstance(client_instance, RekordboxClient):
                raise ValueError("Could not create Rekordbox client")
            self.client = client_instance
        else:
            self.client = client

        # Initialize the abstract provider
        super().__init__(self.client, cache_timeout)

        # Additional cache keys specific to Rekordbox
        self._all_playlists_cache_key = "rekordbox_all_playlists"

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from Rekordbox.

        Returns:
            List of playlist items
        """
        if not self._ensure_authenticated():
            return []

        try:
            # Get all playlists from Rekordbox
            rekordbox_playlists = self.client.get_all_playlists()
            playlist_items = []

            for rb_playlist in rekordbox_playlists:
                # Convert to PlaylistItem
                playlist_items.append(
                    RekordboxPlaylistItem(
                        name=rb_playlist.name,
                        item_id=rb_playlist.id,
                        parent_id=rb_playlist.parent_id
                        if rb_playlist.parent_id != "root"
                        else None,
                        is_folder_flag=rb_playlist.is_folder,
                        track_count=len(rb_playlist.tracks),
                    )
                )

            return playlist_items

        except Exception as e:
            logger.exception(f"Error getting Rekordbox playlists: {e}")
            return []

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from Rekordbox.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self._ensure_authenticated():
            return []

        try:
            # Get the playlist from Rekordbox
            playlist = self.client.get_playlist_by_id(str(playlist_id))
            if not playlist:
                logger.error(f"Playlist not found: {playlist_id}")
                return []

            # Convert tracks to TrackItem objects
            track_items = []
            for rb_track in playlist.tracks:
                # Convert to TrackItem
                track_items.append(
                    RekordboxTrackItem(
                        track_id=rb_track.id,
                        title=rb_track.title,
                        artist=rb_track.artist_name,
                        album=rb_track.album_name,
                        duration_ms=rb_track.duration_ms,
                        bpm=rb_track.bpm,
                        key=rb_track.key,
                        path=rb_track.folder_path,
                        rating=rb_track.rating,
                        created_at=rb_track.created_at,
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
        return "Rekordbox"
