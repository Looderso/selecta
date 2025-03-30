"""Platform authentication panel for all platforms."""

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
        try:
            rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
            if rekordbox_client:
                # Try to authenticate first if we have a key
                auth_manager = RekordboxAuthManager(settings_repo=self.settings_repo)
                if auth_manager.get_stored_key():
                    # Force authentication check with stored key
                    is_authenticated = rekordbox_client.is_authenticated()
                else:
                    # No key yet, need to authenticate
                    is_authenticated = False
            else:
                is_authenticated = False

            widget.set_authenticated(is_authenticated)
        except Exception as e:
            from loguru import logger

            logger.exception(f"Error checking Rekordbox authentication: {e}")
            widget.set_authenticated(False)

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
        from loguru import logger
        from PyQt6.QtWidgets import QMessageBox

        # Check if Rekordbox is running
        try:
            import psutil

            rekordbox_running = any(
                "rekordbox" in p.name().lower() for p in psutil.process_iter(["name"])
            )
            if rekordbox_running:
                # Show warning about Rekordbox running
                response = QMessageBox.warning(
                    self,
                    "Rekordbox is Running",
                    "Rekordbox is currently running which may block database access.\n\n"
                    "For best results, please close Rekordbox before continuing.\n\n"
                    "Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if response == QMessageBox.StandardButton.No:
                    return

        except ImportError:
            pass  # psutil not available, skip this check

        if widget.is_authenticated():
            # Disconnect
            self.settings_repo.delete_credentials("rekordbox")
            widget.set_authenticated(False)

            # Update main window to reflect disconnection
            main_window = self.window()
            if hasattr(main_window, "switch_platform"):
                main_window.switch_platform("rekordbox")  # type: ignore
        else:
            # Show progress message
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("Rekordbox Authentication")
            progress_msg.setText("Attempting to authenticate with Rekordbox...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_msg.show()

            # Force processing of events so message shows up
            from PyQt6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

            try:
                # Try to authenticate through the client directly
                # (which will try multiple methods)
                rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
                if rekordbox_client:
                    authenticated = rekordbox_client.authenticate()

                    # Close progress message
                    progress_msg.close()

                    if authenticated:
                        logger.info("Rekordbox authentication successful")
                        widget.set_authenticated(True)

                        # Update the main window
                        main_window = self.window()
                        if hasattr(main_window, "switch_platform"):
                            main_window.switch_platform("rekordbox")  # type: ignore

                        # Show success message
                        QMessageBox.information(
                            self,
                            "Rekordbox Authentication Successful",
                            "Successfully connected to Rekordbox database.",
                        )
                    else:
                        logger.warning("Rekordbox authentication failed")
                        widget.set_authenticated(False)

                        # Show error message
                        QMessageBox.warning(
                            self,
                            "Rekordbox Authentication Failed",
                            "Could not authenticate with Rekordbox database.\n\n"
                            "Please try again later or check that:\n"
                            "1. Rekordbox is installed correctly\n"
                            "2. Rekordbox is not currently running\n"
                            "3. You have a valid Rekordbox database",
                        )
                else:
                    # Close progress message
                    progress_msg.close()

                    logger.error("Failed to create Rekordbox client")
                    QMessageBox.critical(
                        self,
                        "Rekordbox Client Error",
                        "Failed to create Rekordbox client.\n\n"
                        "Please check that Rekordbox is installed correctly.",
                    )
            except Exception as e:
                # Close progress message
                progress_msg.close()

                logger.exception(f"Error during Rekordbox authentication: {e}")
                QMessageBox.critical(
                    self,
                    "Rekordbox Authentication Error",
                    f"An error occurred during Rekordbox authentication:\n\n{str(e)}",
                )
