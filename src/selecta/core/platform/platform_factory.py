"""Factory for creating platform clients."""

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.discogs.client import DiscogsClient  # Add this import
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient


class PlatformFactory:
    """Factory for creating platform-specific clients."""

    # Registry of platform types
    _platform_types: dict[str, type[AbstractPlatform]] = {
        "spotify": SpotifyClient,
        "discogs": DiscogsClient,  # Add this line
        "rekordbox": RekordboxClient,  # Add this once implemented
    }

    @classmethod
    def create(
        cls, platform_name: str, settings_repo: SettingsRepository | None = None
    ) -> AbstractPlatform | None:
        """Create a platform client instance.

        Args:
            platform_name: Name of the platform ("spotify", "rekordbox", "discogs")
            settings_repo: Optional settings repository

        Returns:
            Platform client instance or None if platform not supported
        """
        if platform_name.lower() not in cls._platform_types:
            logger.error(f"Unsupported platform: {platform_name}")
            return None

        platform_class = cls._platform_types[platform_name.lower()]

        try:
            if settings_repo:
                return platform_class(settings_repo=settings_repo)
            else:
                return platform_class()
        except Exception as e:
            logger.exception(f"Error creating {platform_name} client: {e}")
            return None

    @classmethod
    def register_platform(cls, name: str, platform_class: type[AbstractPlatform]) -> None:
        """Register a new platform type.

        Args:
            name: Name of the platform
            platform_class: Platform client class
        """
        cls._platform_types[name.lower()] = platform_class
        logger.debug(f"Registered platform type: {name}")

    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """Get a list of supported platform names.

        Returns:
            List of supported platform names
        """
        return list(cls._platform_types.keys())
