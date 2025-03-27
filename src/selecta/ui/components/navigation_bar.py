# src/selecta/ui/components/navigation_bar.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class NavigationBar(QWidget):
    """Navigation bar for the application."""

    settings_button_clicked = pyqtSignal()

    def __init__(self, parent: QWidget):
        """Initialize the navigation bar."""
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setObjectName("navigationBar")

        # Make the navigation bar stand out
        self.setStyleSheet("""
            #navigationBar {
                background-color: #1E1E1E;
                border-bottom: 1px solid #333333;
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

        # Add navigation items
        self._add_nav_items(layout)

        # Add spacer to push settings button to the right
        layout.addStretch(1)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings_button_clicked)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.settings_button)

    def _add_nav_items(self, layout):
        """Add navigation menu items."""
        # Add main navigation buttons here
        nav_buttons = [
            ("Playlists", self._on_playlists_clicked),
            ("Tracks", self._on_tracks_clicked),
            ("Vinyl", self._on_vinyl_clicked),
        ]

        for text, handler in nav_buttons:
            button = QPushButton(text)
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(handler)
            layout.addWidget(button)

    def _on_playlists_clicked(self):
        """Handle playlists button click."""
        # To be implemented
        pass

    def _on_tracks_clicked(self):
        """Handle tracks button click."""
        # To be implemented
        pass

    def _on_vinyl_clicked(self):
        """Handle vinyl button click."""
        # To be implemented
        pass
