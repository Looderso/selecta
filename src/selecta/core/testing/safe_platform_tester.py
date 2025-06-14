"""Safe platform testing framework with comprehensive protection and cleanup.

This module provides a testing framework that safely interacts with platform APIs
while ensuring no real user data can be accidentally modified or deleted.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.testing.safety_guard import (
    OperationType,
    SafetyConfig,
    SafetyGuard,
    SafetyLevel,
    create_test_playlist_name,
    get_safety_guard,
)


class PlatformTestSession:
    """A safe testing session for platform operations.

    This class manages a testing session with automatic cleanup and safety enforcement.
    All operations are logged and can be rolled back if needed.
    """

    def __init__(self, safety_guard: SafetyGuard | None = None):
        """Initialize the test session.

        Args:
            safety_guard: Safety guard instance, uses global if None
        """
        self.safety_guard = safety_guard or get_safety_guard()
        self.settings_repo = SettingsRepository()
        self.created_playlists: dict[str, list[str]] = {}  # platform -> playlist_ids
        self.session_active = False

        # Platform clients (lazy loaded)
        self._spotify_client: SpotifyClient | None = None
        self._rekordbox_client: RekordboxClient | None = None
        self._youtube_client: YouTubeClient | None = None
        self._discogs_client: DiscogsClient | None = None

    def __enter__(self) -> "PlatformTestSession":
        """Enter the test session context."""
        self.start_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the test session context with cleanup."""
        self.end_session(cleanup=True)

    def start_session(self) -> None:
        """Start the test session."""
        if self.session_active:
            raise RuntimeError("Test session already active")

        logger.info("🧪 Starting safe platform test session")
        self.safety_guard.validate_test_environment()
        self.session_active = True

        # Clear operation log
        self.safety_guard.clear_operation_log()

    def end_session(self, cleanup: bool = True) -> None:
        """End the test session.

        Args:
            cleanup: Whether to clean up created test playlists
        """
        if not self.session_active:
            return

        logger.info("🧹 Ending test session")

        if cleanup:
            self.cleanup_all_test_playlists()

        # Log session summary
        operations = self.safety_guard.get_operation_log()
        logger.info(f"Session completed with {len(operations)} operations")

        self.session_active = False

    @property
    def spotify_client(self) -> SpotifyClient:
        """Get Spotify client with safety checks."""
        if self._spotify_client is None:
            self._spotify_client = SpotifyClient(self.settings_repo)
            if not self._spotify_client.is_authenticated():
                raise RuntimeError("Spotify not authenticated - run 'selecta auth spotify' first")
        return self._spotify_client

    @property
    def rekordbox_client(self) -> RekordboxClient:
        """Get Rekordbox client with safety checks."""
        if self._rekordbox_client is None:
            self._rekordbox_client = RekordboxClient(self.settings_repo)
            if not self._rekordbox_client.is_authenticated():
                raise RuntimeError("Rekordbox not accessible - ensure database is available")
        return self._rekordbox_client

    @property
    def youtube_client(self) -> YouTubeClient:
        """Get YouTube client with safety checks."""
        if self._youtube_client is None:
            self._youtube_client = YouTubeClient(self.settings_repo)
            if not self._youtube_client.is_authenticated():
                raise RuntimeError("YouTube not authenticated - run 'selecta auth youtube' first")
        return self._youtube_client

    @property
    def discogs_client(self) -> DiscogsClient:
        """Get Discogs client with safety checks."""
        if self._discogs_client is None:
            self._discogs_client = DiscogsClient(self.settings_repo)
            if not self._discogs_client.is_authenticated():
                raise RuntimeError("Discogs not authenticated - run 'selecta auth discogs' first")
        return self._discogs_client

    def create_safe_playlist(self, platform: str, base_name: str, **kwargs) -> str:
        """Create a test playlist with safety checks.

        Args:
            platform: Platform name (spotify, rekordbox, youtube)
            base_name: Base name for the playlist
            **kwargs: Additional arguments for playlist creation

        Returns:
            Playlist ID of the created playlist

        Raises:
            ValueError: If platform is not supported
            RuntimeError: If session is not active
        """
        if not self.session_active:
            raise RuntimeError("Test session not active")

        # Create safe playlist name
        safe_name = create_test_playlist_name(base_name)

        # Verify operation is safe
        self.safety_guard.verify_test_playlist(safe_name, OperationType.CREATE)

        # Create playlist on appropriate platform
        playlist_id = None

        if platform == "spotify":
            playlist = self.spotify_client.create_playlist(name=safe_name, **kwargs)
            playlist_id = playlist.id

        elif platform == "rekordbox":
            # Rekordbox create_playlist doesn't support extra kwargs like description
            playlist = self.rekordbox_client.create_playlist(safe_name)
            playlist_id = str(playlist.id)

        elif platform == "youtube":
            playlist = self.youtube_client.create_playlist(name=safe_name, **kwargs)
            playlist_id = playlist.id

        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Track created playlist for cleanup
        if platform not in self.created_playlists:
            self.created_playlists[platform] = []
        self.created_playlists[platform].append(playlist_id)

        logger.info(f"✅ Created test playlist '{safe_name}' on {platform}: {playlist_id}")
        return playlist_id

    def add_tracks_to_playlist(self, platform: str, playlist_id: str, track_ids: list[str]) -> bool:
        """Add tracks to a test playlist with safety checks.

        Args:
            platform: Platform name
            playlist_id: Playlist ID
            track_ids: List of track IDs to add

        Returns:
            True if successful
        """
        if not self.session_active:
            raise RuntimeError("Test session not active")

        # Get playlist name for safety check
        playlist_name = self._get_playlist_name(platform, playlist_id)
        self.safety_guard.verify_test_playlist(playlist_name, OperationType.MODIFY)

        # Add tracks on appropriate platform
        if platform == "spotify":
            return self.spotify_client.add_tracks_to_playlist(playlist_id, track_ids)
        elif platform == "rekordbox":
            return self.rekordbox_client.add_tracks_to_playlist(playlist_id, track_ids)
        elif platform == "youtube":
            return self.youtube_client.add_tracks_to_playlist(playlist_id, track_ids)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _get_playlist_name(self, platform: str, playlist_id: str) -> str:
        """Get playlist name for a given platform and ID.

        Args:
            platform: Platform name
            playlist_id: Playlist ID

        Returns:
            Playlist name
        """
        try:
            if platform == "spotify":
                playlist = self.spotify_client.get_playlist(playlist_id)
                return playlist.name
            elif platform == "rekordbox":
                playlist = self.rekordbox_client.get_playlist_by_id(playlist_id)
                return playlist.name if playlist else f"Unknown-{playlist_id}"
            elif platform == "youtube":
                playlist = self.youtube_client.get_playlist(playlist_id)
                return playlist.title if playlist else f"YouTube-{playlist_id}"
            else:
                return f"Unknown-{playlist_id}"
        except Exception as e:
            logger.warning(f"Could not get playlist name for {platform}:{playlist_id}: {e}")
            return f"Unknown-{playlist_id}"

    def cleanup_all_test_playlists(self) -> None:
        """Clean up all test playlists created during this session."""
        logger.info("🧹 Cleaning up test playlists...")

        total_cleaned = 0
        for platform, playlist_ids in self.created_playlists.items():
            cleaned = self._cleanup_platform_playlists(platform, playlist_ids)
            total_cleaned += cleaned

        logger.info(f"✅ Cleaned up {total_cleaned} test playlists")
        self.created_playlists.clear()

    def _cleanup_platform_playlists(self, platform: str, playlist_ids: list[str]) -> int:
        """Clean up playlists for a specific platform.

        Args:
            platform: Platform name
            playlist_ids: List of playlist IDs to clean up

        Returns:
            Number of playlists successfully cleaned up
        """
        cleaned_count = 0

        for playlist_id in playlist_ids:
            try:
                # Get playlist name for safety verification
                playlist_name = self._get_playlist_name(platform, playlist_id)

                # Verify it's safe to delete (should be a test playlist)
                if not self.safety_guard.is_test_playlist(playlist_name):
                    logger.error(f"❌ Refusing to delete non-test playlist: {playlist_name}")
                    continue

                # Delete the playlist (note: not all platforms support deletion)
                success = self._delete_playlist(platform, playlist_id, playlist_name)
                if success:
                    cleaned_count += 1
                    logger.info(f"🗑️  Deleted test playlist: {playlist_name}")
                else:
                    logger.warning(f"⚠️  Could not delete playlist: {playlist_name}")

            except Exception as e:
                logger.exception(f"Error cleaning up playlist {playlist_id} on {platform}: {e}")

        return cleaned_count

    def _delete_playlist(self, platform: str, playlist_id: str, playlist_name: str) -> bool:
        """Delete a playlist on the specified platform.

        Args:
            platform: Platform name
            playlist_id: Playlist ID
            playlist_name: Playlist name (for logging)

        Returns:
            True if successfully deleted
        """
        # Verify one more time that this is a test playlist
        self.safety_guard.verify_test_playlist(playlist_name, OperationType.DELETE)

        try:
            if platform == "spotify":
                # Spotify supports unfollowing playlists (which removes them from library)
                return self.spotify_client.delete_playlist(playlist_id)

            elif platform == "rekordbox":
                # Rekordbox supports playlist deletion
                return self.rekordbox_client.delete_playlist(playlist_id, force=True)

            elif platform == "youtube":
                # YouTube supports playlist deletion
                return self.youtube_client.delete_playlist(playlist_id)

            else:
                logger.warning(f"Playlist deletion not implemented for platform: {platform}")
                return False

        except Exception as e:
            logger.exception(f"Error deleting playlist {playlist_id}: {e}")
            return False

    def search_for_test_tracks(self, platform: str, query: str = "test", limit: int = 5) -> list[Any]:
        """Search for tracks that can be used in tests.

        Args:
            platform: Platform to search on
            query: Search query
            limit: Maximum number of results

        Returns:
            List of track objects
        """
        if platform == "spotify":
            return self.spotify_client.search_tracks(query, limit)
        elif platform == "rekordbox":
            return self.rekordbox_client.search_tracks(query, limit)
        elif platform == "youtube":
            return self.youtube_client.search_tracks(query, limit)
        else:
            raise ValueError(f"Unsupported platform: {platform}")


@contextmanager
def safe_platform_test(safety_level: SafetyLevel = SafetyLevel.TEST_ONLY) -> Generator[PlatformTestSession, None, None]:
    """Context manager for safe platform testing.

    Args:
        safety_level: Safety level for the test session

    Yields:
        PlatformTestSession instance

    Example:
        with safe_platform_test() as session:
            playlist_id = session.create_safe_playlist("spotify", "My Test Playlist")
            # All test playlists are automatically cleaned up
    """
    # Create safety configuration
    config = SafetyConfig(
        test_markers=["🧪", "[TEST]", "SELECTA_TEST_"],
        safety_level=safety_level,
        require_confirmation=False,  # Automated tests shouldn't require confirmation
        dry_run_mode=False,
        max_test_playlists=50,
        emergency_stop_enabled=True,
    )

    # Create safety guard with test configuration
    from selecta.core.testing.safety_guard import reset_safety_guard

    safety_guard = reset_safety_guard(config)

    # Create and manage test session
    session = PlatformTestSession(safety_guard)

    try:
        with session:
            yield session
    except Exception as e:
        logger.exception(f"Error in platform test session: {e}")
        # Emergency stop to prevent further operations
        safety_guard.emergency_stop()
        raise
    finally:
        # Ensure cleanup happens even if there's an error
        if session.session_active:
            session.end_session(cleanup=True)
