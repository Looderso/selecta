# src/selecta/ui/components/platform_auth.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PlatformAuthWidget(QWidget):
    """Widget for platform authentication status."""

    authenticated_changed = pyqtSignal(bool)
    auth_button_clicked = pyqtSignal()

    def __init__(self, platform_name, icon_path=None, parent=None):
        """Initialize a platform authentication widget.

        This widget displays authentication status for a specific platform (Spotify,
        Discogs, or Rekordbox) and provides a button to authenticate or disconnect.

        Args:
            platform_name: Name of the platform (e.g., "Spotify", "Discogs", "Rekordbox").
            icon_path: Path to the icon asset.
            parent: Optional parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.platform_name = platform_name
        self.icon_path = icon_path
        self._is_authenticated = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Platform icon
        if self.icon_path:
            icon_label = QLabel()
            pixmap = QPixmap(self.icon_path)
            icon_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio))
            layout.addWidget(icon_label)

        # Content area
        content_layout = QVBoxLayout()

        # Platform name
        name_label = QLabel(self.platform_name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        content_layout.addWidget(name_label)

        # Status label
        self.status_label = QLabel("Not authenticated")
        self.status_label.setStyleSheet("color: #FF5555;")
        content_layout.addWidget(self.status_label)

        layout.addLayout(content_layout, 1)  # Stretch to take available space

        # Auth button
        self.auth_button = QPushButton("Authenticate")
        self.auth_button.setMinimumSize(130, 40)
        self.auth_button.clicked.connect(self.auth_button_clicked)
        layout.addWidget(self.auth_button)

        # Set initial state
        self.set_authenticated(self._is_authenticated)

    def set_authenticated(self, is_authenticated):
        """Set the authentication status."""
        if self._is_authenticated != is_authenticated:
            self._is_authenticated = is_authenticated
            self.authenticated_changed.emit(is_authenticated)

        if is_authenticated:
            self.status_label.setText("Authenticated")
            self.status_label.setStyleSheet("color: #55FF55;")
            self.auth_button.setText("Disconnect")
            self.setStyleSheet("background-color: rgba(10, 70, 10, 100); border-radius: 8px;")
        else:
            self.status_label.setText("Not authenticated")
            self.status_label.setStyleSheet("color: #FF5555;")
            self.auth_button.setText("Authenticate")
            self.setStyleSheet("background-color: rgba(70, 10, 10, 100); border-radius: 8px;")
