"""Abstract base class for platform integrations."""

from abc import ABC, abstractmethod


class AbstractPlatform(ABC):
    """Abstract base class for platform-specific clients (Spotify, Rekordbox, Discogs)."""

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
