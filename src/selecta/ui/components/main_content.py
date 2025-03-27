# src/selecta/ui/components/main_content.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class MainContent(QWidget):
    """Main content area placeholder."""

    def __init__(self, parent=None) -> None:
        """Initialize the main content area."""
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Create a title
        title = QLabel("Welcome to Selecta")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")

        # Create a subtitle
        subtitle = QLabel("Your unified music library manager")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px; color: #AAAAAA; margin-bottom: 40px;")

        # Create a description
        description = QLabel(
            "Selecta helps you organize your music collection across Rekordbox, Spotify,"
            " and Discogs.\n\n"
            "Use the navigation bar above to manage your playlists, tracks, and vinyl collection.\n"
            "Click the Settings button to configure your platform connections."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; line-height: 1.5;")

        # Add widgets to layout
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(description)
        layout.addStretch(2)
