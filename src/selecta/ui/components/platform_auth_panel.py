from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.auth import RekordboxAuthManager
from selecta.ui.components.platform_auth_widget import PlatformAuthWidget


class PlatformAuthPanel(QWidget):
    """Panel containing authentication widgets for all platforms."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the platform authentication panel.

        This panel contains authentication widgets for Spotify, Discogs, and Rekordbox.
        It checks the current authentication status for each platform and provides
        buttons to authenticate or disconnect.

        Args:
            parent: Optional parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.settings_repo = SettingsRepository()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Create platform authentication widgets
        self.spotify_auth = self._create_spotify_widget()
        self.discogs_auth = self._create_discogs_widget()
        self.rekordbox_auth = self._create_rekordbox_widget()

        # Add widgets to layout
        layout.addWidget(self.spotify_auth)
        layout.addWidget(self.discogs_auth)
        layout.addWidget(self.rekordbox_auth)

        # Add footer label
        footer_label = QLabel("Authenticate each platform to start syncing your music")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #888; margin-top: 10px;")
        layout.addWidget(footer_label)

    def _create_spotify_widget(self) -> PlatformAuthWidget:
        """Create Spotify authentication widget."""
        widget = PlatformAuthWidget("Spotify")

        # Check authentication status
        spotify_client = PlatformFactory.create("spotify", self.settings_repo)
        is_authenticated = spotify_client.is_authenticated() if spotify_client else False
        widget.set_authenticated(is_authenticated)

        # Connect authentication handler
        widget.auth_button_clicked.connect(lambda: self._authenticate_platform("spotify"))

        return widget

    def _create_discogs_widget(self) -> PlatformAuthWidget:
        """Create Discogs authentication widget."""
        widget = PlatformAuthWidget("Discogs")

        # Check authentication status
        discogs_client = PlatformFactory.create("discogs", self.settings_repo)
        is_authenticated = discogs_client.is_authenticated() if discogs_client else False
        widget.set_authenticated(is_authenticated)

        # Connect authentication handler
        widget.auth_button_clicked.connect(lambda: self._authenticate_platform("discogs"))

        return widget

    def _create_rekordbox_widget(self) -> PlatformAuthWidget:
        """Create Rekordbox authentication widget."""
        widget = PlatformAuthWidget("Rekordbox")

        # Check authentication status
        rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
        is_authenticated = rekordbox_client.is_authenticated() if rekordbox_client else False
        widget.set_authenticated(is_authenticated)

        # Connect authentication handler
        widget.auth_button_clicked.connect(lambda: self._authenticate_platform("rekordbox"))

        return widget

    def _authenticate_platform(self, platform: str) -> None:
        """Authenticate a specific platform."""
        if platform == "spotify":
            self._authenticate_spotify()
        elif platform == "discogs":
            self._authenticate_discogs()
        elif platform == "rekordbox":
            self._authenticate_rekordbox()

    def _authenticate_spotify(self) -> None:
        """Authenticate with Spotify."""
        widget = self.spotify_auth

        if widget.is_authenticated():
            # Disconnect
            self.settings_repo.delete_credentials("spotify")
            widget.set_authenticated(False)
        else:
            # Connect
            spotify_client = PlatformFactory.create("spotify", self.settings_repo)
            if spotify_client:
                spotify_client.authenticate()
                widget.set_authenticated(spotify_client.is_authenticated())

    def _authenticate_discogs(self) -> None:
        """Authenticate with Discogs."""
        widget = self.discogs_auth

        if widget.is_authenticated():
            # Disconnect
            self.settings_repo.delete_credentials("discogs")
            widget.set_authenticated(False)
        else:
            # Connect
            discogs_client = PlatformFactory.create("discogs", self.settings_repo)
            if discogs_client:
                discogs_client.authenticate()
                widget.set_authenticated(discogs_client.is_authenticated())

    def _authenticate_rekordbox(self) -> None:
        """Authenticate with Rekordbox."""
        widget = self.rekordbox_auth

        if widget.is_authenticated():
            # Disconnect
            self.settings_repo.delete_credentials("rekordbox")
            widget.set_authenticated(False)
        else:
            # Connect - Try to download key
            auth_manager = RekordboxAuthManager(settings_repo=self.settings_repo)
            key = auth_manager.download_key()

            if key:
                # Re-check authentication
                rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
                if rekordbox_client:
                    widget.set_authenticated(rekordbox_client.is_authenticated())
            else:
                from PyQt6.QtWidgets import QMessageBox

                # Show error message
                QMessageBox.warning(
                    self,
                    "Rekordbox Authentication Failed",
                    "Could not automatically download Rekordbox key.\n\n"
                    "Please download manually using:\n"
                    "python -m pyrekordbox download-key\n\n"
                    "Then run:\n"
                    "selecta rekordbox setup",
                )
