"""Abstract base class for platform integrations."""

from abc import ABC, abstractmethod
from typing import TypeVar

from selecta.core.data.repositories.settings_repository import SettingsRepository

# Type variable for platform-specific track models
T = TypeVar("T")
P = TypeVar("P")  # For playlist models


class AbstractPlatform(ABC):
    """Abstract base class for platform-specific clients (Spotify, Rekordbox, Discogs).

    This class defines the common interface that all platform integrations must implement
    for authentication, playlist management, and track synchronization.
    """

    def __init__(self, settings_repo: SettingsRepository | None = None):
        """Initializes the platform with the settings.

        Args:
            settings_repo (SettingsRepository | None, optional): Repository for accessing
                settings (optional).
        """
        self.settings_repo = settings_repo or SettingsRepository()

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials.

        Returns:
            True if authenticated, False otherwise
        """
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """Perform the authentication flow for this platform.

        Returns:
            True if authentication was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_all_playlists(self) -> list[P]:
        """Get all playlists from this platform.

        Returns:
            A list of platform-specific playlist objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> list[T]:
        """Get all tracks in a specific playlist.

        Args:
            playlist_id: The platform-specific playlist ID

        Returns:
            A list of platform-specific track objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def search_tracks(self, query: str, limit: int = 10) -> list[T]:
        """Search for tracks on this platform.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            A list of platform-specific track objects matching the query

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def create_playlist(self, name: str, description: str = "") -> P:
        """Create a new playlist on this platform.

        Args:
            name: Name of the playlist
            description: Optional description

        Returns:
            The created playlist object

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Add tracks to a playlist on this platform.

        Args:
            playlist_id: The platform-specific playlist ID
            track_ids: List of platform-specific track IDs

        Returns:
            True if successful

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Remove tracks from a playlist on this platform.

        Args:
            playlist_id: The platform-specific playlist ID
            track_ids: List of platform-specific track IDs

        Returns:
            True if successful

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def import_playlist_to_local(self, platform_playlist_id: str) -> tuple[list[T], P]:
        """Import a platform playlist to the local database.

        Args:
            platform_playlist_id: Platform-specific playlist ID

        Returns:
            A tuple of (list of platform track objects, playlist object)

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass

    @abstractmethod
    def export_tracks_to_playlist(
        self, playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None
    ) -> str:
        """Export tracks to a playlist on this platform.

        Args:
            playlist_name: Name to use for the playlist
            track_ids: List of platform-specific track IDs
            existing_playlist_id: Optional ID of an existing playlist to update

        Returns:
            The platform-specific playlist ID

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        pass
