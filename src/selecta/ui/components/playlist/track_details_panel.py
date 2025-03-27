from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

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

    def __init__(self, parent=None):
        """Initialize the track details panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Header
        self.header_label = QLabel("Track Details")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.header_label)

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

    def set_track(self, track: TrackItem | None):
        """Set the track to display.

        Args:
            track: Track item to display details for, or None to clear
        """
        # Clear existing cards
        self._clear_cards()

        if not track:
            self.header_label.setText("No Track Selected")
            return

        # Update header with track info
        self.header_label.setText(f"{track.artist} - {track.title}")

        # Get platform info from track
        display_data = track.to_display_data()
        platform_info = display_data.get("platform_info", [])

        # Create cards for each platform
        for info in platform_info:
            platform = info.get("platform", "unknown")
            card = PlatformInfoCard(platform, info)
            self.scroll_layout.insertWidget(0, card)  # Insert at the top

    def _clear_cards(self):
        """Clear all platform cards."""
        # Remove all widgets except the stretch at the end
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.deleteLater()
