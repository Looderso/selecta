from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from selecta.core.utils.path_helper import get_resource_path


class PlatformAuthWidget(QWidget):
    """Widget for platform authentication status."""

    auth_button_clicked = pyqtSignal()

    def __init__(self, platform_name: str, parent=None) -> None:
        """Initializes the Platform Authentication Widget.

        Args:
            platform_name: Name of the platform.
            parent: Parent of the widget. Defaults to None.
        """
        super().__init__(parent)
        self.platform_name = platform_name
        self._is_authenticated = False

        # Setup styling
        self.setMinimumHeight(100)
        self.setObjectName("platformAuth")

        # Get icon path
        self.icon_path = self._get_icon_path()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        # Platform icon
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)

        if self.icon_path and Path(self.icon_path).exists():
            pixmap = QPixmap(self.icon_path)
            icon_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            # Fallback: display the first letter
            icon_label.setText(self.platform_name[0])
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("""
                background-color: #444;
                border-radius: 20px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            """)

        layout.addWidget(icon_label)

        # Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)

        # Platform name
        name_label = QLabel(self.platform_name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        content_layout.addWidget(name_label)

        # Status label
        self.status_label = QLabel("Not authenticated")
        self.status_label.setStyleSheet("color: #FF5555;")
        content_layout.addWidget(self.status_label)

        layout.addLayout(content_layout, 1)  # Add with stretch factor

        # Auth button
        self.auth_button = QPushButton("Authenticate")
        self.auth_button.setFixedSize(130, 40)
        self.auth_button.clicked.connect(self.auth_button_clicked)
        layout.addWidget(self.auth_button)

        # Apply initial status styling
        self.setStyleSheet("""
            #platformAuth {
                background-color: rgba(70, 10, 10, 100);
                border-radius: 8px;
            }
        """)

    def _get_icon_path(self) -> str | None:
        """Get the path to the platform icon."""
        # Map platform names to icon file names
        icon_files = {
            "Spotify": "spotify_logo.png",
            "Discogs": "discogs_logo.png",
            "Rekordbox": "rekordbox_logo.png",
        }

        if self.platform_name in icon_files:
            # Try to get from resources
            icons_dir = get_resource_path("icons")
            icon_path = icons_dir / icon_files[self.platform_name]

            if Path(icon_path).exists():
                return str(icon_path)

        return None

    def is_authenticated(self) -> bool:
        """Get the authentication status."""
        return self._is_authenticated

    def set_authenticated(self, is_authenticated: bool) -> None:
        """Set the authentication status."""
        self._is_authenticated = is_authenticated

        if is_authenticated:
            self.status_label.setText("Authenticated")
            self.status_label.setStyleSheet("color: #55FF55;")
            self.auth_button.setText("Disconnect")
            self.setStyleSheet("""
                #platformAuth {
                    background-color: rgba(10, 70, 10, 100);
                    border-radius: 8px;
                }
            """)
        else:
            self.status_label.setText("Not authenticated")
            self.status_label.setStyleSheet("color: #FF5555;")
            self.auth_button.setText("Authenticate")
            self.setStyleSheet("""
                #platformAuth {
                    background-color: rgba(70, 10, 10, 100);
                    border-radius: 8px;
                }
            """)
