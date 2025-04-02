from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.database import get_session
from selecta.core.data.models.db import ImageSize
from selecta.core.data.repositories.track_repository import TrackRepository
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

    # Signal emitted when track quality is changed
    quality_changed = pyqtSignal(int, int)  # track_id, new_quality

    def __init__(self, parent=None):
        """Initialize the track details panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(300)

        # Track we're currently displaying
        self._current_track_id = None
        self._current_album_id = None
        self._current_quality = -1  # NOT_RATED by default

        # Initialize the database image loader if needed
        if TrackDetailsPanel._db_image_loader is None:
            TrackDetailsPanel._db_image_loader = DatabaseImageLoader()

        # Connect to image loader signals
        TrackDetailsPanel._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        TrackDetailsPanel._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

        # Set up the UI
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

        # Quality rating section
        quality_container = QWidget()
        quality_layout = QVBoxLayout(quality_container)

        # Label for the quality section
        quality_label = QLabel("Quality Rating:")
        quality_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        quality_layout.addWidget(quality_label)

        # Quality selector dropdown
        quality_selection = QHBoxLayout()

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Not Rated", -1)
        self.quality_combo.addItem("★ Very Poor", 1)
        self.quality_combo.addItem("★★ Poor", 2)
        self.quality_combo.addItem("★★★ OK", 3)
        self.quality_combo.addItem("★★★★ Good", 4)
        self.quality_combo.addItem("★★★★★ Great", 5)

        # Connect the quality change signal
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)

        quality_selection.addWidget(self.quality_combo)
        quality_layout.addLayout(quality_selection)

        layout.addWidget(quality_container)

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

            # Reset quality dropdown
            self.quality_combo.setCurrentIndex(0)  # Not rated
            self.quality_combo.setEnabled(False)
            self._current_quality = -1
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

        # Set quality rating if available
        display_data = track.to_display_data()
        quality = display_data.get("quality", -1)
        self._current_quality = quality

        logger.debug(f"Setting quality dropdown for track {track.track_id} to {quality}")

        # Set the quality dropdown to the track's quality
        self.quality_combo.blockSignals(True)  # Prevent triggering the signal during setup

        # Find the index for the current quality value
        index = self.quality_combo.findData(quality)
        if index >= 0:
            logger.debug(f"Found quality {quality} at index {index}, setting it")
            self.quality_combo.setCurrentIndex(index)
        else:
            logger.warning(f"Quality {quality} not found in combo box, defaulting to NOT_RATED")
            self.quality_combo.setCurrentIndex(0)  # Default to "Not Rated"

        self.quality_combo.blockSignals(False)
        self.quality_combo.setEnabled(True)

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

    @pyqtSlot(int)
    def _on_quality_changed(self, index: int):
        """Handle quality rating changes.

        Args:
            index: The index of the selected quality in the combo box
        """
        logger.debug(f"Quality dropdown changed to index {index}")

        if self._current_track_id is None:
            logger.warning("No track ID available, ignoring quality change")
            return

        # Get the quality value from the combo box
        quality_data = self.quality_combo.itemData(index)

        # Ensure we have an integer
        try:
            quality = quality_data if isinstance(quality_data, int) else int(quality_data)
        except (ValueError, TypeError):
            logger.error(f"Error converting quality data to int: {quality_data}")
            quality = -1  # Default to NOT_RATED

        logger.debug(f"Quality data value: {quality}")

        # Only update if the quality has actually changed
        if quality != self._current_quality:
            self._current_quality = quality
            logger.info(
                f"Updating quality in database:"
                f" track_id={self._current_track_id}, quality={quality}"
            )

            # Update the database directly
            session = get_session()
            track_repo = TrackRepository(session)

            # Update the quality
            success = track_repo.set_track_quality(self._current_track_id, quality)

            if success:
                logger.info(f"Quality updated successfully for track {self._current_track_id}")

                # Still emit the signal for any listeners that want to know about the change
                self.quality_changed.emit(self._current_track_id, quality)

                # Force a refresh of the parent component
                # This is a hack, but we need to refresh the UI
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(100, self._notify_parent_of_change)
            else:
                logger.error(f"Failed to update quality for track {self._current_track_id}")
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Quality Update Failed",
                    f"Failed to update quality rating for track {self._current_track_id}.",
                )
        else:
            logger.debug(f"Quality unchanged from {self._current_quality}, not updating")

    def _notify_parent_of_change(self):
        """Notify the parent component that a change has occurred."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "refresh"):
                logger.debug("Found parent with refresh method, calling it")
                parent.refresh()
                break
            parent = parent.parent()

    def _clear_cards(self):
        """Clear all platform cards."""
        # Remove all widgets except the stretch at the end
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()
