"""Spotify track item component for search results."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.spotify.image_loader import ImageLoader


class SpotifyTrackItem(QWidget):
    """Widget to display a single Spotify track search result."""

    sync_clicked = pyqtSignal(dict)  # Emits track data on sync button click
    add_clicked = pyqtSignal(dict)  # Emits track data on add button click

    # Shared image loader for all track items
    _image_loader = None

    def __init__(self, track_data: dict, parent=None):
        """Initialize the Spotify track item.

        Args:
            track_data: Dictionary with track data from Spotify API
            parent: Parent widget
        """
        super().__init__(parent)
        self.track_data = track_data
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("spotifyTrackItem")

        # Initialize image loader if needed
        if SpotifyTrackItem._image_loader is None:
            SpotifyTrackItem._image_loader = ImageLoader()

        # Always connect to the image loader signals
        # This is important as each widget needs its own connection
        SpotifyTrackItem._image_loader.image_loaded.connect(self._on_image_loaded)

        # Apply styling
        self.setStyleSheet("""
            #spotifyTrackItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #spotifyTrackItem:hover {
                background-color: #333333;
            }
            #trackTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #artistName {
                font-size: 12px;
                color: #B3B3B3;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #1DB954;
                border-radius: 4px;
                color: #1DB954;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(29, 185, 84, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(29, 185, 84, 0.2);
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Album cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(54, 54)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 4px;")

        # Set album image if available
        album_image_url = None
        if "album" in self.track_data and "images" in self.track_data["album"]:
            images = self.track_data["album"]["images"]
            if images:
                # Find smallest image that's at least 60x60
                for image in sorted(images, key=lambda x: x.get("width", 0)):
                    if image.get("width", 0) >= 60:
                        album_image_url = image.get("url")
                        break
                # If no suitable image found, use the first one
                if not album_image_url and images:
                    album_image_url = images[0].get("url")

        # Set a placeholder initially
        placeholder = QPixmap(54, 54)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.cover_label.setPixmap(placeholder)

        # Store the URL for loading
        if album_image_url:
            self.cover_label.setProperty("imageUrl", album_image_url)
            # Start loading the image
            if SpotifyTrackItem._image_loader:
                SpotifyTrackItem._image_loader.load_image(album_image_url, 60)

        layout.addWidget(self.cover_label)

        # Track info (title and artist)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Track title
        self.title_label = QLabel(self.track_data.get("name", "Unknown Title"))
        self.title_label.setObjectName("trackTitle")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        # Artist name
        artist_names = []
        if "artists" in self.track_data:
            artist_names = [artist.get("name", "") for artist in self.track_data["artists"]]
        artist_text = ", ".join(artist_names) if artist_names else "Unknown Artist"
        self.artist_label = QLabel(artist_text)
        self.artist_label.setObjectName("artistName")
        info_layout.addWidget(self.artist_label)

        layout.addLayout(info_layout, 1)  # 1 = stretch factor

        # Buttons layout
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Sync button
        self.sync_button = QPushButton("Sync")
        self.sync_button.setFixedSize(60, 25)
        self.sync_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_button.clicked.connect(self._on_sync_clicked)
        buttons_layout.addWidget(self.sync_button)

        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.setFixedSize(60, 25)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self._on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        layout.addLayout(buttons_layout)

    def _on_image_loaded(self, url: str, pixmap: QPixmap):
        """Handle loaded image.

        Args:
            url: The URL of the loaded image
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to this widget
        if self.cover_label.property("imageUrl") == url:
            self.cover_label.setPixmap(pixmap)

    def _on_sync_clicked(self):
        """Handle sync button click."""
        self.sync_clicked.emit(self.track_data)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self.track_data)
