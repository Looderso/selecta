"""Base class for platform search panels with shared functionality."""

from abc import abstractmethod
from typing import Any

from loguru import logger
from PyQt6.QtCore import QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget

from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.selection_state import SelectionState


class PlatformSearchPanel(LoadableWidget):
    """Abstract base class for platform search panels with shared functionality."""

    # Signals for track operations
    track_linked = pyqtSignal(dict)  # Emitted when a track is linked
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the platform search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Access the shared selection state
        self.selection_state = SelectionState()

        # Connect to selection state signals
        self.selection_state.playlist_selected.connect(self._on_global_playlist_selected)
        self.selection_state.track_selected.connect(self._on_global_track_selected)
        self.selection_state.data_changed.connect(self._on_data_changed)

    @abstractmethod
    def _on_global_playlist_selected(self, playlist: Any) -> None:
        """Handle playlist selection from the global state.

        Args:
            playlist: The selected playlist
        """
        pass

    @abstractmethod
    def _on_global_track_selected(self, track: Any) -> None:
        """Handle track selection from the global state.

        Args:
            track: The selected track
        """
        pass

    @abstractmethod
    def _on_data_changed(self) -> None:
        """Handle notification that the underlying data has changed."""
        pass

    def _handle_link_complete(self, track_data: dict[str, Any], track_name: str) -> None:
        """Handle completion of track linking with best practices.

        This method provides a standardized way to handle track linking across
        all platform search panels, ensuring consistent behavior.

        Args:
            track_data: The track/video/release data that was linked
            track_name: The name of the track for display purposes
        """
        # Emit signal with the linked track
        self.track_linked.emit(track_data)

        # Get the track ID that we linked to from the currently selected track
        selected_track = self.selection_state.get_selected_track()

        if selected_track and hasattr(selected_track, "track_id"):
            track_id = selected_track.track_id
            logger.debug(f"Updating platforms for track_id={track_id}")

            # Get updated platform list from the database
            platforms = self._get_track_platforms(track_id)
            
            # Force a direct database refresh
            try:
                # Get fresh track data from database for display
                from selecta.core.data.database import get_session
                from selecta.core.data.repositories.track_repository import TrackRepository
                
                session = get_session()
                track_repo = TrackRepository(session)
                
                # Get the complete track
                fresh_track_data = track_repo.get_by_id(track_id)
                
                if not fresh_track_data:
                    logger.warning(f"Could not find track {track_id} in database")
                else:
                    logger.debug(f"Retrieved fresh track data for track_id={track_id}")
            except Exception as e:
                logger.error(f"Error getting fresh track data: {e}")

            # Use the models property to get access to the tracks table model
            from selecta.ui.components.playlist.tracks_table_model import TracksTableModel

            # Find the active model in the UI
            tracks_model = None
            main_window = self.window()
            if main_window:
                playlist_content = main_window.findChild(QWidget, "playlistContent")
                if playlist_content and hasattr(playlist_content, "playlist_component"):
                    component = playlist_content.playlist_component
                    if hasattr(component, "tracks_model"):
                        tracks_model = component.tracks_model
                    elif hasattr(component, "track_container") and hasattr(
                        component.track_container, "tracks_model"
                    ):
                        tracks_model = component.track_container.tracks_model

            # Use the targeted update method if we found the model
            if tracks_model and isinstance(tracks_model, TracksTableModel):
                # Force a reload from database to ensure we have latest platform info
                result = tracks_model.update_track_from_database(track_id)
                logger.debug(f"Used database reload for platform update for track_id={track_id}, result={result}")
            else:
                # Fall back to the selection state mechanism if we can't find the model
                logger.debug(f"Used selection state notification for track_id={track_id}")
                self.selection_state.notify_track_updated(track_id)
                
            # Re-select the track immediately (no need for timer)
            self.selection_state.set_selected_track(selected_track)
        else:
            # Fallback to general notification if we can't get the track ID
            logger.debug("Using general data_changed notification (fallback)")
            self.selection_state.notify_data_changed()

        # Show a proper toast notification using PyQtToast
        logger.info(f"TOAST NOTIFICATION: Track '{track_name}' linked successfully!")
        try:
            # Import PyQtToast
            from pyqttoast import Toast, ToastPreset, ToastPosition
            # Create a toast notification with custom styling for more visibility
            toast = Toast(self.window())  # Use main window as parent
            toast.setTitle("Link Successful ✅")
            toast.setText(f"Track '{track_name}' linked!")
            toast.setDuration(4000)  # 4 seconds for better visibility
            toast.applyPreset(ToastPreset.SUCCESS_DARK)  # Use dark success preset
            toast.setBorderRadius(8)  # More rounded corners
            toast.setShowIcon(True)  # Show the success icon
            toast.setIconSize(QSize(20, 20))  # Larger icon
            toast.setTitleFont(QFont("Arial", 11, QFont.Weight.Bold))  # Larger title font
            toast.setTextFont(QFont("Arial", 10))  # Larger text font
            # Make sure it stays on top
            toast.setStayOnTop(True)
            # Show the toast
            toast.show()
            logger.info(f"Displayed GUI toast notification for '{track_name}'")
        except ImportError:
            # Fall back to simple message if PyQtToast isn't available
            logger.warning("PyQtToast not available, using simple message")
            self.show_message(f"✅ Track linked: {track_name}")
        except Exception as e:
            # Log any other errors but continue execution
            logger.error(f"Error showing toast: {e}")
            self.show_message(f"✅ Track linked: {track_name}")
        
        # DIRECT PANEL SWITCH: Immediately switch to track details after linking
        try:
            # Find the dynamic content container
            main_window = self.window()
            if not main_window:
                logger.error("Could not get main window")
                return
                
            # Find the dynamic content container by name
            dynamic_content = main_window.findChild(QWidget, "dynamicContent")
            if not dynamic_content:
                logger.error("Could not find dynamicContent widget")
                return
                
            # Verify it has the necessary attributes
            if not hasattr(dynamic_content, "stacked_widget") or not hasattr(dynamic_content, "track_details_panel"):
                logger.error("Dynamic content missing required attributes")
                return
                
            # Log we're about to perform the critical operations
            logger.critical(f"PANEL SWITCH: About to force update for track {track_name}")
                
            # SIMPLIFIED DIRECT APPROACH: Force a fresh database call
            if selected_track and hasattr(selected_track, "track_id"):
                # Get fresh platform info directly
                from selecta.core.data.database import get_session
                from selecta.core.data.repositories.track_repository import TrackRepository
                
                # Create fresh session
                session = get_session()
                repo = TrackRepository(session)
                
                # Get ALL platform info for the track
                track_id = selected_track.track_id
                platform_info = {}
                
                # Log all steps with high visibility
                logger.critical(f"DIRECT DB QUERY: Getting platform info for track_id={track_id}")
                
                # Query each platform
                for platform_name in ["spotify", "rekordbox", "discogs", "youtube"]:
                    info = repo.get_platform_info(track_id, platform_name)
                    if info:
                        platform_info[platform_name] = info
                        logger.critical(f"✅ FOUND {platform_name} info: id={info.platform_id}")
                
                # Force details panel update with fresh DB data
                if platform_info:
                    logger.critical(f"UPDATING panel with platforms: {list(platform_info.keys())}")
                    # Clear and update the track details
                    dynamic_content.track_details_panel.set_track(selected_track, platform_info)
                else:
                    logger.error(f"No platform info found in database for track {track_id}")
                    dynamic_content.track_details_panel.set_track(selected_track)
            
            # CRITICAL: Force the panel switch to happen AFTER the data is loaded
            logger.critical(f"SWITCHING to track details panel")
            dynamic_content.stacked_widget.setCurrentWidget(dynamic_content.track_details_panel)
            
            # Force UI update
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, main_window.update)
            
            logger.critical(f"✅ COMPLETED panel switch for track '{track_name}'")
            
        except Exception as e:
            logger.error(f"Error during panel switch: {e}", exc_info=True)

    def _get_track_platforms(self, track_id: int) -> list[str]:
        """Get updated platform information for a track.

        Retrieves just the platform list directly from the database.

        Args:
            track_id: The ID of the track to get platforms for

        Returns:
            A list of platform names the track is available on
        """
        from selecta.core.data.database import get_session
        from selecta.core.data.repositories.track_repository import TrackRepository

        try:
            # Get a fresh database session
            session = get_session()
            track_repo = TrackRepository(session)

            # Get the track with all relationships loaded
            db_track = track_repo.get_by_id(track_id)

            if not db_track:
                logger.warning(f"Track {track_id} not found in database")
                return []

            # Extract platform names from platform_info
            platforms = []

            if hasattr(db_track, "platform_info") and db_track.platform_info:
                for info in db_track.platform_info:
                    platform_name = getattr(info, "platform", None)
                    if platform_name and platform_name not in platforms:
                        platforms.append(platform_name)
                        # Commented out for less verbosity
                        # logger.debug(f"Found platform '{platform_name}' for track {track_id}")

            # Also check individual platform flags
            if hasattr(db_track, "in_collection") and db_track.in_collection:
                if "collection" not in platforms:
                    platforms.append("collection")

            if hasattr(db_track, "in_wantlist") and db_track.in_wantlist:
                if "wantlist" not in platforms:
                    platforms.append("wantlist")

            # Log platforms retrieval only in rare cases to reduce noise
            if len(platforms) > 2:
                logger.debug(f"Retrieved platforms for track {track_id}: {platforms}")
            
            # Force a platform update notification
            try:
                # Try to find active selection state
                from selecta.ui.components.selection_state import SelectionState
                selection_state = SelectionState()
                
                # Emit a track update signal to refresh UI
                selection_state.notify_track_updated(track_id)
                # Less verbose logging
                # logger.debug(f"Emitted track update notification for track_id={track_id}")
            except Exception as e:
                logger.warning(f"Could not emit track update notification: {e}")
                
            return platforms

        except Exception as e:
            logger.error(f"Error getting platforms for track_id={track_id}: {e}")
            return []
