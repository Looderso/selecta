"""Settings repository for database operations."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from selecta.data.database import get_session
from selecta.data.models.credentials import PlatformCredentials
from selecta.data.models.settings import UserSettings


class SettingsRepository:
    """Repository for settings and credentials-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()

    # === User Settings Methods ===

    def get_setting(self, key: str) -> UserSettings | None:
        """Get a user setting by key.

        Args:
            key: The settings key

        Returns:
            The setting if found, None otherwise
        """
        return self.session.query(UserSettings).filter(UserSettings.key == key).first()

    def get_setting_value(self, key: str, default: Any = None) -> Any:
        """Get a user setting value by key.

        Args:
            key: The settings key
            default: Default value if setting not found

        Returns:
            The setting value, or default if not found
        """
        setting = self.get_setting(key)
        if not setting:
            return default
        return setting.typed_value

    def set_setting(
        self,
        key: str,
        value: Any,
        data_type: str | None = None,
        description: str | None = None,
    ) -> UserSettings:
        """Set a user setting.

        Args:
            key: The settings key
            value: The setting value
            data_type: Optional data type ('string', 'boolean', 'integer', 'json')
            description: Optional description of the setting

        Returns:
            The created or updated setting
        """
        # Convert value to string for storage
        if value is not None:
            if isinstance(value, bool):
                value_str = str(value).lower()
                if data_type is None:
                    data_type = "boolean"
            elif isinstance(value, int):
                value_str = str(value)
                if data_type is None:
                    data_type = "integer"
            elif isinstance(value, dict | list):
                import json

                value_str = json.dumps(value)
                if data_type is None:
                    data_type = "json"
            else:
                value_str = str(value)
                if data_type is None:
                    data_type = "string"
        else:
            value_str = None
            if data_type is None:
                data_type = "string"

        # Check if setting already exists
        setting = self.get_setting(key)
        if setting:
            # Update existing using setattr to avoid type checking issues
            setting.value = value_str
            if data_type is not None:
                setting.data_type = data_type
            if description is not None:
                setting.description = description
        else:
            # Create new
            setting = UserSettings(
                key=key, value=value_str, data_type=data_type, description=description
            )
            self.session.add(setting)

        self.session.commit()
        return setting

    def delete_setting(self, key: str) -> bool:
        """Delete a user setting by key.

        Args:
            key: The settings key

        Returns:
            True if deleted, False if not found
        """
        setting = self.get_setting(key)
        if not setting:
            return False

        self.session.delete(setting)
        self.session.commit()
        return True

    def get_all_settings(self) -> list[UserSettings]:
        """Get all user settings.

        Returns:
            List of user settings
        """
        return self.session.query(UserSettings).all()

    def get_settings_dict(self) -> dict[str, Any]:
        """Get all settings as a dictionary.

        Returns:
            Dictionary of settings (key: typed_value)
        """
        settings = self.get_all_settings()
        result: dict[str, Any] = {}

        for s in settings:
            # Extract the string value from the Column type
            key = str(s.key)  # Explicitly convert to string
            value = s.typed_value
            result[key] = value

        return result

    # === Platform Credentials Methods ===

    def get_credentials(self, platform: str) -> PlatformCredentials | None:
        """Get credentials for a platform.

        Args:
            platform: Platform name (e.g., 'spotify', 'discogs', 'rekordbox')

        Returns:
            Credentials if found, None otherwise
        """
        return (
            self.session.query(PlatformCredentials)
            .filter(PlatformCredentials.platform == platform)
            .first()
        )

    def set_credentials(self, platform: str, credentials_data: dict) -> PlatformCredentials:
        """Set credentials for a platform.

        Args:
            platform: Platform name
            credentials_data: Dictionary with credential data

        Returns:
            The updated or created credentials
        """
        credentials = self.get_credentials(platform)

        if credentials:
            # Update existing
            for key, value in credentials_data.items():
                # Only update if the field exists on the model
                if hasattr(credentials, key):
                    setattr(credentials, key, value)
        else:
            # Create new
            credentials_data["platform"] = platform
            credentials = PlatformCredentials(**credentials_data)
            self.session.add(credentials)

        # Use setattr to bypass type checking issues
        credentials.updated_at = datetime.utcnow()

        self.session.commit()
        return credentials

    def delete_credentials(self, platform: str) -> bool:
        """Delete credentials for a platform.

        Args:
            platform: Platform name

        Returns:
            True if deleted, False if not found
        """
        credentials = self.get_credentials(platform)
        if not credentials:
            return False

        self.session.delete(credentials)
        self.session.commit()
        return True

    def get_all_credentials(self) -> list[PlatformCredentials]:
        """Get all platform credentials.

        Returns:
            List of platform credentials
        """
        return self.session.query(PlatformCredentials).all()
