"""Abstract base class for platform integrations."""

from abc import ABC, abstractmethod

from selecta.core.data.repositories.settings_repository import SettingsRepository


class AbstractPlatform(ABC):
    """Abstract base class for platform-specific clients (Spotify, Rekordbox, Discogs)."""

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
