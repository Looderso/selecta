"""Platform registry for managing playlist data providers.

This module provides a central registry for registering and accessing
platform data providers, which helps reduce duplication and enforce
consistency across the application.
"""

from loguru import logger

from selecta.ui.components.playlist.interfaces import (
    IPlatformClient,
    IPlatformDataProvider,
    PlatformCapability,
)


class PlatformRegistry:
    """Registry for platform data providers and clients.

    This class provides a single point of access for all platform data providers
    and ensures consistent initialization and access patterns across the application.
    """

    # Singleton instance
    _instance = None

    # Class attribute declarations for type checking
    _provider_registry: dict[str, type[IPlatformDataProvider]]
    _client_registry: dict[str, type[IPlatformClient]]
    _platform_capabilities: dict[str, set[PlatformCapability]]
    _provider_instances: dict[str, IPlatformDataProvider]
    _client_instances: dict[str, IPlatformClient]

    def __new__(cls):
        """Create or return the singleton instance.

        Returns:
            The singleton PlatformRegistry instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize attributes here rather than in __init__
            # This ensures they're set only once
            cls._instance._provider_registry = {}
            cls._instance._client_registry = {}
            cls._instance._platform_capabilities = {}
            cls._instance._provider_instances = {}
            cls._instance._client_instances = {}
        return cls._instance

    def register_provider(
        self,
        platform_name: str,
        provider_class: type[IPlatformDataProvider],
        capabilities: list[PlatformCapability],
    ) -> None:
        """Register a platform data provider class.

        Args:
            platform_name: Name of the platform (e.g., "spotify", "rekordbox")
            provider_class: The provider class to register
            capabilities: List of capabilities supported by this platform
        """
        # Convert platform name to lowercase for consistency
        platform_name = platform_name.lower()

        # Register the provider class
        self._provider_registry[platform_name] = provider_class

        # Register capabilities
        self._platform_capabilities[platform_name] = set(capabilities)

        logger.debug(f"Registered provider for {platform_name}: {provider_class.__name__}")

    def register_client(self, platform_name: str, client_class: type[IPlatformClient]) -> None:
        """Register a platform client class.

        Args:
            platform_name: Name of the platform (e.g., "spotify", "rekordbox")
            client_class: The client class to register
        """
        # Convert platform name to lowercase for consistency
        platform_name = platform_name.lower()

        # Register the client class
        self._client_registry[platform_name] = client_class

        logger.debug(f"Registered client for {platform_name}: {client_class.__name__}")

    def get_provider(self, platform_name: str) -> IPlatformDataProvider | None:
        """Get a platform data provider instance.

        This method lazily creates provider instances as needed, ensuring
        that only one instance exists per platform.

        Args:
            platform_name: Name of the platform (e.g., "spotify", "rekordbox")

        Returns:
            The platform data provider instance, or None if not registered
        """
        # Convert platform name to lowercase for consistency
        platform_name = platform_name.lower()

        # Return existing instance if already created
        if platform_name in self._provider_instances:
            return self._provider_instances[platform_name]

        # Check if the provider is registered
        if platform_name not in self._provider_registry:
            logger.warning(f"No provider registered for platform: {platform_name}")
            return None

        try:
            # Create a client instance if needed
            client = self.get_client(platform_name)

            # Create the provider instance
            provider_class = self._provider_registry[platform_name]

            # Import here to avoid circular imports
            from selecta.ui.components.playlist.library.library_data_provider import LibraryDataProvider

            # Special case for Library provider which doesn't need a client

            provider = provider_class() if provider_class is LibraryDataProvider else provider_class(client)  # type: ignore

            # Cache the instance
            self._provider_instances[platform_name] = provider

            return provider
        except Exception as e:
            logger.exception(f"Error creating provider for {platform_name}: {e}")
            return None

    def get_client(self, platform_name: str) -> IPlatformClient | None:
        """Get a platform client instance.

        This method lazily creates client instances as needed, ensuring
        that only one instance exists per platform.

        Args:
            platform_name: Name of the platform (e.g., "spotify", "rekordbox")

        Returns:
            The platform client instance, or None if not registered
        """
        # Convert platform name to lowercase for consistency
        platform_name = platform_name.lower()

        # Return existing instance if already created
        if platform_name in self._client_instances:
            return self._client_instances[platform_name]

        # Check if the client is registered
        if platform_name not in self._client_registry:
            logger.warning(f"No client registered for platform: {platform_name}")
            return None

        try:
            # Create the client instance using PlatformFactory
            from typing import cast

            from selecta.core.data.repositories.settings_repository import SettingsRepository

            # Import both interfaces for proper typing
            from selecta.core.platform.platform_factory import PlatformFactory

            settings_repo = SettingsRepository()
            platform_client = PlatformFactory.create(platform_name, settings_repo)

            # The PlatformFactory returns AbstractPlatform, but we need IPlatformClient
            # This is a temporary solution during the refactoring process
            # Cast to the interface that BasePlatformDataProvider expects
            client = cast(IPlatformClient, platform_client)

            # Cache the instance
            self._client_instances[platform_name] = client

            return client
        except Exception as e:
            logger.exception(f"Error creating client for {platform_name}: {e}")
            return None

    def get_all_platforms(self) -> list[str]:
        """Get all registered platform names.

        Returns:
            List of platform names
        """
        return list(self._provider_registry.keys())

    def get_capabilities(self, platform_name: str) -> set[PlatformCapability]:
        """Get the capabilities supported by a platform.

        Args:
            platform_name: Name of the platform

        Returns:
            Set of capabilities supported by the platform
        """
        platform_name = platform_name.lower()
        return self._platform_capabilities.get(platform_name, set())

    def get_platforms_with_capability(self, capability: PlatformCapability) -> list[str]:
        """Get all platforms that support a specific capability.

        Args:
            capability: The capability to check for

        Returns:
            List of platform names that support the capability
        """
        return [
            platform for platform, capabilities in self._platform_capabilities.items() if capability in capabilities
        ]

    def clear_cache(self) -> None:
        """Clear all provider and client instances.

        This is useful for testing or when settings have changed
        and instances need to be recreated.
        """
        # Clear provider instances
        for provider in self._provider_instances.values():
            # Type-safe way to check for and clear the cache
            try:
                # First try calling refresh() which should clear the cache internally
                provider.refresh()
            except Exception:
                # If that fails, try more direct approaches
                try:
                    # Try to get the cache attribute and clear it if possible
                    cache = getattr(provider, "cache", None)
                    if cache is not None and hasattr(cache, "clear"):
                        cache.clear()
                except Exception:
                    # If all else fails, just log and continue
                    logger.debug(f"Could not clear cache for provider: {provider.get_platform_name()}")

        # Reset instances
        self._provider_instances.clear()
        self._client_instances.clear()

        logger.debug("Cleared all provider and client instances")


# Convenience function to get the singleton instance
def get_platform_registry() -> PlatformRegistry:
    """Get the singleton PlatformRegistry instance.

    Returns:
        The singleton PlatformRegistry instance
    """
    return PlatformRegistry()
