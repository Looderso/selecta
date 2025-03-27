# src/selecta/ui/components/playlist/playlist_data_provider.py
from abc import ABC, abstractmethod
from typing import Any

from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class PlaylistDataProvider(ABC):
    """Interface for providing playlist data to the playlist component."""

    @abstractmethod
    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        pass
