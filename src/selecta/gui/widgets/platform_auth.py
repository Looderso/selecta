"""Platform authentication widgets for Selecta."""

from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from loguru import logger

from selecta.data.repositories.settings_repository import SettingsRepository
from selecta.platform.platform_factory import PlatformFactory


class PlatformAuthPanel(BoxLayout):
    """Panel containing authentication widgets for all platforms."""

    def __init__(self, **kwargs):
        """Initialize the authentication panel."""
        super().__init__(**kwargs)
        self.settings_repo = SettingsRepository()


class BasePlatformAuth(BoxLayout):
    """Base class for platform authentication widgets."""

    is_authenticated = BooleanProperty(False)
    platform_name = StringProperty("")

    def __init__(self, **kwargs):
        """Initialize the platform authentication widget."""
        super().__init__(**kwargs)
        self.settings_repo = SettingsRepository()
        self.client = None

        # Schedule a check of authentication status
        Clock.schedule_once(self.check_auth_status, 0.5)

    def check_auth_status(self, dt):
        """Check if the platform is authenticated."""
        raise NotImplementedError("Subclasses must implement check_auth_status")

    def authenticate(self):
        """Start the authentication process."""
        raise NotImplementedError("Subclasses must implement authenticate")

    def disconnect(self):
        """Disconnect from the platform."""
        raise NotImplementedError("Subclasses must implement disconnect")


class SpotifyAuth(BasePlatformAuth):
    """Widget for Spotify authentication."""

    platform_name = StringProperty("spotify")

    def __init__(self, **kwargs):
        """Initialize the Spotify authentication widget."""
        super().__init__(**kwargs)
        # Initialize client
        self.client = PlatformFactory.create("spotify", self.settings_repo)

    def check_auth_status(self, dt):
        """Check if Spotify is authenticated."""
        if self.client:
            try:
                self.is_authenticated = self.client.is_authenticated()
                logger.debug(f"Spotify authenticated: {self.is_authenticated}")
            except Exception as e:
                logger.error(f"Error checking Spotify authentication: {e}")
                self.is_authenticated = False
        else:
            self.is_authenticated = False

    def authenticate(self):
        """Start the Spotify authentication process."""
        logger.info("Starting Spotify authentication...")
        if not self.client:
            self.client = PlatformFactory.create("spotify", self.settings_repo)

        if self.client:
            try:
                # This will trigger browser auth flow
                success = self.client.authenticate()
                if success:
                    logger.info("Spotify authentication successful")
                    self.is_authenticated = True
                else:
                    logger.error("Spotify authentication failed")
            except Exception as e:
                logger.error(f"Error during Spotify authentication: {e}")
        else:
            logger.error("Could not create Spotify client")

    def disconnect(self):
        """Disconnect from Spotify."""
        logger.info("Disconnecting from Spotify...")
        # For now, just delete the stored credentials
        self.settings_repo.delete_credentials("spotify")
        self.is_authenticated = False


class DiscogsAuth(BasePlatformAuth):
    """Widget for Discogs authentication."""

    platform_name = StringProperty("discogs")

    def __init__(self, **kwargs):
        """Initialize the Discogs authentication widget."""
        super().__init__(**kwargs)
        # Initialize client
        self.client = PlatformFactory.create("discogs", self.settings_repo)

    def check_auth_status(self, dt):
        """Check if Discogs is authenticated."""
        if self.client:
            try:
                self.is_authenticated = self.client.is_authenticated()
                logger.debug(f"Discogs authenticated: {self.is_authenticated}")
            except Exception as e:
                logger.error(f"Error checking Discogs authentication: {e}")
                self.is_authenticated = False
        else:
            self.is_authenticated = False

    def authenticate(self):
        """Start the Discogs authentication process."""
        logger.info("Starting Discogs authentication...")
        if not self.client:
            self.client = PlatformFactory.create("discogs", self.settings_repo)

        if self.client:
            try:
                # This will trigger browser auth flow
                success = self.client.authenticate()
                if success:
                    logger.info("Discogs authentication successful")
                    self.is_authenticated = True
                else:
                    logger.error("Discogs authentication failed")
            except Exception as e:
                logger.error(f"Error during Discogs authentication: {e}")
        else:
            logger.error("Could not create Discogs client")

    def disconnect(self):
        """Disconnect from Discogs."""
        logger.info("Disconnecting from Discogs...")
        # For now, just delete the stored credentials
        self.settings_repo.delete_credentials("discogs")
        self.is_authenticated = False


class RekordboxAuth(BasePlatformAuth):
    """Widget for Rekordbox authentication."""

    platform_name = StringProperty("rekordbox")

    def __init__(self, **kwargs):
        """Initialize the Rekordbox authentication widget."""
        super().__init__(**kwargs)
        # Initialize client
        self.client = PlatformFactory.create("rekordbox", self.settings_repo)

    def check_auth_status(self, dt):
        """Check if Rekordbox is authenticated."""
        if self.client:
            try:
                self.is_authenticated = self.client.is_authenticated()
                logger.debug(f"Rekordbox authenticated: {self.is_authenticated}")
            except Exception as e:
                logger.error(f"Error checking Rekordbox authentication: {e}")
                self.is_authenticated = False
        else:
            self.is_authenticated = False

    def authenticate(self):
        """Start the Rekordbox authentication process."""
        logger.info("Starting Rekordbox authentication...")
        if not self.client:
            self.client = PlatformFactory.create("rekordbox", self.settings_repo)

        if self.client:
            try:
                # For Rekordbox, we might need a different auth flow
                # This could involve showing a file dialog or downloading the key
                success = self.client.authenticate()
                if success:
                    logger.info("Rekordbox authentication successful")
                    self.is_authenticated = True
                else:
                    logger.error("Rekordbox authentication failed")
            except Exception as e:
                logger.error(f"Error during Rekordbox authentication: {e}")
        else:
            logger.error("Could not create Rekordbox client")

    def disconnect(self):
        """Disconnect from Rekordbox."""
        logger.info("Disconnecting from Rekordbox...")
        # For now, just delete the stored credentials
        self.settings_repo.delete_credentials("rekordbox")
        self.is_authenticated = False
