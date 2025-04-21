"""Base class for platform search panels with common functionality."""

from abc import abstractmethod
from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.search.base_search_result import BaseSearchResult
from selecta.ui.components.search_bar import SearchBar
from selecta.ui.components.selection_state import SelectionState


class BaseSearchPanel(LoadableWidget):
    """Abstract base class for platform search panels.

    This class provides common functionality for all platform search panels,
    including UI structure, search logic, and result handling.
    """

    # Common signals
    track_linked = pyqtSignal(dict)  # Emitted when a track is linked
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the base search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Common attributes
        self.result_widgets: list[BaseSearchResult] = []
        self.message_label: QLabel | None = None
        self.initial_message: QLabel | None = None

        # Access the shared selection state
        self.selection_state = SelectionState()

        # Connect to selection state signals
        self.selection_state.playlist_selected.connect(self._on_global_playlist_selected)
        self.selection_state.track_selected.connect(self._on_global_track_selected)
        self.selection_state.data_changed.connect(self._on_data_changed)

        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        main_layout.addWidget(content_widget)

        # Create loading widget
        loading_widget = self._create_loading_widget(f"Searching {self.get_platform_name()}...")
        main_layout.addWidget(loading_widget)
        loading_widget.setVisible(False)

        # Setup the UI
        self._setup_base_ui(content_widget)

    def _setup_base_ui(self, content_widget: QWidget) -> None:
        """Set up the base UI components shared by all search panels.

        Args:
            content_widget: Widget to add UI components to
        """
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Header label
        self.header = QLabel(f"{self.get_platform_name()} Search")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.header)

        # Platform-specific header content
        self._setup_header_content(header_layout)

        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)

        # Search bar
        self.search_bar = SearchBar(placeholder_text=f"Search {self.get_platform_name()}...")
        self.search_bar.search_confirmed.connect(self._on_search)
        self.content_layout.addWidget(self.search_bar)

        # Results container with scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(self.scroll_area.Shape.NoFrame)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for search results
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Initial message
        self.initial_message = QLabel(f"Enter a search term to find {self.get_platform_name()} content")
        self.initial_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.initial_message.setStyleSheet("color: #888; margin: 20px 0;")
        self.results_layout.addWidget(self.initial_message)

        self.scroll_area.setWidget(self.results_container)
        self.content_layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

        # Initialize with an empty state
        self.show_message(f"Enter a search term to find {self.get_platform_name()} content")

        # Platform-specific setup
        self._setup_platform_ui()

    @abstractmethod
    def _setup_platform_ui(self) -> None:
        """Set up platform-specific UI elements.

        This method should be implemented by subclasses to add any
        platform-specific UI elements.
        """
        pass

    @abstractmethod
    def _setup_header_content(self, header_layout: QHBoxLayout) -> None:
        """Set up platform-specific header content.

        Args:
            header_layout: Layout to add header content to
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name (e.g., "Spotify", "YouTube")
        """
        pass

    def _on_global_playlist_selected(self, playlist: Any) -> None:
        """Handle playlist selection from the global state.

        Args:
            playlist: The selected playlist
        """
        # Update buttons based on the new selection
        self._update_result_buttons()

    def _on_global_track_selected(self, track: Any) -> None:
        """Handle track selection from the global state.

        Args:
            track: The selected track
        """
        # Update buttons based on the new selection
        self._update_result_buttons()

    def _on_data_changed(self) -> None:
        """Handle notification that the underlying data has changed."""
        # Refresh the current search results if we have a search term
        current_search = self.search_bar.get_search_text()
        if current_search:
            # Re-run the search to refresh results
            self._on_search(current_search)

    def _update_result_buttons(self) -> None:
        """Update all result item buttons based on current selection."""
        # Get button states from the selection state
        can_add = self.selection_state.is_playlist_selected()
        can_link = self.selection_state.is_track_selected()

        # Update all result widgets
        for widget in self.result_widgets:
            if isinstance(widget, BaseSearchResult):
                widget.update_button_state(can_add=can_add, can_link=can_link)

    @abstractmethod
    def _on_search(self, query: str) -> None:
        """Handle search query submission.

        Args:
            query: The search query
        """
        pass

    def search(self, query: str) -> None:
        """Public method to perform a search.

        Args:
            query: The search query
        """
        self.search_bar.set_search_text(query)
        self._on_search(query)

    def clear_results(self) -> None:
        """Clear all search results."""
        # Remove the initial message if it exists
        if self.initial_message is not None:
            self.initial_message.setParent(None)
            self.initial_message = None

        # Remove any message widget
        if self.message_label is not None:
            self.message_label.setParent(None)
            self.message_label = None

        # Remove all result widgets
        for widget in self.result_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.result_widgets.clear()

        # Remove spacer if it exists
        if self.results_layout.count() > 0:
            spacer_item = self.results_layout.itemAt(self.results_layout.count() - 1)
            if spacer_item is not None and spacer_item.spacerItem():
                self.results_layout.removeItem(spacer_item)

    def show_message(self, message: str) -> None:
        """Show a message in the results area.

        Args:
            message: Message to display
        """
        # Clear current results
        self.clear_results()

        # Create message label
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: #888; margin: 20px 0;")
        self.results_layout.addWidget(self.message_label)
        self.results_layout.addStretch(1)

    def _handle_link_complete(self, item_data: dict[str, Any], item_name: str) -> None:
        """Handle completion of track linking with best practices.

        This method provides a standardized way to handle track linking across
        all platform search panels, ensuring consistent behavior.

        Args:
            item_data: The track/video/release data that was linked
            item_name: The name of the item for display purposes
        """
        # Emit signal with the linked track
        self.track_linked.emit(item_data)

        # Get the track ID that we linked to from the currently selected track
        selected_track = self.selection_state.get_selected_track()

        if selected_track and hasattr(selected_track, "track_id"):
            track_id = selected_track.track_id
            logger.debug(f"Updating platforms for track_id={track_id}")

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
            from selecta.ui.components.playlist.model.tracks_table_model import TracksTableModel

            # Find the active model in the UI
            tracks_model = None
            main_window = self.window()

            # Use a safer approach with explicit type checking
            if main_window is not None:
                playlist_content = main_window.findChild(QWidget, "playlistContent")

                # Type-safe navigation with type casting for analysis tools
                if playlist_content is not None:
                    # Use getattr to avoid direct attribute access that causes type errors
                    component = getattr(playlist_content, "playlist_component", None)

                    if component is not None:
                        # Try direct tracks_model access
                        tracks_model = getattr(component, "tracks_model", None)

                        # If not found, try via track_container
                        if tracks_model is None:
                            track_container = getattr(component, "track_container", None)
                            if track_container is not None:
                                tracks_model = getattr(track_container, "tracks_model", None)

            # Use the targeted update method if we found the model
            if tracks_model and isinstance(tracks_model, TracksTableModel):
                # Force a reload from database to ensure we have latest platform info
                result = tracks_model.update_track_from_database(track_id)
                logger.debug(f"Used database reload for platform update for track_id={track_id}, result={result}")
            else:
                # Fall back to the selection state mechanism if we can't find the model
                logger.debug(f"Used selection state notification for track_id={track_id}")
                self.selection_state.notify_track_updated(track_id)

            # Re-select the track immediately
            self.selection_state.set_selected_track(selected_track)
        else:
            # Fallback to general notification if we can't get the track ID
            logger.debug("Using general data_changed notification (fallback)")
            self.selection_state.notify_data_changed()

        # Show a proper toast notification using PyQtToast
        logger.info(f"TOAST NOTIFICATION: {item_name} linked successfully!")
        try:
            # Import PyQtToast
            from PyQt6.QtCore import QSize
            from pyqttoast import Toast, ToastPreset

            # Create a toast notification with custom styling for more visibility
            toast = Toast(self.window())  # Use main window as parent
            toast.setTitle("Link Successful ✅")
            toast.setText(f"{item_name} linked!")
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
            logger.info(f"Displayed GUI toast notification for '{item_name}'")
        except ImportError:
            # Fall back to simple message if PyQtToast isn't available
            logger.warning("PyQtToast not available, using simple message")
            self.show_message(f"✅ Item linked: {item_name}")
        except Exception as e:
            # Log any other errors but continue execution
            logger.error(f"Error showing toast: {e}")
            self.show_message(f"✅ Item linked: {item_name}")

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
            logger.critical("PANEL SWITCH: About to force update for item " + item_name)

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
                # Use getattr for type-safe attribute access
                track_details_panel = getattr(dynamic_content, "track_details_panel", None)
                if track_details_panel is not None:
                    if platform_info:
                        logger.critical(f"UPDATING panel with platforms: {list(platform_info.keys())}")
                        # Clear and update the track details
                        track_details_panel.set_track(selected_track, platform_info)
                    else:
                        logger.error(f"No platform info found in database for track {track_id}")
                        track_details_panel.set_track(selected_track)

            # CRITICAL: Force the panel switch to happen AFTER the data is loaded
            logger.critical("SWITCHING to track details panel")
            # Use getattr for type-safe attribute access
            stacked_widget = getattr(dynamic_content, "stacked_widget", None)
            track_details_panel = getattr(dynamic_content, "track_details_panel", None)

            if stacked_widget is not None and track_details_panel is not None:
                stacked_widget.setCurrentWidget(track_details_panel)

            # Force UI update
            QTimer.singleShot(100, main_window.update)

            logger.critical(f"✅ COMPLETED panel switch for item '{item_name}'")

        except Exception as e:
            logger.error(f"Error during panel switch: {e}", exc_info=True)

    def _handle_add_complete(self, item_data: dict[str, Any], item_name: str) -> None:
        """Handle completion of track addition.

        Args:
            item_data: The track/video/release data that was added
            item_name: The name of the item for display purposes
        """
        # Emit signal with the added track
        self.track_added.emit(item_data)

        # Notify that data has changed
        self.selection_state.notify_data_changed()

        # Show a proper toast notification
        try:
            # Import PyQtToast
            from PyQt6.QtCore import QSize
            from pyqttoast import Toast, ToastPreset

            # Create a toast notification with custom styling for more visibility
            toast = Toast(self.window())  # Use main window as parent
            toast.setTitle("Item Added ✅")
            toast.setText(f"{item_name}")
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
            logger.info(f"Displayed GUI toast for item added: '{item_name}'")
        except ImportError:
            # Fall back to simple message if PyQtToast isn't available
            self.show_message(f"Item added: {item_name}")
        except Exception as e:
            # Log any other errors but continue execution
            logger.error(f"Error showing toast: {e}")
            self.show_message(f"Item added: {item_name}")

        # Wait a moment, then restore the search results
        QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))
