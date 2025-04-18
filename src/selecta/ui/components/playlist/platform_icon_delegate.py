from PyQt6.QtCore import QModelIndex, QSize, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from selecta.core.utils.path_helper import get_resource_path


class PlatformIconDelegate(QStyledItemDelegate):
    """Delegate for drawing platform icons in the track table."""

    def __init__(self, parent=None):
        """Initialize the platform icon delegate.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.icon_size = 20
        self.spacing = 2
        # Cache platform icons
        self.platform_icons = {}
        for platform in ["spotify", "rekordbox", "discogs", "youtube", "wantlist", "collection"]:
            # Try different icon paths with scaling variations
            icon_found = False
            for icon_path_pattern in [
                f"icons/0.125x/{platform}@0.125x.png",  # Scaled versions
                f"icons/1x/{platform}.png",  # 1x version
                f"icons/{platform}.png",  # Fallback to root
            ]:
                icon_path = get_resource_path(icon_path_pattern)
                if icon_path.exists():
                    self.platform_icons[platform] = QPixmap(str(icon_path)).scaled(
                        self.icon_size,
                        self.icon_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    icon_found = True
                    break

            if not icon_found:
                print(f"Warning: Could not find icon for platform {platform}")

    def paint(self, painter: QPainter, option: "QStyleOptionViewItem", index: QModelIndex) -> None:
        """Paint the platform icons.

        Args:
            painter: QPainter to use for drawing
            option: Style options for the item
            index: Index of the item
        """
        # First, let the base class handle selection background etc.
        super().paint(painter, option, index)

        # Get the platforms from the model - ALWAYS get fresh data, never cache
        # This is critical for showing updated platform icons
        platforms = index.data(Qt.ItemDataRole.UserRole)
        
        # Force refresh data - critical for updating platforms
        # This ensures we're getting the most recent platform data
        index.model().force_refresh_data = True

        # Get track info for logging
        track_info = ""
        track_data = index.model().data(
            index.model().index(index.row(), 0), Qt.ItemDataRole.UserRole
        )
        if isinstance(track_data, dict) and "track_id" in track_data:
            track_info = f"track_id={track_data['track_id']}"

        from loguru import logger
        
        # Only log once every few seconds per track to reduce log spam
        import time
        current_time = time.time()
        
        # Use a class-level cache to avoid excessive logging
        if not hasattr(self, '_last_icon_log_times'):
            self._last_icon_log_times = {}
            
        # Only log once every 5 seconds per track
        track_id = None
        if isinstance(track_data, dict) and "track_id" in track_data:
            track_id = track_data['track_id']
            
        if track_id is not None:
            last_log_time = self._last_icon_log_times.get(track_id, 0)
            if current_time - last_log_time > 60:  # Log only once per minute per track
                logger.debug(f"Drawing platform icons for {track_info}: {platforms}")
                self._last_icon_log_times[track_id] = current_time

        if not platforms:
            return

        # Calculate total width needed
        total_width = len(platforms) * self.icon_size + (len(platforms) - 1) * self.spacing

        # Calculate starting position to center the icons
        start_x = option.rect.left() + (option.rect.width() - total_width) / 2
        y = option.rect.top() + (option.rect.height() - self.icon_size) / 2

        # Draw each platform icon
        for platform in platforms:
            icon = self.platform_icons.get(platform)
            if icon:
                painter.drawPixmap(int(start_x), int(y), icon)
                start_x += self.icon_size + self.spacing

    def sizeHint(self, option: "QStyleOptionViewItem", index: QModelIndex) -> QSize:
        """Get the size hint for the delegate.

        Args:
            option: Style options for the item
            index: Index of the item

        Returns:
            Size hint for the delegate
        """
        size = super().sizeHint(option, index)
        platforms = index.data(Qt.ItemDataRole.UserRole)
        if platforms:
            # Ensure row height is enough for the icons
            size.setHeight(max(size.height(), self.icon_size + 4))
        return size
