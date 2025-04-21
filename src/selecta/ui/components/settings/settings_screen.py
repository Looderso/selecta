from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget


class SettingsScreen(QWidget):
    """Main settings screen component that replaces the main content when active."""

    closed = pyqtSignal()  # Emitted when settings screen is closed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_category = "general"

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with title and close button
        header = QWidget()
        header.setObjectName("settingsHeader")
        header.setStyleSheet("#settingsHeader { background-color: #1E1E1E; border-bottom: 1px solid #333; }")
        header.setFixedHeight(60)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 15, 0)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        close_button = QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 24px;
                color: #AAAAAA;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.closed.emit)
        header_layout.addWidget(close_button)

        layout.addWidget(header)

        # Content area with sidebar and stacked widget
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create and add sidebar navigation
        from selecta.ui.components.settings.settings_navigation import SettingsNavigation

        self.navigation = SettingsNavigation()
        self.navigation.category_changed.connect(self._on_category_changed)
        content_layout.addWidget(self.navigation)

        # Create and add content stack
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack, 1)  # 1 = stretch factor

        # Add settings panels to the stack
        from selecta.ui.components.settings.auth_settings_panel import AuthSettingsPanel
        from selecta.ui.components.settings.discogs_settings_panel import DiscogsSettingsPanel
        from selecta.ui.components.settings.general_settings_panel import GeneralSettingsPanel
        from selecta.ui.components.settings.rekordbox_settings_panel import RekordboxSettingsPanel
        from selecta.ui.components.settings.spotify_settings_panel import SpotifySettingsPanel
        from selecta.ui.components.settings.youtube_settings_panel import YouTubeSettingsPanel

        self.general_panel = GeneralSettingsPanel()
        self.auth_panel = AuthSettingsPanel()
        self.rekordbox_panel = RekordboxSettingsPanel()
        self.discogs_panel = DiscogsSettingsPanel()
        self.spotify_panel = SpotifySettingsPanel()
        self.youtube_panel = YouTubeSettingsPanel()

        self.content_stack.addWidget(self.general_panel)
        self.content_stack.addWidget(self.auth_panel)
        self.content_stack.addWidget(self.rekordbox_panel)
        self.content_stack.addWidget(self.discogs_panel)
        self.content_stack.addWidget(self.spotify_panel)
        self.content_stack.addWidget(self.youtube_panel)

        layout.addWidget(content, 1)  # 1 = stretch factor

        # Set initial state
        self.navigation.set_active_category("general")
        self.content_stack.setCurrentWidget(self.general_panel)

    def _on_category_changed(self, category):
        """Handle category change from navigation.

        Args:
            category: Name of the selected category
        """
        self._current_category = category

        # Update content stack
        if category == "general":
            self.content_stack.setCurrentWidget(self.general_panel)
        elif category == "auth":
            self.content_stack.setCurrentWidget(self.auth_panel)
        elif category == "rekordbox":
            self.content_stack.setCurrentWidget(self.rekordbox_panel)
        elif category == "discogs":
            self.content_stack.setCurrentWidget(self.discogs_panel)
        elif category == "spotify":
            self.content_stack.setCurrentWidget(self.spotify_panel)
        elif category == "youtube":
            self.content_stack.setCurrentWidget(self.youtube_panel)
