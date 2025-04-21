# src/selecta/ui/components/navigation_bar.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class NavigationBar(QWidget):
    """Navigation bar for the application."""

    # Keep existing signals
    settings_button_clicked = pyqtSignal()

    # Add platform selection signals
    library_button_clicked = pyqtSignal()  # Renamed from local_button_clicked
    spotify_button_clicked = pyqtSignal()
    rekordbox_button_clicked = pyqtSignal()
    discogs_button_clicked = pyqtSignal()
    youtube_button_clicked = pyqtSignal()

    def __init__(self, parent: QWidget):
        """Initialize the navigation bar."""
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setObjectName("navigationBar")

        # Apply styling
        self.setStyleSheet("""
            #navigationBar {
                background-color: #1E1E1E;
                border-bottom: 1px solid #333333;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                background-color: transparent;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton.active {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: bold;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        # App logo and title
        logo_label = QLabel("Selecta")
        logo_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(logo_label)

        # Add spacing
        layout.addSpacing(20)

        # Add navigation items
        self._add_platform_buttons(layout)

        # Add spacer to push settings button to the right
        layout.addStretch(1)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings_button_clicked)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.settings_button)

    def _add_platform_buttons(self, layout):
        """Add platform selection buttons."""
        # Create platform buttons
        self.library_button = QPushButton("Library")  # Renamed from local_button
        self.spotify_button = QPushButton("Spotify")
        self.rekordbox_button = QPushButton("Rekordbox")
        self.discogs_button = QPushButton("Discogs")
        self.youtube_button = QPushButton("YouTube")

        # Connect signals
        self.library_button.clicked.connect(self.library_button_clicked)  # Updated signal
        self.spotify_button.clicked.connect(self.spotify_button_clicked)
        self.rekordbox_button.clicked.connect(self.rekordbox_button_clicked)
        self.discogs_button.clicked.connect(self.discogs_button_clicked)
        self.youtube_button.clicked.connect(self.youtube_button_clicked)

        # Set cursor and add to layout
        for button in [
            self.library_button,  # Updated variable name
            self.spotify_button,
            self.rekordbox_button,
            self.discogs_button,
            self.youtube_button,
        ]:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)

    def set_active_platform(self, platform: str):
        """Set the active platform button.

        Args:
            platform: Platform name ('library', 'spotify', 'rekordbox', 'discogs')
        """
        # Remove active class from all buttons
        for button in [
            self.library_button,  # Updated variable name
            self.spotify_button,
            self.rekordbox_button,
            self.discogs_button,
            self.youtube_button,
        ]:
            button.setProperty("class", "")
            button.setStyleSheet("")

        # Set active class for the selected platform
        if platform == "library" or platform == "local":  # Support both names during transition
            self.library_button.setProperty("class", "active")
            self.library_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); color: white; font-weight: bold;"
            )
        elif platform == "spotify":
            self.spotify_button.setProperty("class", "active")
            self.spotify_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); color: white; font-weight: bold;"
            )
        elif platform == "rekordbox":
            self.rekordbox_button.setProperty("class", "active")
            self.rekordbox_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); color: white; font-weight: bold;"
            )
        elif platform == "discogs":
            self.discogs_button.setProperty("class", "active")
            self.discogs_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); color: white; font-weight: bold;"
            )
        elif platform == "youtube":
            self.youtube_button.setProperty("class", "active")
            self.youtube_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); color: white; font-weight: bold;"
            )
