"""Utility for asynchronously loading images from the database."""

import time
from threading import Thread

from loguru import logger
from PyQt6.QtCore import QByteArray, QObject, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from selecta.core.data.models.db import ImageSize
from selecta.core.data.repositories.image_repository import ImageRepository


class DatabaseImageLoader(QObject):
    """Asynchronous image loader for loading images from the database."""

    # Signal emitted when an image is loaded successfully
    image_loaded = pyqtSignal(str, QPixmap)
    album_image_loaded = pyqtSignal(int, QPixmap)
    track_image_loaded = pyqtSignal(int, QPixmap)

    # Signal emitted when image loading fails
    image_failed = pyqtSignal(str, str)
    album_image_failed = pyqtSignal(int, str)
    track_image_failed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        """Initialize the database image loader.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self._cache = {}  # Simple in-memory cache: keys: "track_<id>_<size>" or "album_<id>_<size>"
        self._loading = set()  # Track keys currently being loaded

        # Create a persistent session for the image repository
        from selecta.core.data.database import get_session

        session = get_session()
        self._image_repo = ImageRepository(session)

    def load_track_image(self, track_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> None:
        """Load a track's image from the database.

        Args:
            track_id: The track ID
            size: Desired image size
        """
        # Create a unique key for this request
        cache_key = f"track_{track_id}_{size.name}"

        # Check cache first
        if cache_key in self._cache:
            self.track_image_loaded.emit(track_id, self._cache[cache_key])
            return

        # Skip if already loading
        if cache_key in self._loading:
            return

        # Mark as loading
        self._loading.add(cache_key)

        # Start a thread to load the image
        thread = Thread(target=self._load_track_image_thread, args=(track_id, size, cache_key))
        thread.daemon = True
        thread.start()

    def load_album_image(self, album_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> None:
        """Load an album's image from the database.

        Args:
            album_id: The album ID
            size: Desired image size
        """
        # Create a unique key for this request
        cache_key = f"album_{album_id}_{size.name}"

        # Check cache first
        if cache_key in self._cache:
            self.album_image_loaded.emit(album_id, self._cache[cache_key])
            return

        # Skip if already loading
        if cache_key in self._loading:
            return

        # Mark as loading
        self._loading.add(cache_key)

        # Start a thread to load the image
        thread = Thread(target=self._load_album_image_thread, args=(album_id, size, cache_key))
        thread.daemon = True
        thread.start()

    def _load_track_image_thread(self, track_id: int, size: ImageSize, cache_key: str) -> None:
        """Background thread for loading a track's image.

        Args:
            track_id: The track ID
            size: Desired image size
            cache_key: Unique cache key for this request
        """
        try:
            start_time = time.time()

            # Get image from repository
            image = self._image_repo.get_track_image(track_id, size)

            if not image or not image.data:
                self.track_image_failed.emit(track_id, "Image not found")
                return

            # Convert to QPixmap
            pixmap = self._create_pixmap_from_image_data(image.data)

            if pixmap is None:
                self.track_image_failed.emit(track_id, "Failed to create pixmap")
                return

            # Cache the pixmap
            self._cache[cache_key] = pixmap

            # Emit signal with the loaded image
            self.track_image_loaded.emit(track_id, pixmap)

            logger.debug(f"Loaded track image {track_id} in {time.time() - start_time:.2f}s")

        except Exception as e:
            logger.error(f"Error loading track image {track_id}: {e}")
            self.track_image_failed.emit(track_id, str(e))
        finally:
            # Remove from loading set
            self._loading.discard(cache_key)

    def _load_album_image_thread(self, album_id: int, size: ImageSize, cache_key: str) -> None:
        """Background thread for loading an album's image.

        Args:
            album_id: The album ID
            size: Desired image size
            cache_key: Unique cache key for this request
        """
        try:
            start_time = time.time()

            # Get image from repository
            image = self._image_repo.get_album_image(album_id, size)

            if not image or not image.data:
                self.album_image_failed.emit(album_id, "Image not found")
                return

            # Convert to QPixmap
            pixmap = self._create_pixmap_from_image_data(image.data)

            if pixmap is None:
                self.album_image_failed.emit(album_id, "Failed to create pixmap")
                return

            # Cache the pixmap
            self._cache[cache_key] = pixmap

            # Emit signal with the loaded image
            self.album_image_loaded.emit(album_id, pixmap)

            logger.debug(f"Loaded album image {album_id} in {time.time() - start_time:.2f}s")

        except Exception as e:
            logger.error(f"Error loading album image {album_id}: {e}")
            self.album_image_failed.emit(album_id, str(e))
        finally:
            # Remove from loading set
            self._loading.discard(cache_key)

    def _create_pixmap_from_image_data(self, image_data: bytes) -> QPixmap | None:
        """Create a QPixmap from image binary data.

        Args:
            image_data: Binary image data

        Returns:
            QPixmap object or None if conversion fails
        """
        try:
            # Convert binary data to QImage
            byte_array = QByteArray(image_data)
            image = QImage.fromData(byte_array)

            if image.isNull():
                return None

            return QPixmap.fromImage(image)
        except Exception as e:
            logger.error(f"Error creating pixmap: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the image cache."""
        self._cache.clear()
