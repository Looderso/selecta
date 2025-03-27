"""Rekordbox authentication utilities."""

import subprocess

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.utils.type_helpers import column_to_str, is_column_truthy


class RekordboxAuthManager:
    """Handles Rekordbox authentication and key management."""

    def __init__(
        self,
        db_key: str | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize the Rekordbox authentication manager.

        Args:
            db_key: Rekordbox database key (can be loaded from settings if None)
            settings_repo: Repository for accessing application settings
        """
        self.settings_repo = settings_repo or SettingsRepository()

        # Load credentials from settings if not provided
        if db_key is None:
            stored_creds = self.settings_repo.get_credentials("rekordbox")
            if stored_creds:
                db_key = column_to_str(stored_creds.client_secret)

        self.db_key = db_key

    def get_stored_key(self) -> str | None:
        """Get the stored Rekordbox database key.

        Returns:
            The stored database key or None if not found
        """
        creds = self.settings_repo.get_credentials("rekordbox")

        if not creds or not is_column_truthy(creds.client_secret):
            return None

        return column_to_str(creds.client_secret)

    def store_key(self, key: str) -> bool:
        """Store the Rekordbox database key in settings.

        This method also writes the key to the pyrekordbox cache.

        Args:
            key: The Rekordbox database key

        Returns:
            True if successful, False otherwise
        """
        if not key:
            logger.error("Cannot store empty Rekordbox key")
            return False

        try:
            # Store key in settings repository
            self.settings_repo.set_credentials(
                "rekordbox",
                {
                    "client_id": "rekordbox",  # Using a placeholder
                    "client_secret": key,
                },
            )

            # Also write to pyrekordbox cache
            try:
                from pyrekordbox.config import write_db6_key_cache

                write_db6_key_cache(key)
                logger.info("Rekordbox key written to pyrekordbox cache")
            except ImportError:
                logger.warning("Could not import pyrekordbox. Key not written to cache.")

            self.db_key = key
            return True
        except Exception as e:
            logger.exception(f"Error storing Rekordbox key: {e}")
            return False

    def download_key(self) -> str | None:
        """Download the Rekordbox database key using pyrekordbox CLI.

        Returns:
            The downloaded key if successful, None otherwise
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pyrekordbox", "download-key"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Try to parse the key from the output
            output = result.stdout
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("402fd"):
                    # This looks like a key
                    self.store_key(line)
                    return line

            logger.warning("Could not find key in pyrekordbox output")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running pyrekordbox download-key: {e.stderr}")
            return None
        except Exception as e:
            logger.exception(f"Error downloading Rekordbox key: {e}")
            return None
