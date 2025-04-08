# src/selecta/ui/components/playlist/abstract_playlist_data_provider.py
"""Abstract implementation of PlaylistDataProvider with common functionality."""

from abc import abstractmethod
from typing import Any

from loguru import logger

from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.utils.cache_manager import CacheManager
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class AbstractPlaylistDataProvider(PlaylistDataProvider):
    """Abstract implementation of PlaylistDataProvider with caching and common functionality."""

    def __init__(self, client: AbstractPlatform | None = None, cache_timeout: float = 300.0):
        """Initialize the abstract playlist data provider.

        Args:
            client: Platform client instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        super().__init__()
        self.client = client
        self.cache = CacheManager(default_timeout=cache_timeout)

        # Common cache keys
        self._playlists_cache_key = f"{self.get_platform_name().lower()}_playlists"

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists with caching.

        Returns:
            List of playlist items
        """
        # Try to get from cache first
        if self.cache.has_valid(self._playlists_cache_key):
            return self.cache.get(self._playlists_cache_key, [])

        # Check authentication
        if not self._ensure_authenticated():
            logger.warning(f"{self.get_platform_name()} client is not authenticated")
            return []

        try:
            # Get fresh data
            playlists = self._fetch_playlists()

            # Cache the result
            self.cache.set(self._playlists_cache_key, playlists)

            return playlists
        except Exception as e:
            logger.exception(f"Error getting {self.get_platform_name()} playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist with caching.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        # Generate cache key for this playlist's tracks
        cache_key = f"{self.get_platform_name().lower()}_tracks_{playlist_id}"

        # Try to get from cache first - show cached data immediately if available
        # to prevent UI locking while data is being fetched
        if self.cache.has_valid(cache_key):
            cached_data = self.cache.get(cache_key, [])

            # Only trigger background refresh if we have data to show
            # This ensures we don't have empty loading states while refreshing
            if cached_data:
                # Trigger a background refresh after returning cached data
                # This ensures our cache stays fresh without blocking the UI
                self._trigger_background_refresh(playlist_id, cache_key)
                return cached_data
            # If cache is empty, continue to fetch new data

        # Check authentication
        if not self._ensure_authenticated():
            logger.warning(f"{self.get_platform_name()} client is not authenticated")
            return []

        try:
            # Get fresh data
            tracks = self._fetch_playlist_tracks(playlist_id)

            # Cache the result
            self.cache.set(cache_key, tracks)

            return tracks
        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def refresh(self) -> None:
        """Refresh all cached data and notify listeners."""
        # Clear the cache
        self.cache.clear()

        # Notify listeners
        self.notify_refresh_needed()

    def refresh_playlist(self, playlist_id: Any) -> None:
        """Refresh a specific playlist's tracks.

        Args:
            playlist_id: ID of the playlist to refresh
        """
        # Invalidate just this playlist's cache
        cache_key = f"{self.get_platform_name().lower()}_tracks_{playlist_id}"
        self.cache.invalidate(cache_key)

        # Notify listeners
        self.notify_refresh_needed()

    def _trigger_background_refresh(self, playlist_id: Any, cache_key: str) -> None:
        """Trigger a background refresh of a playlist's tracks.

        This ensures the cache stays fresh without blocking the UI,
        addressing the issue of playlists appearing to be stuck while loading.

        Args:
            playlist_id: The playlist ID
            cache_key: Cache key for the playlist's tracks
        """
        # Skip for non-authenticated clients (will be handled in main method)
        if not self._ensure_authenticated():
            return

        # Use ThreadManager to run the refresh in background
        from selecta.core.utils.worker import ThreadManager

        def background_refresh_task() -> None:
            try:
                # Fetch fresh data directly from source
                fresh_tracks = self._fetch_playlist_tracks(playlist_id)

                # Update cache with fresh data
                self.cache.set(cache_key, fresh_tracks)

                platform = self.get_platform_name()
                logger.debug(f"Background refresh completed for {platform} playlist {playlist_id}")
            except Exception as e:
                # Just log errors, don't interrupt the UI
                logger.error(f"Error in background refresh for {playlist_id}: {e}")

        # Run the task in background with low priority
        thread_manager = ThreadManager()
        thread_manager.run_task(background_refresh_task)

    def _ensure_authenticated(self) -> bool:
        """Ensure the client is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.client:
            return False

        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False

    @abstractmethod
    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch playlists from the platform API.

        This method should be implemented by platform-specific providers.

        Returns:
            List of playlist items
        """
        pass

    @abstractmethod
    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a playlist from the platform API.

        This method should be implemented by platform-specific providers.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        pass
