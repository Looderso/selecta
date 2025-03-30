# src/selecta/core/platform/rekordbox/auth.py
"""Rekordbox authentication utilities."""

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository

# Fixed Rekordbox database key - the same for all installations
REKORDBOX_DB_KEY = "402fd482c38817c35ffa8ffb8c7d93143b749e7d315df7a81732a1ff43608497"


class RekordboxAuthManager:
    """Handles Rekordbox authentication and key management."""

    def __init__(
        self,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize the Rekordbox authentication manager.

        Args:
            settings_repo: Repository for accessing application settings
        """
        self.settings_repo = settings_repo or SettingsRepository()

    def get_stored_key(self) -> str:
        """Get the Rekordbox database key.

        Returns:
            The Rekordbox database key
        """
        return REKORDBOX_DB_KEY

    def store_key(self, key: str) -> bool:
        """Store the Rekordbox database key in settings.

        This is a no-op since we use a fixed key.

        Args:
            key: The Rekordbox database key

        Returns:
            True
        """
        # We don't need to store the key, but we'll log it for debugging
        if key != REKORDBOX_DB_KEY:
            logger.warning(f"Ignoring provided key: {key}, using fixed key instead")
        return True

    def download_key(self) -> str:
        """Get the Rekordbox database key.

        Returns:
            The fixed Rekordbox database key
        """
        return REKORDBOX_DB_KEY
