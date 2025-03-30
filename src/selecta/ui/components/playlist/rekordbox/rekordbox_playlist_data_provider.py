# src/selecta/ui/components/playlist/rekordbox/rekordbox_playlist_data_provider.py
from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_playlist_item import RekordboxPlaylistItem
from selecta.ui.components.playlist.rekordbox.rekordbox_track_item import RekordboxTrackItem
from selecta.ui.components.playlist.track_item import TrackItem


class RekordboxPlaylistDataProvider(PlaylistDataProvider):
    """Data provider for Rekordbox playlists."""

    def __init__(self, client: RekordboxClient | None = None):
        """Initialize the Rekordbox playlist data provider.

        Args:
            client: Optional RekordboxClient instance
        """
        # Create or use the provided Rekordbox client
        if client is None:
            settings_repo = SettingsRepository()
            self.client = PlatformFactory.create("rekordbox", settings_repo)
            if not isinstance(self.client, RekordboxClient):
                raise ValueError("Could not create Rekordbox client")
        else:
            self.client = client

        # Check authentication
        if not self.client.is_authenticated():
            logger.warning("Rekordbox client is not authenticated")

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists from Rekordbox.

        Returns:
            List of playlist items
        """
        if not self.client.is_authenticated():
            logger.error("Rekordbox client is not authenticated")
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

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        if not self.client.is_authenticated():
            logger.error("Rekordbox client is not authenticated")
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
