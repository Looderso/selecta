from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

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
        self.parent_window = self.window()

        # Set size policy to expand in both directions
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Initialize database using the configured path
        initialize_database()

        # Create a basic repository to check for data
        repo = PlaylistRepository()
        playlists = repo.get_all()
        logger.info(f"Found {len(playlists)} playlists in database")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create a title
        title = QLabel("Playlists")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Create data provider
        data_provider = LocalPlaylistDataProvider()

        # Create playlist component
        self.playlist_component = PlaylistComponent(data_provider)
        # Set size policy to expand
        self.playlist_component.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Connect track selection signal
        self.playlist_component.track_selected.connect(self._on_track_selected)

        layout.addWidget(self.playlist_component, 1)  # Add with stretch factor of 1

        # If no playlists, show a message
        if not playlists:
            message = QLabel(
                "No playlists found."
                " Run the app in Dev Mode or initialize the database with sample data."
            )
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setStyleSheet("color: #888; margin-top: 20px;")
            layout.addWidget(message)

    def _on_track_selected(self, track):
        """Handle track selection to show details panel.

        Args:
            track: The selected track
        """
        # We need to access the details panel directly since the window() method
        # isn't returning the SelectaMainWindow instance correctly
        if hasattr(self.playlist_component, "details_panel"):
            details_panel = self.playlist_component.details_panel
            details_panel.set_track(track)
