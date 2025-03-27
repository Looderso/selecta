"""API credentials and tokens for external platforms."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from selecta.core.data.database import Base
from selecta.core.utils.type_helpers import is_column_truthy


class PlatformCredentials(Base):
    """Credentials for external platforms like Spotify, Discogs."""

    __tablename__ = "platform_credentials"

    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False, unique=True)  # 'spotify', 'discogs', 'rekordbox'

    # OAuth2 credentials
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)

    # Rekordbox database path (for rekordbox platform)
    db_path = Column(String(1024), nullable=True)

    # Token expiration
    token_expiry = Column(DateTime, nullable=True)

    # When credentials were last updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of PlatformCredentials.

        Returns:
            str: String representation
        """
        return f"<Credentials for {self.platform}>"

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token is expired.

        Returns:
            bool: True if token is expired or missing
        """
        if not is_column_truthy(self.access_token) or not is_column_truthy(self.token_expiry):
            return True

        return datetime.utcnow() > self.token_expiry  # type: ignore
