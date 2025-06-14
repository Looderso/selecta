"""Cache management utilities for platform data."""

import time
from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class CacheEntry(Generic[T]):
    """A cache entry with data and timestamp."""

    def __init__(self, data: T, timestamp: float):
        """Initialize a cache entry.

        Args:
            data: The cached data
            timestamp: When the data was cached
        """
        self.data = data
        self.timestamp = timestamp


class CacheManager:
    """Manages caching of platform data with timeout-based invalidation."""

    def __init__(self, default_timeout: float = 300.0):
        """Initialize the cache manager.

        Args:
            default_timeout: Default cache timeout in seconds (5 minutes)
        """
        self._cache: dict[str, CacheEntry[Any]] = {}
        self.default_timeout = default_timeout

    def set(self, key: str, data: Any, timeout: float | None = None) -> None:
        """Cache data with the given key.

        Args:
            key: Cache key
            data: Data to cache
            timeout: Optional custom timeout for this entry
        """
        self._cache[key] = CacheEntry(data, time.time())

    def get(self, key: str, default: Any = None, ignore_expiry: bool = False) -> Any:
        """Get cached data if it exists and is valid.

        Args:
            key: Cache key
            default: Value to return if cache miss or invalid
            ignore_expiry: If True, return data even if expired

        Returns:
            Cached data or default value
        """
        entry = self._cache.get(key)
        if entry and (ignore_expiry or not self._is_expired(entry, self.default_timeout)):
            return entry.data
        return default

    def _is_expired(self, entry: CacheEntry[Any], timeout: float) -> bool:
        """Check if a cache entry is expired.

        Args:
            entry: The cache entry
            timeout: Timeout in seconds

        Returns:
            True if the entry is expired, False otherwise
        """
        return (time.time() - entry.timestamp) > timeout

    def has_valid(self, key: str, timeout: float | None = None) -> bool:
        """Check if the cache has valid data for a key.

        Args:
            key: Cache key
            timeout: Optional custom timeout to check against

        Returns:
            True if data exists and is valid, False otherwise
        """
        entry = self._cache.get(key)
        if not entry:
            return False

        check_timeout = timeout if timeout is not None else self.default_timeout
        return not self._is_expired(entry, check_timeout)

    def has(self, key: str) -> bool:
        """Check if the cache has data for a key, regardless of expiry.

        Args:
            key: Cache key

        Returns:
            True if data exists, False otherwise
        """
        return key in self._cache

    def invalidate(self, key: str) -> None:
        """Remove an item from the cache.

        Args:
            key: Cache key to invalidate
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def get_or_set(self, key: str, data_getter: Callable, timeout: float | None = None) -> Any:
        """Get cached data or set it if not available.

        Args:
            key: Cache key
            data_getter: Function to call to get fresh data
            timeout: Optional custom timeout

        Returns:
            Cached or fresh data
        """
        if self.has_valid(key, timeout):
            return self.get(key)

        # Get fresh data and cache it
        fresh_data = data_getter()
        self.set(key, fresh_data, timeout)
        return fresh_data
