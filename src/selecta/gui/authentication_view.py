"""Authentication view for Selecta platforms."""

import traceback

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from loguru import logger

from selecta.data.repositories.settings_repository import SettingsRepository
from selecta.gui.widgets.platform_indicators import PlatformIndicator
from selecta.platform.platform_factory import PlatformFactory
from selecta.platform.rekordbox.auth import RekordboxAuthManager


class PlatformAuthenticationView(BoxLayout):
    """Main authentication view for platforms."""

    def __init__(self, **kwargs):
        """Initialize the authentication view."""
        try:
            super().__init__(**kwargs)

            # Configure layout
            self.orientation = "vertical"
            self.spacing = 15
            self.padding = [20, 40]

            # Create settings repository
            self.settings_repo = SettingsRepository()

            # Add title
            title_label = Label(
                text="Platform Authentication",
                font_size="24sp",
                bold=True,
                size_hint_y=None,
                height=50,
            )
            self.add_widget(title_label)

            # Create platform indicators
            logger.info("Creating platform indicators")
            self.platform_indicators = {
                "spotify": self._create_spotify_indicator(),
                "discogs": self._create_discogs_indicator(),
                "rekordbox": self._create_rekordbox_indicator(),
            }

            # Add platform indicators
            for platform, indicator in self.platform_indicators.items():
                # Bind authentication button
                indicator.auth_button.bind(
                    on_press=lambda _, p=platform: self._authenticate_platform(p)
                )
                self.add_widget(indicator)

            # Add debug label (optional, for tracking)
            self.debug_label = Label(
                text="Authentication View Loaded",
                color=(1, 1, 1, 0.5),
                font_size="12sp",
                size_hint_y=None,
                height=30,
            )
            self.add_widget(self.debug_label)

            logger.info("Authentication view initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing authentication view: {e}")
            logger.error(traceback.format_exc())

            # Add an error label to the view
            error_label = Label(
                text=f"Initialization Error:\n{e}",
                color=(1, 0, 0, 1),  # Red color
            )
            self.add_widget(error_label)

    def _create_spotify_indicator(self) -> PlatformIndicator:
        """Create Spotify authentication indicator."""
        try:
            spotify_indicator = PlatformIndicator(platform_name="Spotify")

            # Check authentication status
            spotify_client = PlatformFactory.create("spotify", self.settings_repo)
            is_authenticated = spotify_client.is_authenticated() if spotify_client else False
            spotify_indicator.set_authenticated(is_authenticated)

            return spotify_indicator
        except Exception as e:
            logger.error(f"Error creating Spotify indicator: {e}")
            logger.error(traceback.format_exc())
            return PlatformIndicator(platform_name="Spotify Error")

    def _create_discogs_indicator(self) -> PlatformIndicator:
        """Create Discogs authentication indicator."""
        try:
            discogs_indicator = PlatformIndicator(platform_name="Discogs")

            # Check authentication status
            discogs_client = PlatformFactory.create("discogs", self.settings_repo)
            is_authenticated = discogs_client.is_authenticated() if discogs_client else False
            discogs_indicator.set_authenticated(is_authenticated)

            return discogs_indicator
        except Exception as e:
            logger.error(f"Error creating Discogs indicator: {e}")
            logger.error(traceback.format_exc())
            return PlatformIndicator(platform_name="Discogs Error")

    def _create_rekordbox_indicator(self) -> PlatformIndicator:
        """Create Rekordbox authentication indicator."""
        try:
            rekordbox_indicator = PlatformIndicator(platform_name="Rekordbox")

            # Check authentication status
            rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
            is_authenticated = rekordbox_client.is_authenticated() if rekordbox_client else False
            rekordbox_indicator.set_authenticated(is_authenticated)

            return rekordbox_indicator
        except Exception as e:
            logger.error(f"Error creating Rekordbox indicator: {e}")
            logger.error(traceback.format_exc())
            return PlatformIndicator(platform_name="Rekordbox Error")

    def _authenticate_platform(self, platform: str):
        """Authenticate a specific platform.

        Args:
            platform: Platform name to authenticate
        """
        try:
            logger.info(f"Authenticating {platform}")

            if platform == "rekordbox":
                # Special handling for Rekordbox
                auth_manager = RekordboxAuthManager(self.settings_repo)

                # Try to download key
                key = auth_manager.download_key()

                if not key:
                    # Show a popup with manual instructions
                    popup_content = BoxLayout(orientation="vertical", padding=20, spacing=10)
                    popup_content.add_widget(
                        Label(
                            text="Could not automatically download Rekordbox key.\n"
                            "Please download manually using:\n"
                            "python -m pyrekordbox download-key\n"
                            "Then run: selecta rekordbox setup"
                        )
                    )
                    close_btn = Button(text="Close", size_hint_y=None, height=50)
                    popup_content.add_widget(close_btn)

                    popup = Popup(
                        title="Rekordbox Authentication Failed",
                        content=popup_content,
                        size_hint=(None, None),
                        size=(400, 300),
                    )
                    close_btn.bind(on_press=popup.dismiss)
                    popup.open()

                    return

            # For other platforms
            client = PlatformFactory.create(platform, self.settings_repo)

            if client:
                # Trigger platform-specific authentication
                auth_result = client.authenticate()
                logger.info(f"{platform} authentication result: {auth_result}")

                # Update the indicator status
                indicator = self.platform_indicators.get(platform)
                if indicator:
                    indicator.set_authenticated(client.is_authenticated())
            else:
                logger.error(f"Failed to create client for {platform}")
        except Exception as e:
            logger.error(f"Error authenticating {platform}: {e}")
            logger.error(traceback.format_exc())
