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

from selecta.core.data.models.db import ImageSize
from selecta.ui.components.image_loader import DatabaseImageLoader
from selecta.ui.components.spotify.image_loader import ImageLoader


class SpotifyTrackItem(QWidget):
    """Widget to display a single Spotify track search result."""

    sync_clicked = pyqtSignal(dict)  # Emits track data on link button click
    add_clicked = pyqtSignal(dict)  # Emits track data on add button click

    # Shared image loaders for all track items
    _url_image_loader = None
    _db_image_loader = None

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
        self.setMouseTracking(True)  # Enable mouse tracking for hover events

        # Track hover state
        self.is_hovered = False

        # Track button state
        self._can_add = False
        self._can_sync = False

        # Track image loading state
        self._db_image_tried = False
        self._track_id = track_data.get("id")
        self._album_id = None

        # Initialize image loaders if needed
        if SpotifyTrackItem._url_image_loader is None:
            SpotifyTrackItem._url_image_loader = ImageLoader()

        if SpotifyTrackItem._db_image_loader is None:
            SpotifyTrackItem._db_image_loader = DatabaseImageLoader()

        # Always connect to the image loader signals
        # This is important as each widget needs its own connection
        SpotifyTrackItem._url_image_loader.image_loaded.connect(self._on_url_image_loaded)
        SpotifyTrackItem._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        SpotifyTrackItem._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

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
            QPushButton:disabled {
                border-color: #555;
                color: #555;
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

        # Set a placeholder initially
        placeholder = QPixmap(54, 54)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.cover_label.setPixmap(placeholder)

        # Try to load image from database first if we have a database ID
        if self._track_id and "db_id" in self.track_data:
            db_id = self.track_data.get("db_id")
            self.cover_label.setProperty("trackId", db_id)
            # Try loading from database
            if SpotifyTrackItem._db_image_loader:
                SpotifyTrackItem._db_image_loader.load_track_image(db_id, ImageSize.THUMBNAIL)
                self._db_image_tried = True

        # If we have an album ID, also try to load that image
        if "album_id" in self.track_data:
            self._album_id = self.track_data.get("album_id")
            self.cover_label.setProperty("albumId", self._album_id)
            # Try loading album image from database
            if SpotifyTrackItem._db_image_loader and self._album_id:
                SpotifyTrackItem._db_image_loader.load_album_image(
                    self._album_id, ImageSize.THUMBNAIL
                )

        # Fall back to URL-based image if available
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

        # Store the URL for loading if we don't have a database image yet
        if album_image_url:
            self.cover_label.setProperty("imageUrl", album_image_url)
            # Start loading the image if we haven't tried loading from DB or if DB loading failed
            if not self._db_image_tried and SpotifyTrackItem._url_image_loader:
                SpotifyTrackItem._url_image_loader.load_image(album_image_url, 60)

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
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setSpacing(6)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Link button
        self.sync_button = QPushButton("Link")
        self.sync_button.setFixedSize(60, 25)
        self.sync_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_button.clicked.connect(self._on_sync_clicked)
        # Initially disabled until a track is selected
        self.sync_button.setEnabled(False)
        self.buttons_layout.addWidget(self.sync_button)

        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.setFixedSize(60, 25)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self._on_add_clicked)
        # Initially disabled until a playlist is selected
        self.add_button.setEnabled(False)
        self.buttons_layout.addWidget(self.add_button)

        # Add the buttons layout to the main layout
        layout.addLayout(self.buttons_layout)

        # Hide buttons initially
        self.sync_button.setVisible(False)
        self.add_button.setVisible(False)

    def update_button_state(self, can_add: bool = False, can_sync: bool = False) -> None:
        """Update the state of the buttons based on current selection.

        Args:
            can_add: Whether the add button should be enabled
            can_sync: Whether the sync button should be enabled
        """
        # Store the button states
        self._can_add = can_add
        self._can_sync = can_sync

        # Update button states
        self.add_button.setEnabled(can_add)
        self.sync_button.setEnabled(can_sync)

        # Only show buttons if we're hovered and set appropriate state
        self._update_button_visibility()

    def _on_url_image_loaded(self, url: str, pixmap: QPixmap):
        """Handle loaded image from URL.

        Args:
            url: The URL of the loaded image
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to this widget and no DB image has been loaded
        if self.cover_label.property("imageUrl") == url and not self._db_image_tried:
            self.cover_label.setPixmap(pixmap)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap):
        """Handle loaded image from database for a track.

        Args:
            track_id: The track ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to this widget
        if self.cover_label.property("trackId") == track_id:
            self.cover_label.setPixmap(pixmap)
            self._db_image_tried = True

    def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap):
        """Handle loaded image from database for an album.

        Args:
            album_id: The album ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to this widget and we don't already have a track image
        if self.cover_label.property("albumId") == album_id and not self._db_image_tried:
            self.cover_label.setPixmap(pixmap)
            self._db_image_tried = True

    def _on_sync_clicked(self):
        """Handle sync button click."""
        self.sync_clicked.emit(self.track_data)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self.track_data)

    def enterEvent(self, event):
        """Handle mouse enter events to show buttons.

        Args:
            event: The enter event
        """
        self.is_hovered = True
        self._update_button_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events to hide buttons.

        Args:
            event: The leave event
        """
        self.is_hovered = False
        self._update_button_visibility()
        super().leaveEvent(event)

    def _update_button_visibility(self):
        """Update the visibility of the buttons based on hover state."""
        if self.is_hovered:
            # When hovering, show both buttons
            self.sync_button.setVisible(True)
            self.add_button.setVisible(True)

            # Make sure the enabled state is correct
            self.sync_button.setEnabled(self._can_sync)
            self.add_button.setEnabled(self._can_add)
        else:
            # When not hovering, hide both buttons
            self.sync_button.setVisible(False)
            self.add_button.setVisible(False)
