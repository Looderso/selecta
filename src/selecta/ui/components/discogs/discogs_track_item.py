"""Discogs track item component for search results."""

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


class DiscogsTrackItem(QWidget):
    """Widget to display a single Discogs release search result."""

    sync_clicked = pyqtSignal(dict)  # Emits release data on sync button click
    add_clicked = pyqtSignal(dict)  # Emits release data on add button click

    # Shared image loaders for all track items
    _url_image_loader = None
    _db_image_loader = None

    def __init__(self, release_data: dict, parent=None):
        """Initialize the Discogs release item.

        Args:
            release_data: Dictionary with release data from Discogs API
            parent: Parent widget
        """
        super().__init__(parent)
        self.release_data = release_data
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("discogsTrackItem")
        self.setMouseTracking(True)  # Enable mouse tracking for hover events

        # Track hover state
        self.is_hovered = False

        # Track button state
        self._can_add = False
        self._can_sync = False

        # Track image loading state
        self._db_image_tried = False
        self._track_id = release_data.get("id")
        self._album_id = None

        # Initialize image loaders if needed
        if DiscogsTrackItem._url_image_loader is None:
            DiscogsTrackItem._url_image_loader = ImageLoader()

        if DiscogsTrackItem._db_image_loader is None:
            DiscogsTrackItem._db_image_loader = DatabaseImageLoader()

        # Always connect to the image loader signals
        # This is important as each widget needs its own connection
        DiscogsTrackItem._url_image_loader.image_loaded.connect(self._on_url_image_loaded)
        DiscogsTrackItem._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        DiscogsTrackItem._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

        # Apply styling
        self.setStyleSheet("""
            #discogsTrackItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #discogsTrackItem:hover {
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
            #releaseYear {
                font-size: 11px;
                color: #999999;
            }
            #releaseLabel {
                font-size: 11px;
                color: #999999;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #FFFFFF;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(51, 51, 51, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(51, 51, 51, 0.5);
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

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(54, 54)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 4px;")

        # Set release image if available
        cover_image_url = self.release_data.get("thumb_url") or self.release_data.get("cover_url")

        # Set a placeholder initially
        placeholder = QPixmap(54, 54)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.cover_label.setPixmap(placeholder)

        # Try to load image from database first if we have a database ID
        if self._track_id and "db_id" in self.release_data:
            db_id = self.release_data.get("db_id")
            self.cover_label.setProperty("trackId", db_id)
            # Try loading from database
            if DiscogsTrackItem._db_image_loader:
                DiscogsTrackItem._db_image_loader.load_track_image(db_id, ImageSize.THUMBNAIL)
                self._db_image_tried = True

        # If we have an album ID, also try to load that image
        if "album_id" in self.release_data:
            self._album_id = self.release_data.get("album_id")
            self.cover_label.setProperty("albumId", self._album_id)
            # Try loading album image from database
            if DiscogsTrackItem._db_image_loader and self._album_id:
                DiscogsTrackItem._db_image_loader.load_album_image(
                    self._album_id, ImageSize.THUMBNAIL
                )

        # Store the URL for loading if we don't have a database image yet
        if cover_image_url:
            self.cover_label.setProperty("imageUrl", cover_image_url)
            # Start loading the image only if we haven't tried database loading
            if not self._db_image_tried and DiscogsTrackItem._url_image_loader:
                DiscogsTrackItem._url_image_loader.load_image(cover_image_url, 60)

        layout.addWidget(self.cover_label)

        # Release info (title, artist, year, label)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Release title
        title = self.release_data.get("title", "Unknown Title")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("trackTitle")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        # Artist name
        artist = self.release_data.get("artist", "Unknown Artist")
        self.artist_label = QLabel(artist)
        self.artist_label.setObjectName("artistName")
        info_layout.addWidget(self.artist_label)

        # Year and label in one row
        details_layout = QHBoxLayout()
        details_layout.setSpacing(10)
        details_layout.setContentsMargins(0, 0, 0, 0)

        # Year
        year = self.release_data.get("year", "")
        if year:
            self.year_label = QLabel(f"Year: {year}")
            self.year_label.setObjectName("releaseYear")
            details_layout.addWidget(self.year_label)

        # Label
        label = self.release_data.get("label", "")
        if label:
            self.label_label = QLabel(f"Label: {label}")
            self.label_label.setObjectName("releaseLabel")
            details_layout.addWidget(self.label_label)

        details_layout.addStretch(1)
        info_layout.addLayout(details_layout)

        layout.addLayout(info_layout, 1)  # 1 = stretch factor

        # Buttons layout
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setSpacing(6)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Sync button
        self.sync_button = QPushButton("Sync")
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
        self.sync_clicked.emit(self.release_data)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self.release_data)

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
