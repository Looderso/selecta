from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.models.db import ImageSize
from selecta.ui.components.image_loader import DatabaseImageLoader
from selecta.ui.components.playlist.track_item import TrackItem


class PlatformInfoCard(QFrame):
    """Card displaying platform-specific information."""

    def __init__(self, platform: str, info: dict, parent=None):
        """Initialize the platform info card.

        Args:
            platform: Platform name
            info: Platform-specific information
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(0)

        # Set background color based on platform
        self.setStyleSheet(self._get_platform_style(platform))

        layout = QVBoxLayout(self)

        # Platform header
        header_layout = QHBoxLayout()
        platform_icon = QLabel()  # You would set the platform icon here
        platform_name = QLabel(platform.capitalize())
        platform_name.setStyleSheet("font-weight: bold; font-size: 14px;")

        header_layout.addWidget(platform_icon)
        header_layout.addWidget(platform_name, 1)  # 1 = stretch factor
        layout.addLayout(header_layout)

        # Platform-specific info
        for key, value in info.items():
            if key == "platform":
                continue  # Skip the platform key itself

            info_layout = QHBoxLayout()
            key_label = QLabel(f"{key.replace('_', ' ').capitalize()}:")
            key_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)

            info_layout.addWidget(key_label)
            info_layout.addWidget(value_label, 1)  # 1 = stretch factor
            layout.addLayout(info_layout)

    def _get_platform_style(self, platform: str) -> str:
        """Get the style for a platform.

        Args:
            platform: Platform name

        Returns:
            CSS style string
        """
        match platform:
            case "spotify":
                return "background-color: #1DB954; color: white; border-radius: 5px;"
            case "rekordbox":
                return "background-color: #0082CD; color: white; border-radius: 5px;"
            case "discogs":
                return "background-color: #333333; color: white; border-radius: 5px;"
            case _:
                return "background-color: #888888; color: white; border-radius: 5px;"


class TrackDetailsPanel(QWidget):
    """Panel displaying detailed information about a track."""

    # Shared image loader
    _db_image_loader = None

    def __init__(self, parent=None):
        """Initialize the track details panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(300)

        # Initialize the database image loader if needed
        if TrackDetailsPanel._db_image_loader is None:
            TrackDetailsPanel._db_image_loader = DatabaseImageLoader()

        # Connect to image loader signals
        TrackDetailsPanel._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        TrackDetailsPanel._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

        # Track the current track and album IDs
        self._current_track_id = None
        self._current_album_id = None

        layout = QVBoxLayout(self)

        # Header
        self.header_label = QLabel("Track Details")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.header_label)

        # Album artwork
        self.image_container = QWidget()
        self.image_layout = QHBoxLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Set placeholder
        placeholder = QPixmap(200, 200)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.image_label.setPixmap(placeholder)

        self.image_layout.addWidget(self.image_label)
        layout.addWidget(self.image_container)

        # Create scroll area for platform cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for cards
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)  # Push cards to the top

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

    def set_track(self, track: TrackItem | None, platform_info: dict[str, Any] = None):
        """Set the track to display.

        Args:
            track: Track item to display details for, or None to clear
            platform_info: Optional dictionary of platform info objects keyed by platform name
        """
        # Clear existing cards
        self._clear_cards()

        if not track:
            self.header_label.setText("No Track Selected")
            # Reset image
            placeholder = QPixmap(200, 200)
            placeholder.fill(Qt.GlobalColor.darkGray)
            self.image_label.setPixmap(placeholder)
            self._current_track_id = None
            self._current_album_id = None
            return

        # Update header with track info
        self.header_label.setText(f"{track.artist} - {track.title}")

        # Get platform info from track or use provided platform_info
        if platform_info:
            # Process platform info from database
            for platform_name, info in platform_info.items():
                if info:
                    # Create card for each platform
                    platform_data = {
                        "platform": platform_name,
                    }

                    # If platform_data is a JSON string, parse it
                    if info.platform_data:
                        import json

                        try:
                            platform_metadata = json.loads(info.platform_data)
                            # Add all metadata to platform_data dictionary
                            for key, value in platform_metadata.items():
                                platform_data[key] = value
                        except json.JSONDecodeError:
                            pass

                    # Add platform ID and URI
                    platform_data["id"] = info.platform_id
                    platform_data["uri"] = info.platform_uri

                    # Create and add the card
                    card = PlatformInfoCard(platform_name, platform_data)
                    self.scroll_layout.insertWidget(0, card)
        else:
            # Get platform info from track's display data
            display_data = track.to_display_data()
            track_platform_info = display_data.get("platform_info", [])

            # Create cards for each platform
            for info in track_platform_info:
                platform = info.get("platform", "unknown")
                card = PlatformInfoCard(platform, info)
                self.scroll_layout.insertWidget(0, card)  # Insert at the top

        # Try to load the track image
        self._current_track_id = track.track_id
        self._current_album_id = track.album_id

        # Load track image from database if available
        if hasattr(track, "has_image") and track.has_image and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_track_image(track.track_id, ImageSize.MEDIUM)

        # Also try to load the album image as a fallback
        if hasattr(track, "album_id") and track.album_id and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_album_image(track.album_id, ImageSize.MEDIUM)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap):
        """Handle loaded image from database for a track.

        Args:
            track_id: The track ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to the current track
        if track_id == self._current_track_id:
            self.image_label.setPixmap(pixmap)

    def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap):
        """Handle loaded image from database for an album.

        Args:
            album_id: The album ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to the current album and we don't already have a track image
        if album_id == self._current_album_id and self.image_label.pixmap().width() <= 200:
            self.image_label.setPixmap(pixmap)

    def _clear_cards(self):
        """Clear all platform cards."""
        # Remove all widgets except the stretch at the end
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()
