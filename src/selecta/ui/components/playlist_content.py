from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from selecta.core.data.init_db import initialize_database
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.ui.components.playlist.local.local_playlist_data_provider import (
    LocalPlaylistDataProvider,
)
from selecta.ui.components.playlist.playlist_component import PlaylistComponent


class PlaylistContent(QWidget):
    """Playlist content for the main area."""

    def __init__(self, parent=None) -> None:
        """Initialize the playlist content area."""
        super().__init__(parent)

        # Initialize database using the configured path
        initialize_database()

        # Create a basic repository to check for data
        repo = PlaylistRepository()
        playlists = repo.get_all()
        logger.info(f"Found {len(playlists)} playlists in database")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create a title
        title = QLabel("Playlists")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Create data provider
        data_provider = LocalPlaylistDataProvider()

        # Create playlist component
        self.playlist_component = PlaylistComponent(data_provider)
        layout.addWidget(self.playlist_component)

        # If no playlists, show a message
        if not playlists:
            message = QLabel(
                "No playlists found."
                " Run the app in Dev Mode or initialize the database with sample data."
            )
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setStyleSheet("color: #888; margin-top: 20px;")
            layout.addWidget(message)
