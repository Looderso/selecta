"""Enhanced cache manager for playlist components.

This module provides an improved cache manager implementation that addresses
issues with the current caching system, particularly focusing on reducing
unnecessary reloads when switching between platforms.
"""

import pickle
import time
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

from loguru import logger

from selecta.ui.components.playlist.interfaces import ICacheManager


class EnhancedCacheManager(ICacheManager):
    """Enhanced cache manager for playlist components.

    This cache manager provides both in-memory and disk caching with
    proper invalidation controls to prevent unnecessary reloads.
    """

    def __init__(
        self,
        default_timeout: float = 300.0,
        disk_cache_dir: Path | None = None,
        enable_disk_cache: bool = True,
    ):
        """Initialize the enhanced cache manager.

        Args:
            default_timeout: Default cache timeout in seconds (default: 5 minutes)
            disk_cache_dir: Directory to store disk cache (default: ~/.selecta/cache)
            enable_disk_cache: Whether to enable disk caching for persistence between runs
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._default_timeout = default_timeout
        self._lock = Lock()  # Thread safety for cache operations

        # Disk cache settings
        self._enable_disk_cache = enable_disk_cache
        if disk_cache_dir:
            self._disk_cache_dir = disk_cache_dir
        else:
            home_dir = Path.home()
            self._disk_cache_dir = home_dir / ".selecta" / "cache"

        # Create disk cache directory if it doesn't exist
        if self._enable_disk_cache:
            self._disk_cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.

        Args:
            key: Cache key
            default: Default value to return if key not found

        Returns:
            Cached value or default
        """
        with self._lock:
            # Check if the key exists in memory cache
            if key in self._cache:
                cache_entry = self._cache[key]

                # Check if the entry is expired
                if "expiry" in cache_entry and cache_entry["expiry"] < time.time():
                    # Entry is expired, but keep it in case we need to fall back to it
                    logger.debug(f"Cache entry for {key} is expired")

                    # Return expired data if we requested it specifically
                    return cache_entry["value"]

                # Entry exists and is valid
                return cache_entry["value"]

            # If not in memory cache, try disk cache if enabled
            if self._enable_disk_cache:
                disk_value = self._load_from_disk(key)
                if disk_value is not None:
                    # Found in disk cache, store in memory for faster access
                    self._cache[key] = {
                        "value": disk_value,
                        "expiry": time.time() + self._default_timeout,
                    }
                    return disk_value

        # Not found in any cache
        return default

    def set(self, key: str, value: Any, timeout: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Optional timeout in seconds (uses default if None)
        """
        if timeout is None:
            timeout = self._default_timeout

        with self._lock:
            expiry = time.time() + timeout
            self._cache[key] = {"value": value, "expiry": expiry}

            # Also save to disk if enabled
            if self._enable_disk_cache:
                self._save_to_disk(key, value)

    def delete(self, key: str) -> None:
        """Delete a value from the cache.

        Args:
            key: Cache key to delete
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

            # Also delete from disk if enabled
            if self._enable_disk_cache:
                self._delete_from_disk(key)

    def has(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        with self._lock:
            return key in self._cache

    def has_valid(self, key: str) -> bool:
        """Check if a key exists in the cache and is not expired.

        Args:
            key: Cache key

        Returns:
            True if key exists and is valid, False otherwise
        """
        with self._lock:
            if key in self._cache:
                cache_entry = self._cache[key]
                return not ("expiry" in cache_entry and cache_entry["expiry"] < time.time())

            # Check disk cache if enabled
            if self._enable_disk_cache:
                disk_value = self._load_from_disk(key)
                if disk_value is not None:
                    # Found in disk cache, store in memory with default expiry
                    self._cache[key] = {
                        "value": disk_value,
                        "expiry": time.time() + self._default_timeout,
                    }
                    return True

            return False

    def get_or_set(self, key: str, default_func: Callable[[], Any], timeout: float | None = None) -> Any:
        """Get a value from the cache, or set it if not present.

        Args:
            key: Cache key
            default_func: Function to call to get default value if key not found
            timeout: Optional timeout in seconds

        Returns:
            Cached value or result of default_func
        """
        # Check if the key exists and is valid
        if self.has_valid(key):
            return self.get(key)

        # Key doesn't exist or is expired, call the default function
        value = default_func()

        # Set the value in the cache
        self.set(key, value, timeout)

        return value

    def clear(self) -> None:
        """Clear all values from the cache."""
        with self._lock:
            self._cache.clear()

            # Also clear disk cache if enabled
            if self._enable_disk_cache:
                try:
                    for file_path in self._disk_cache_dir.glob("*.cache"):
                        file_path.unlink()
                except Exception as e:
                    logger.warning(f"Error clearing disk cache: {e}")

    def invalidate(self, key: str) -> None:
        """Invalidate a cached value without removing it.

        This marks the value as expired but keeps it in the cache.

        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self._cache:
                # Set expiry to now, making it immediately expired
                self._cache[key]["expiry"] = time.time()

    def _get_disk_cache_path(self, key: str) -> Path:
        """Get the file path for a disk cache key.

        Args:
            key: Cache key

        Returns:
            Path to the cache file
        """
        # Replace any characters that would be invalid in filenames
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self._disk_cache_dir / f"{safe_key}.cache"

    def _save_to_disk(self, key: str, value: Any) -> bool:
        """Save a value to disk cache.

        Args:
            key: Cache key
            value: Value to save

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self._get_disk_cache_path(key)
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            logger.warning(f"Error saving to disk cache: {e}")
            return False

    def _load_from_disk(self, key: str) -> Any | None:
        """Load a value from disk cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            cache_path = self._get_disk_cache_path(key)
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Error loading from disk cache: {e}")
        return None

    def _delete_from_disk(self, key: str) -> bool:
        """Delete a value from disk cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self._get_disk_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            return True
        except Exception as e:
            logger.warning(f"Error deleting from disk cache: {e}")
            return False


# Create a version of EnhancedCacheManager with disk caching disabled
# for use in tests and when persistence is not required
class MemoryCacheManager(EnhancedCacheManager):
    """Memory-only version of EnhancedCacheManager.

    This cache manager operates identically to EnhancedCacheManager
    but does not persist any data to disk.
    """

    def __init__(self, default_timeout: float = 300.0):
        """Initialize the memory cache manager.

        Args:
            default_timeout: Default cache timeout in seconds (default: 5 minutes)
        """
        super().__init__(default_timeout=default_timeout, enable_disk_cache=False)
