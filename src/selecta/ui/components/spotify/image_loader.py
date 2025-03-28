"""Utility for asynchronously loading images from URLs."""

import time
from threading import Thread

import httpx
from loguru import logger
from PyQt6.QtCore import QByteArray, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class ImageLoader(QObject):
    """Asynchronous image loader for loading images from URLs."""

    # Signal emitted when an image is loaded successfully
    image_loaded = pyqtSignal(str, QPixmap)

    # Signal emitted when image loading fails
    image_failed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """Initialize the image loader.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self._cache = {}  # Simple in-memory cache
        self._loading = set()  # Track URLs currently being loaded

    def load_image(self, url: str, max_size: int = 300) -> None:
        """Load an image asynchronously from a URL.

        Args:
            url: The URL of the image to load
            max_size: Maximum size (width/height) for the image
        """
        # Check cache first
        if url in self._cache:
            self.image_loaded.emit(url, self._cache[url])
            return

        # Skip if already loading
        if url in self._loading:
            return

        # Mark as loading
        self._loading.add(url)

        # Start a thread to load the image
        thread = Thread(target=self._load_image_thread, args=(url, max_size))
        thread.daemon = True
        thread.start()

    def _load_image_thread(self, url: str, max_size: int) -> None:
        """Background thread for loading an image.

        Args:
            url: The URL of the image to load
            max_size: Maximum size (width/height) for the image
        """
        try:
            start_time = time.time()

            # Download the image
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()

                # Convert to QPixmap
                image_data = QByteArray(response.content)
                image = QImage.fromData(image_data)

                if image.isNull():
                    self.image_failed.emit(url, "Invalid image data")
                    return

                # Scale if necessary
                if image.width() > max_size or image.height() > max_size:
                    image = image.scaled(
                        max_size,
                        max_size,
                        aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                        transformMode=Qt.TransformationMode.SmoothTransformation,
                    )

                pixmap = QPixmap.fromImage(image)

                # Cache the image
                self._cache[url] = pixmap

                # Emit signal with the loaded image
                self.image_loaded.emit(url, pixmap)

                logger.debug(f"Loaded image from {url} in {time.time() - start_time:.2f}s")

        except Exception as e:
            logger.error(f"Error loading image from {url}: {e}")
            self.image_failed.emit(url, str(e))
        finally:
            # Remove from loading set
            self._loading.discard(url)

    def clear_cache(self) -> None:
        """Clear the image cache."""
        self._cache.clear()
