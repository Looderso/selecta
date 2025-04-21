"""Platform initialization module.

This module handles the initialization of platform providers and clients,
registering them with the platform registry.
"""

from loguru import logger

from selecta.ui.components.playlist.interfaces import PlatformCapability
from selecta.ui.components.playlist.platform.platform_registry import get_platform_registry


def initialize_platforms(enabled_platforms: list[str] | None = None) -> None:
    """Initialize all platform providers and register them with the registry.

    Args:
        enabled_platforms: List of platform names to enable, or None for all
    """
    registry = get_platform_registry()

    # If no enabled platforms specified, enable all
    if enabled_platforms is None:
        enabled_platforms = ["library", "spotify", "rekordbox", "discogs", "youtube"]

    # Convert to lowercase for consistency
    enabled_platforms = [p.lower() for p in enabled_platforms]

    # Initialize Library provider (always available)
    if "library" in enabled_platforms:
        _initialize_library_provider(registry)

    # Initialize Spotify provider
    if "spotify" in enabled_platforms:
        _initialize_spotify_provider(registry)

    # Initialize Rekordbox provider
    if "rekordbox" in enabled_platforms:
        _initialize_rekordbox_provider(registry)

    # Initialize Discogs provider
    if "discogs" in enabled_platforms:
        _initialize_discogs_provider(registry)

    # Initialize YouTube provider
    if "youtube" in enabled_platforms:
        _initialize_youtube_provider(registry)

    logger.info(f"Initialized {len(enabled_platforms)} platform providers")


def _initialize_library_provider(registry) -> None:
    """Initialize the Library provider.

    Args:
        registry: The platform registry
    """
    try:
        # Import the provider class from the refactored module
        from selecta.ui.components.playlist.library.library_data_provider import LibraryDataProvider

        # Register the provider with capabilities
        registry.register_provider(
            platform_name="library",
            provider_class=LibraryDataProvider,
            capabilities=[
                PlatformCapability.IMPORT_PLAYLISTS,
                PlatformCapability.EXPORT_PLAYLISTS,
                PlatformCapability.SYNC_PLAYLISTS,
                PlatformCapability.CREATE_PLAYLISTS,
                PlatformCapability.DELETE_PLAYLISTS,
                PlatformCapability.MODIFY_PLAYLISTS,
                PlatformCapability.IMPORT_TRACKS,
                PlatformCapability.EXPORT_TRACKS,
                PlatformCapability.SEARCH,
                PlatformCapability.FOLDERS,
                PlatformCapability.COVER_ART,
                PlatformCapability.RATINGS,
            ],
        )

        logger.info("Registered Library provider")
    except Exception as e:
        logger.error(f"Failed to initialize Library provider: {e}")


def _initialize_spotify_provider(registry) -> None:
    """Initialize the Spotify provider.

    Args:
        registry: The platform registry
    """
    try:
        # Import the provider class and client class
        from selecta.core.platform.spotify.client import SpotifyClient
        from selecta.ui.components.playlist.platform.spotify.spotify_data_provider import (
            SpotifyDataProvider,
        )

        # Register the client
        registry.register_client("spotify", SpotifyClient)

        # Register the provider with capabilities
        registry.register_provider(
            platform_name="spotify",
            provider_class=SpotifyDataProvider,
            capabilities=[
                PlatformCapability.IMPORT_PLAYLISTS,
                PlatformCapability.EXPORT_PLAYLISTS,
                PlatformCapability.SYNC_PLAYLISTS,
                PlatformCapability.IMPORT_TRACKS,
                PlatformCapability.SEARCH,
                PlatformCapability.COVER_ART,
            ],
        )

        logger.info("Registered Spotify provider")
    except Exception as e:
        logger.error(f"Failed to initialize Spotify provider: {e}")


def _initialize_rekordbox_provider(registry) -> None:
    """Initialize the Rekordbox provider.

    Args:
        registry: The platform registry
    """
    try:
        # Import the provider class and client class
        from selecta.core.platform.rekordbox.client import RekordboxClient
        from selecta.ui.components.playlist.platform.rekordbox.rekordbox_data_provider import (
            RekordboxDataProvider,
        )

        # Register the client
        registry.register_client("rekordbox", RekordboxClient)

        # Register the provider with capabilities
        registry.register_provider(
            platform_name="rekordbox",
            provider_class=RekordboxDataProvider,
            capabilities=[
                PlatformCapability.IMPORT_PLAYLISTS,
                PlatformCapability.EXPORT_PLAYLISTS,
                PlatformCapability.SYNC_PLAYLISTS,
                PlatformCapability.IMPORT_TRACKS,
                PlatformCapability.FOLDERS,
            ],
        )

        logger.info("Registered Rekordbox provider")
    except Exception as e:
        logger.error(f"Failed to initialize Rekordbox provider: {e}")


def _initialize_discogs_provider(registry) -> None:
    """Initialize the Discogs provider.

    Args:
        registry: The platform registry
    """
    try:
        # Import the provider class and client class
        from selecta.core.platform.discogs.client import DiscogsClient
        from selecta.ui.components.playlist.platform.discogs.discogs_data_provider import (
            DiscogsDataProvider,
        )

        # Register the client
        registry.register_client("discogs", DiscogsClient)

        # Register the provider with capabilities
        registry.register_provider(
            platform_name="discogs",
            provider_class=DiscogsDataProvider,
            capabilities=[
                PlatformCapability.IMPORT_PLAYLISTS,
                PlatformCapability.IMPORT_TRACKS,
                PlatformCapability.SYNC_PLAYLISTS,
                PlatformCapability.SEARCH,
                PlatformCapability.COVER_ART,
            ],
        )

        logger.info("Registered Discogs provider")
    except Exception as e:
        logger.error(f"Failed to initialize Discogs provider: {e}")


def _initialize_youtube_provider(registry) -> None:
    """Initialize the YouTube provider.

    Args:
        registry: The platform registry
    """
    try:
        # Import the provider class and client class
        from selecta.core.platform.youtube.client import YouTubeClient
        from selecta.ui.components.playlist.platform.youtube.youtube_data_provider import (
            YouTubeDataProvider,
        )

        # Register the client
        registry.register_client("youtube", YouTubeClient)

        # Register the provider with capabilities
        registry.register_provider(
            platform_name="youtube",
            provider_class=YouTubeDataProvider,
            capabilities=[
                PlatformCapability.IMPORT_PLAYLISTS,
                PlatformCapability.EXPORT_PLAYLISTS,
                PlatformCapability.SYNC_PLAYLISTS,
                PlatformCapability.CREATE_PLAYLISTS,
                PlatformCapability.IMPORT_TRACKS,
                PlatformCapability.SEARCH,
                PlatformCapability.COVER_ART,
            ],
        )

        logger.info("Registered YouTube provider")
    except Exception as e:
        logger.error(f"Failed to initialize YouTube provider: {e}")
