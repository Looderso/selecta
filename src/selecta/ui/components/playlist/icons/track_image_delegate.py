"""Delegate for rendering track images in tables."""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QItemDelegate, QStyle

from selecta.core.data.models.db import ImageSize
from selecta.ui.components.image_loader import DatabaseImageLoader


class TrackImageDelegate(QItemDelegate):
    """Delegate for rendering track images in tables."""

    # Shared image loader for all instances
    _db_image_loader = None

    def __init__(self, parent=None):
        """Initialize the track image delegate.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._loaded_images = {}  # Cache for loaded images by id

        # Initialize the DB image loader if needed
        if TrackImageDelegate._db_image_loader is None:
            TrackImageDelegate._db_image_loader = DatabaseImageLoader()

        # Connect to the image loader signals
        TrackImageDelegate._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        TrackImageDelegate._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap):
        """Handle loaded image from database for a track.

        Args:
            track_id: The track ID
            pixmap: The loaded image pixmap
        """
        # Store the image in our cache
        cache_key = f"track_{track_id}"
        self._loaded_images[cache_key] = pixmap

        # Request a repaint of the view
        parent = self.parent()
        if parent is not None and hasattr(parent, "viewport"):
            viewport = parent.viewport()
            if viewport is not None:
                viewport.update()

    def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap):
        """Handle loaded image from database for an album.

        Args:
            album_id: The album ID
            pixmap: The loaded image pixmap
        """
        # Store the image in our cache
        cache_key = f"album_{album_id}"
        self._loaded_images[cache_key] = pixmap

        # Request a repaint of the view
        parent = self.parent()
        if parent is not None and hasattr(parent, "viewport"):
            viewport = parent.viewport()
            if viewport is not None:
                viewport.update()

    def paint(self, painter, option, index):
        """Paint the delegate.

        Args:
            painter: QPainter
            option: QStyleOptionViewItem
            index: QModelIndex
        """
        # Get the track data from the model
        track_data = index.data(Qt.ItemDataRole.UserRole)

        if not track_data:
            # Fall back to default painting if no track data
            super().paint(painter, option, index)
            return

        # Check if we need to render an image
        track_id = track_data.get("track_id")
        album_id = track_data.get("album_id")
        has_image = track_data.get("has_image", False)

        if not (track_id or album_id):
            # Fall back to default painting if no track or album ID
            super().paint(painter, option, index)
            return

        # Check if we already have the image cached
        track_cache_key = f"track_{track_id}" if track_id else None
        album_cache_key = f"album_{album_id}" if album_id else None

        pixmap = None

        # Try to get the track image first
        if track_cache_key and track_cache_key in self._loaded_images:
            pixmap = self._loaded_images[track_cache_key]
        # Fall back to album image
        elif album_cache_key and album_cache_key in self._loaded_images:
            pixmap = self._loaded_images[album_cache_key]
        # If we don't have either image, try to load them
        else:
            if has_image and track_id and TrackImageDelegate._db_image_loader:
                TrackImageDelegate._db_image_loader.load_track_image(track_id, ImageSize.THUMBNAIL)
            if album_id and TrackImageDelegate._db_image_loader:
                TrackImageDelegate._db_image_loader.load_album_image(album_id, ImageSize.THUMBNAIL)

        # Prepare the option for rendering
        if painter is not None and option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Get the text from the display role
        text = index.data(Qt.ItemDataRole.DisplayRole)

        # Calculate the image and text positions
        image_size = 40  # Size of the thumbnail
        padding = 5  # Padding between image and text

        # Calculate the image rect
        image_rect = QRect(
            option.rect.left() + padding,
            option.rect.top() + (option.rect.height() - image_size) // 2,
            image_size,
            image_size,
        )

        # Calculate the text rect
        text_rect = QRect(
            image_rect.right() + padding,
            option.rect.top(),
            option.rect.width() - image_rect.width() - padding * 3,
            option.rect.height(),
        )

        # Draw the image if we have one
        if pixmap:
            # Scale the pixmap to the image rect
            scaled_pixmap = pixmap.scaled(
                image_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if painter is not None:
                painter.drawPixmap(image_rect, scaled_pixmap)
        else:
            # Draw a placeholder rect
            if painter is not None:
                painter.save()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(option.palette.dark())
                painter.drawRect(image_rect)
                painter.restore()

        # Draw the text
        if text and painter is not None:
            painter.save()
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(option.palette.text().color())

            # Align text vertically in the middle
            text_rect.adjust(0, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            painter.restore()

    def sizeHint(self, option, index):
        """Get the size hint for the delegate.

        Args:
            option: QStyleOptionViewItem
            index: QModelIndex

        Returns:
            QSize with the size hint
        """
        # Return a size that accommodates the image and text
        return QSize(200, 50)  # Height of 50px to accommodate a 40px image + padding
