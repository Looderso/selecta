from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class SearchPlatformTabs(QWidget):
    """Tabs for switching between search platforms."""

    platform_changed = pyqtSignal(str)  # Emits the selected platform name

    def __init__(self, parent=None):
        """Initialize the search platform tabs.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self._current_platform = "spotify"

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Create platform buttons
        self.spotify_button = QPushButton("Spotify")
        self.spotify_button.setCheckable(True)
        self.spotify_button.clicked.connect(lambda: self._on_platform_selected("spotify"))

        self.discogs_button = QPushButton("Discogs")
        self.discogs_button.setCheckable(True)
        self.discogs_button.clicked.connect(lambda: self._on_platform_selected("discogs"))

        self.youtube_button = QPushButton("YouTube")
        self.youtube_button.setCheckable(True)
        self.youtube_button.clicked.connect(lambda: self._on_platform_selected("youtube"))

        # Add buttons to layout
        layout.addWidget(self.spotify_button)
        layout.addWidget(self.discogs_button)
        layout.addWidget(self.youtube_button)
        layout.addStretch(1)

        # Set initial state
        self.spotify_button.setChecked(True)

    def _on_platform_selected(self, platform_name):
        """Handle platform selection.

        Args:
            platform_name: Name of the selected platform
        """
        # Update button states
        self.spotify_button.setChecked(platform_name == "spotify")
        self.discogs_button.setChecked(platform_name == "discogs")
        self.youtube_button.setChecked(platform_name == "youtube")

        # Update current platform
        self._current_platform = platform_name

        # Emit signal
        self.platform_changed.emit(platform_name)

    def set_current_platform(self, platform_name):
        """Programmatically set the current platform.

        Args:
            platform_name: Platform name to set
        """
        if platform_name != self._current_platform:
            self._on_platform_selected(platform_name)
