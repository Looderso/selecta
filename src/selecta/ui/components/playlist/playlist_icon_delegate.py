"""Delegate for drawing platform icons in playlist items."""

from PyQt6.QtCore import QModelIndex, QSize, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from selecta.core.utils.path_helper import get_resource_path
from selecta.core.utils.type_helpers import has_synced_platforms


class PlaylistIconDelegate(QStyledItemDelegate):
    """Delegate for drawing platform icons in playlist tree items."""

    def __init__(self, parent=None):
        """Initialize the playlist icon delegate.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.icon_size = 16  # Slightly smaller than track icons for better appearance in tree
        self.spacing = 2
        self.padding = 4  # Padding after main icon before platform icons

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
                from loguru import logger

                logger.warning(f"Could not find icon for platform {platform}")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint the playlist item with platform icons.

        Args:
            painter: QPainter to use for drawing
            option: Style options for the item
            index: Index of the item
        """
        # First, let the standard delegate draw the item (background, text, etc.)
        super().paint(painter, option, index)

        # Get the item from the index
        item = index.internalPointer()
        if not item or not has_synced_platforms(item):
            return

        # Get the platforms from the item
        platforms = item.get_platform_icons()
        if not platforms:
            return

        # Calculate the position for platform icons
        # We need to find the end of the text to place our icons
        text = index.data(Qt.ItemDataRole.DisplayRole)
        text_rect = option.fontMetrics.boundingRect(text)

        # Start position is after the text plus padding, and centered vertically
        start_x = option.rect.left() + text_rect.width() + 20 + self.padding
        y = option.rect.top() + (option.rect.height() - self.icon_size) / 2

        # Draw each platform icon
        for platform in platforms:
            icon = self.platform_icons.get(platform)
            if icon:
                painter.drawPixmap(int(start_x), int(y), icon)
                start_x += self.icon_size + self.spacing

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Get the size hint for the delegate.

        Args:
            option: Style options for the item
            index: Index of the item

        Returns:
            Size hint for the delegate
        """
        size = super().sizeHint(option, index)

        # If this item has platform icons, make it taller
        item = index.internalPointer()
        if item and has_synced_platforms(item) and item.get_platform_icons():
            # Ensure row height is enough for the icons and add extra width
            size.setHeight(max(size.height(), self.icon_size + 4))

            # Add extra width for platform icons
            platforms = item.get_platform_icons()
            extra_width = len(platforms) * (self.icon_size + self.spacing) + self.padding
            size.setWidth(size.width() + extra_width)

        return size
