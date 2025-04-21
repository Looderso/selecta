"""Image loader utility for search components."""

import threading
from collections.abc import Callable

import requests
from loguru import logger
from PyQt6.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class SearchImageLoader(QObject):
    """Image loader for search result items.

    This class provides asynchronous image loading capabilities for search results
    across different platforms. It handles caching, network requests, and PyQt signals
    for image loading completion.
    """

    # Signal emitted when an image is loaded
    image_loaded = pyqtSignal(str, QPixmap)  # url, pixmap

    # Signal emitted when an image load fails
    image_load_failed = pyqtSignal(str, str)  # url, error message

    # Singleton instance
    _instance = None

    def __new__(cls):
        """Create a singleton instance of the image loader.

        Returns:
            The singleton SearchImageLoader instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the image loader."""
        if self._initialized:
            return

        super().__init__()

        # Cache of loaded images
        self._cache: dict[str, QPixmap] = {}

        # Cache expiration time (in seconds)
        self._cache_ttl = 300  # 5 minutes

        # Lock for thread safety
        self._lock = threading.RLock()

        # Set initialized flag
        self._initialized = True

    def load_image(self, url: str, callback: Callable[[QPixmap], None] | None = None) -> None:
        """Load an image from a URL.

        Args:
            url: URL of the image to load
            callback: Optional callback to call when the image is loaded
        """
        if not url:
            logger.warning("No URL provided to image loader")
            if callback:
                callback(self._create_placeholder())
            return

        # Check cache first
        with self._lock:
            if url in self._cache:
                logger.debug(f"Image found in cache: {url}")
                pixmap = self._cache[url]
                if callback:
                    callback(pixmap)
                self.image_loaded.emit(url, pixmap)
                return

        # Load the image in a background thread
        def load_thread():
            try:
                # Set appropriate headers
                headers = {
                    "User-Agent": "Selecta/1.0 +https://github.com/Looderso/selecta (Music Library App)",
                    "Referer": "https://www.discogs.com/",
                }

                # Download the image - special handling for Discogs URLs
                if "discogs.com" in url or "i.discogs.com" in url:
                    logger.debug(f"Using Discogs headers for: {url}")
                    response = requests.get(url, headers=headers, timeout=10)
                else:
                    response = requests.get(url, timeout=10)

                if not response.ok:
                    logger.warning(f"Failed to download image: {url}, status: {response.status_code}")
                    if callback:
                        callback(self._create_placeholder())
                    self.image_load_failed.emit(url, f"HTTP error: {response.status_code}")
                    return

                # Create image from data
                image_data = response.content
                image = QImage()
                if not image.loadFromData(image_data):
                    logger.warning(f"Failed to create image from data: {url}")
                    if callback:
                        callback(self._create_placeholder())
                    self.image_load_failed.emit(url, "Failed to create image from data")
                    return

                # Convert to pixmap
                pixmap = QPixmap.fromImage(image)

                # Cache the image
                with self._lock:
                    self._cache[url] = pixmap

                # Signal that the image is loaded
                self.image_loaded.emit(url, pixmap)

                # Call the callback
                if callback:
                    callback(pixmap)

                logger.debug(f"Image loaded successfully: {url}")

            except Exception as e:
                logger.error(f"Error loading image: {e}")
                if callback:
                    callback(self._create_placeholder())
                self.image_load_failed.emit(url, str(e))

        # Start the thread
        thread = threading.Thread(target=load_thread)
        thread.daemon = True
        thread.start()

    def get_cached_image(self, url: str) -> QPixmap | None:
        """Get an image from the cache.

        Args:
            url: URL of the image to get

        Returns:
            The cached image pixmap, or None if not in cache
        """
        with self._lock:
            return self._cache.get(url)

    def clear_cache(self) -> None:
        """Clear the image cache."""
        with self._lock:
            self._cache.clear()

    def _create_placeholder(self, size: QSize | None = None) -> QPixmap:
        """Create a placeholder image.

        Args:
            size: Size of the placeholder

        Returns:
            A placeholder pixmap
        """
        if size is None:
            size = QSize(100, 100)

        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.darkGray)
        return pixmap


# Convenience function to get the singleton instance
def get_image_loader() -> SearchImageLoader:
    """Get the singleton image loader instance.

    Returns:
        The singleton SearchImageLoader instance
    """
    return SearchImageLoader()
