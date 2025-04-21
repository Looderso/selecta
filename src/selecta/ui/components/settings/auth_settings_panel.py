from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.ui.components.settings.auth_dialog import AuthenticationDialog


class PlatformAuthWidget(QWidget):
    """Unified platform authentication widget."""

    def __init__(self, platform_name, parent=None):
        """Initialize the platform auth widget.

        Args:
            platform_name: Name of the platform
            parent: Parent widget
        """
        super().__init__(parent)
        self.platform_name = platform_name.lower()  # Normalize to lowercase
        self.display_name = platform_name  # Keep original case for display
        self.settings_repo = SettingsRepository()
        self._setup_ui()
        self._update_status()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Platform info section
        info_layout = QVBoxLayout()

        self.name_label = QLabel(self.display_name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.name_label)

        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #FF5555;")
        info_layout.addWidget(self.status_label)

        self.last_auth_label = QLabel("")
        self.last_auth_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(self.last_auth_label)

        layout.addLayout(info_layout, 1)  # 1 = stretch factor

        # Button section
        button_layout = QVBoxLayout()

        self.auth_button = QPushButton("Connect")
        self.auth_button.clicked.connect(self._on_auth_clicked)
        button_layout.addWidget(self.auth_button)

        layout.addLayout(button_layout)

    def _update_status(self):
        """Update the display based on current authentication status."""
        # Check if platform is authenticated
        client = PlatformFactory.create(self.platform_name, self.settings_repo)
        is_authenticated = False

        if client is not None:
            try:
                is_authenticated = client.is_authenticated()
            except Exception:
                is_authenticated = False

        # Update UI based on status
        if is_authenticated:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #55FF55;")
            self.auth_button.setText("Disconnect")

            # Get last authentication time if available
            last_auth = self.settings_repo.get_last_auth_time(self.platform_name)
            if last_auth:
                self.last_auth_label.setText(f"Last connected: {last_auth}")
            else:
                self.last_auth_label.setText("")
        else:
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("color: #FF5555;")
            self.auth_button.setText("Connect")
            self.last_auth_label.setText("")

    def _on_auth_clicked(self):
        """Handle authentication button click."""
        # Check current status
        client = PlatformFactory.create(self.platform_name, self.settings_repo)
        is_authenticated = False

        if client is not None:
            try:
                is_authenticated = client.is_authenticated()
            except Exception:
                is_authenticated = False

        if is_authenticated:
            # Disconnect
            from PyQt6.QtWidgets import QMessageBox

            # Ask for confirmation
            response = QMessageBox.question(
                self,
                f"Disconnect {self.display_name}",
                f"Are you sure you want to disconnect from {self.display_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response == QMessageBox.StandardButton.Yes:
                # Perform disconnect
                self.settings_repo.delete_credentials(self.platform_name)
                self._update_status()
        else:
            # Connect using unified dialog
            success = AuthenticationDialog.authenticate_platform(self.platform_name, self)

            # Update status after authentication
            if success:
                # Store last authentication time
                import datetime

                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                self.settings_repo.set_last_auth_time(self.platform_name, now)

            self._update_status()


class AuthSettingsPanel(QWidget):
    """Panel for authentication settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Header
        header = QLabel("Authentication Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Description
        description = QLabel(
            "Connect to various music platforms to enable synchronization and search functionality. "
            "Authentication is required for each platform you want to use."
        )
        description.setWordWrap(True)
        content_layout.addWidget(description)

        # Platform authentication widgets
        self.spotify_auth = PlatformAuthWidget("Spotify")
        self.discogs_auth = PlatformAuthWidget("Discogs")
        self.rekordbox_auth = PlatformAuthWidget("Rekordbox")
        self.youtube_auth = PlatformAuthWidget("YouTube")

        # Add platform widgets with separators
        content_layout.addWidget(self.spotify_auth)
        content_layout.addWidget(self._create_separator())
        content_layout.addWidget(self.discogs_auth)
        content_layout.addWidget(self._create_separator())
        content_layout.addWidget(self.rekordbox_auth)
        content_layout.addWidget(self._create_separator())
        content_layout.addWidget(self.youtube_auth)

        # Add stretch to push content to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def _create_separator(self):
        """Create a horizontal separator line.

        Returns:
            QFrame separator
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator

    def refresh(self):
        """Refresh the authentication status of all platforms."""
        self.spotify_auth._update_status()
        self.discogs_auth._update_status()
        self.rekordbox_auth._update_status()
        self.youtube_auth._update_status()
