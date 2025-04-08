"""Utility for asynchronously loading images from the database."""

import time

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

        # Use ThreadManager instead of raw Thread for better performance
        from selecta.core.utils.worker import ThreadManager

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(self._load_track_image_task, track_id, size, cache_key)

        # Connect signals
        worker.signals.error.connect(
            lambda err: self._handle_track_image_error(track_id, err, cache_key)
        )
        worker.signals.finished.connect(lambda: self._loading.discard(cache_key))

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

        # Use ThreadManager instead of raw Thread for better performance
        from selecta.core.utils.worker import ThreadManager

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(self._load_album_image_task, album_id, size, cache_key)

        # Connect signals
        worker.signals.error.connect(
            lambda err: self._handle_album_image_error(album_id, err, cache_key)
        )
        worker.signals.finished.connect(lambda: self._loading.discard(cache_key))

    def _load_track_image_task(
        self, track_id: int, size: ImageSize, cache_key: str
    ) -> QPixmap | None:
        """Task function for loading a track's image using ThreadManager.

        Args:
            track_id: The track ID
            size: Desired image size
            cache_key: Unique cache key for this request

        Returns:
            QPixmap if successful, None otherwise
        """
        start_time = time.time()

        # Get image from repository
        image = self._image_repo.get_track_image(track_id, size)

        if not image or not image.data:
            return None

        # Convert to QPixmap
        pixmap = self._create_pixmap_from_image_data(image.data)

        if pixmap is None:
            return None

        # Cache the pixmap
        self._cache[cache_key] = pixmap

        # Emit signal with result - will be handled by the main thread
        logger.debug(f"Loaded track image {track_id} in {time.time() - start_time:.2f}s")

        # We return the pixmap, and the Worker will pass it to the result signal
        # We'll connect to the signal in the load method
        self.track_image_loaded.emit(track_id, pixmap)
        return pixmap

    def _handle_track_image_error(self, track_id: int, error: str, cache_key: str) -> None:
        """Handle errors from track image loading.

        Args:
            track_id: The track ID
            error: Error message
            cache_key: Cache key to clean up
        """
        logger.error(f"Error loading track image {track_id}: {error}")
        self.track_image_failed.emit(track_id, error)

    def _load_album_image_task(
        self, album_id: int, size: ImageSize, cache_key: str
    ) -> QPixmap | None:
        """Task function for loading an album's image using ThreadManager.

        Args:
            album_id: The album ID
            size: Desired image size
            cache_key: Unique cache key for this request

        Returns:
            QPixmap if successful, None otherwise
        """
        start_time = time.time()

        # Get image from repository
        image = self._image_repo.get_album_image(album_id, size)

        if not image or not image.data:
            return None

        # Convert to QPixmap
        pixmap = self._create_pixmap_from_image_data(image.data)

        if pixmap is None:
            return None

        # Cache the pixmap
        self._cache[cache_key] = pixmap

        # Log performance
        logger.debug(f"Loaded album image {album_id} in {time.time() - start_time:.2f}s")

        # Emit signal with the loaded image
        self.album_image_loaded.emit(album_id, pixmap)
        return pixmap

    def _handle_album_image_error(self, album_id: int, error: str, cache_key: str) -> None:
        """Handle errors from album image loading.

        Args:
            album_id: The album ID
            error: Error message
            cache_key: Cache key to clean up
        """
        logger.error(f"Error loading album image {album_id}: {error}")
        self.album_image_failed.emit(album_id, error)

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
