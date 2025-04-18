"""Selection state manager for sharing state between components."""

from typing import Any

from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from selecta.core.utils.type_helpers import has_is_folder


class SelectionState(QObject):
    """Class to manage and share selection state between components.

    This is implemented as a singleton to ensure there's only one state object
    across the application.
    """

    # Signals for selection changes
    playlist_selected = pyqtSignal(object)  # Emits the selected playlist item
    track_selected = pyqtSignal(object)  # Emits the selected track item
    data_changed = pyqtSignal()  # Emitted when underlying data changes (after add/sync)
    track_updated = pyqtSignal(int)  # Emitted when a track is updated (pass track_id)

    # Singleton instance
    _instance = None

    def __new__(cls):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the selection state manager."""
        if self._initialized:
            return

        super().__init__()
        self.current_playlist = None
        self.current_track = None
        self._initialized = True
        self._last_data_change_time = 0
        self._last_track_update_times = {}

        logger.debug("SelectionState initialized")

    def set_selected_playlist(self, playlist: Any) -> None:
        """Set the currently selected playlist.

        Args:
            playlist: The selected playlist object
        """
        if self.current_playlist != playlist:
            old_id = (
                getattr(self.current_playlist, "item_id", None) if self.current_playlist else None
            )
            new_id = getattr(playlist, "item_id", None) if playlist else None

            self.current_playlist = playlist
            logger.debug(f"Global playlist selection changed: {old_id} -> {new_id}")

            # Emit signal
            self.playlist_selected.emit(playlist)

    def set_selected_track(self, track: Any) -> None:
        """Set the currently selected track.

        Args:
            track: The selected track object
        """
        if self.current_track != track:
            old_id = getattr(self.current_track, "track_id", None) if self.current_track else None
            new_id = getattr(track, "track_id", None) if track else None

            self.current_track = track
            logger.debug(f"Global track selection changed: {old_id} -> {new_id}")

            # Emit signal
            self.track_selected.emit(track)

    def notify_data_changed(self) -> None:
        """Notify all observers that the underlying data has changed."""
        # Add debouncing to prevent notification storms
        import time
        current_time = time.time()
        
        # Only allow one notification per 0.5 seconds
        if current_time - self._last_data_change_time < 0.5:
            logger.debug("Data change notification throttled")
            return
            
        self._last_data_change_time = current_time
        logger.debug("Data change notification sent")
        self.data_changed.emit()

    def notify_track_updated(self, track_id: int) -> None:
        """Notify all observers that a specific track has been updated.

        Args:
            track_id: The ID of the track that was updated
        """
        # Add debouncing to prevent notification storms for the same track
        import time
        current_time = time.time()
        
        # Only allow one notification per track per 0.5 seconds
        if track_id in self._last_track_update_times and current_time - self._last_track_update_times[track_id] < 0.5:
            logger.debug(f"Track update notification throttled for track_id={track_id}")
            return
            
        self._last_track_update_times[track_id] = current_time
        logger.debug(f"Track update notification sent for track_id={track_id}")
        
        # Force a refresh of the track via full database lookup with a bit of delay
        # This ensures we get completely fresh data including all platform links
        from PyQt6.QtCore import QTimer
        
        def emit_after_delay():
            logger.debug(f"Delayed track update signal emitted for track_id={track_id}")
            self.track_updated.emit(track_id)
            
        # Small delay to ensure database writes are complete
        QTimer.singleShot(100, emit_after_delay)

    def get_selected_playlist_id(self) -> Any:
        """Get the ID of the currently selected playlist.

        Returns:
            The playlist ID or None if no playlist is selected
        """
        if self.current_playlist is None:
            return None

        return getattr(self.current_playlist, "item_id", None)

    def get_selected_track(self) -> Any:
        """Get the currently selected track.

        Returns:
            The selected track object or None if no track is selected
        """
        return self.current_track

    def is_playlist_selected(self) -> bool:
        """Check if a playlist is currently selected.

        Returns:
            True if a playlist is selected, False otherwise
        """
        return self.current_playlist is not None and not self._is_folder(self.current_playlist)

    def is_track_selected(self) -> bool:
        """Check if a track is currently selected.

        Returns:
            True if a track is selected, False otherwise
        """
        return self.current_track is not None

    def _is_folder(self, item: Any) -> bool:
        """Check if an item is a folder.

        Args:
            item: The item to check

        Returns:
            True if the item is a folder, False otherwise
        """
        if item is None:
            return False

        # Use the TypeGuard to check for is_folder method or _is_folder attribute
        if has_is_folder(item):
            # If it has is_folder method, call it
            if hasattr(item, "is_folder") and callable(item.is_folder):
                return item.is_folder()
            # Otherwise use the _is_folder attribute
            return bool(item._is_folder)

        return False