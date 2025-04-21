from PyQt6.QtWidgets import QCheckBox, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


class SpotifySettingsPanel(QWidget):
    """Panel for Spotify-specific settings."""

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
        header = QLabel("Spotify Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Playlist filters group
        playlist_group = QGroupBox("Playlist Filters")
        playlist_layout = QVBoxLayout(playlist_group)

        # Filter checkboxes
        self.ignore_shared = QCheckBox("Ignore shared playlists")
        self.ignore_followed = QCheckBox("Ignore followed playlists")
        self.filter_collaborative = QCheckBox("Filter by collaborative status")

        playlist_layout.addWidget(self.ignore_shared)
        playlist_layout.addWidget(self.ignore_followed)
        playlist_layout.addWidget(self.filter_collaborative)

        content_layout.addWidget(playlist_group)

        # Synchronization settings group
        sync_group = QGroupBox("Synchronization Settings")
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.addWidget(QLabel("Spotify synchronization settings will appear here"))
        content_layout.addWidget(sync_group)

        # Add stretch to push groups to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
