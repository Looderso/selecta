# src/selecta/ui/components/playlist/platform_icon_delegate.py
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
        self.icon_size = 16
        self.spacing = 2
        # Cache platform icons
        self.platform_icons = {}
        for platform in ["spotify", "rekordbox", "discogs"]:
            icon_path = get_resource_path(f"icons/{platform}.png")
            if icon_path.exists():
                self.platform_icons[platform] = QPixmap(str(icon_path)).scaled(
                    self.icon_size,
                    self.icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

    def paint(self, painter: QPainter, option: "QStyleOptionViewItem", index: QModelIndex) -> None:
        """Paint the platform icons.

        Args:
            painter: QPainter to use for drawing
            option: Style options for the item
            index: Index of the item
        """
        # First, let the base class handle selection background etc.
        super().paint(painter, option, index)

        # Get the platforms from the model
        platforms = index.data(Qt.ItemDataRole.UserRole)
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
