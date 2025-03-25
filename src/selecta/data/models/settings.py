"""User settings model definitions."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from selecta.data.database import Base


class UserSettings(Base):
    """User preferences and application settings."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    data_type = Column(
        String(20), nullable=False, default="string"
    )  # 'string', 'boolean', 'integer', 'json'

    # Optional description of what this setting controls
    description = Column(String(255), nullable=True)

    # Whether this setting can be modified via the UI
    user_editable = Column(Boolean, default=True)

    def __repr__(self) -> str:
        """String representation of UserSettings.

        Returns:
            str: String representation
        """
        return f"<Setting {self.key}: {self.value}>"

    @property
    def typed_value(self) -> bool | int | dict | str | None:
        """Return the setting value converted to its appropriate type.

        Returns:
            The value in its native Python type
        """
        if self.value is None:
            return None

        if self.data_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.data_type == "integer":
            return int(self.value)
        elif self.data_type == "json":
            import json

            return json.loads(self.value)
        else:  # default to string
            return self.value
