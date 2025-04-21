"""Delegate for displaying track quality ratings."""

from PyQt6.QtCore import QModelIndex, QRect, QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem


class TrackQualityDelegate(QStyledItemDelegate):
    """Delegate for displaying quality ratings as colored dots."""

    def __init__(self, parent=None):
        """Initialize the track quality delegate.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.dot_size = 16
        self.color_map = {
            -1: QColor(150, 150, 150),  # Grey for NOT_RATED
            1: QColor(255, 50, 50),  # Red for very poor
            2: QColor(255, 200, 50),  # Yellow/orange for poor
            3: QColor(100, 200, 50),  # Green for ok
            4: QColor(50, 150, 255),  # Blue for good
            5: QColor(200, 50, 255),  # Purple for great
        }

    def paint(self, painter: QPainter, option: "QStyleOptionViewItem", index: QModelIndex) -> None:
        """Paint the quality rating dot.

        Args:
            painter: QPainter to use for drawing
            option: Style options for the item
            index: Index of the item
        """
        # First, let the base class handle selection background etc.
        super().paint(painter, option, index)

        # Get the quality value from the model
        quality = index.data(Qt.ItemDataRole.UserRole)
        if quality is None:
            quality = -1  # Default to NOT_RATED

        # Get the color for this quality rating
        color = self.color_map.get(quality, self.color_map[-1])

        # Calculate center position for the dot
        x_center = option.rect.left() + option.rect.width() // 2
        y_center = option.rect.top() + option.rect.height() // 2

        # Draw the dot
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw shadow/border
        painter.setPen(QPen(QColor(80, 80, 80, 100), 1))
        painter.setBrush(QBrush(color.darker(110)))
        painter.drawEllipse(
            QRect(
                x_center - self.dot_size // 2 + 1,
                y_center - self.dot_size // 2 + 1,
                self.dot_size,
                self.dot_size,
            )
        )

        # Draw the main dot
        painter.setPen(QPen(color.darker(130), 1))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(
            QRect(
                x_center - self.dot_size // 2,
                y_center - self.dot_size // 2,
                self.dot_size,
                self.dot_size,
            )
        )

    def sizeHint(self, option: "QStyleOptionViewItem", index: QModelIndex) -> QSize:
        """Get the size hint for the delegate.

        Args:
            option: Style options for the item
            index: Index of the item

        Returns:
            Size hint for the delegate
        """
        size = super().sizeHint(option, index)
        # Ensure row height is enough for the dot
        size.setHeight(max(size.height(), self.dot_size + 4))
        return size
