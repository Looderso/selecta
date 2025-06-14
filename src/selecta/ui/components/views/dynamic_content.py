"""Dynamic content controller for the main window.

This component handles switching between views (track details, playlist details, search)
based on context and user actions.
"""

from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from selecta.core.data.models.db import Track, TrackPlatformInfo
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.common.selection_state import SelectionState
from selecta.ui.components.search.search_panel import SearchPanel
from selecta.ui.components.search.search_platform_tabs import SearchPlatformTabs
from selecta.ui.components.sync.sync_center import SyncCenter
from selecta.ui.components.views.dynamic_content_navigation import DynamicContentNavigationBar
from selecta.ui.components.views.playlist_details_panel import PlaylistDetailsPanel
from selecta.ui.components.views.track_details_panel import TrackDetailsPanel
from selecta.ui.widgets.loading_widget import LoadableWidget


class DynamicContent(LoadableWidget):
    """Controller for switching between track details, playlist details, and search panels."""

    # Signal to indicate that track was updated in database
    track_updated = pyqtSignal(int)  # Emits track_id when updated

    def __init__(self, parent=None) -> None:
        """Initialize the dynamic content controller.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        # Set object name to make it easier to find
        self.setObjectName("dynamicContent")
        self._setup_ui()

        # Track the current state
        self._current_track_id = None
        self._current_platform = None
        self._track_repo = TrackRepository()
        self._platform_clients = {}  # Cache platform clients

        # Connect signals from search panel
        self.search_panel.track_linked.connect(self._handle_track_linked)
        self.search_panel.track_added.connect(self._handle_track_added)

        # Connect to selection state
        self.selection_state = SelectionState()
        self.selection_state.track_selected.connect(self._on_track_selected)
        self.selection_state.playlist_selected.connect(self._on_playlist_selected)

        # Initialize state
        self._current_view = "details"
        self._current_search_platform = "spotify"
        self._has_track_selection = False
        self._has_playlist_selection = False

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        layout.addWidget(content_widget)

        # Create loading widget (will be added in show_loading)
        loading_widget = self._create_loading_widget("Loading...")
        layout.addWidget(loading_widget)
        loading_widget.setVisible(False)

        # Content layout
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top navigation bar
        self.nav_bar = DynamicContentNavigationBar()
        self.nav_bar.view_changed.connect(self._on_view_changed)
        content_layout.addWidget(self.nav_bar)

        # Search platform tabs (hidden initially)
        self.search_platform_tabs = SearchPlatformTabs()
        self.search_platform_tabs.platform_changed.connect(self._on_search_platform_changed)
        self.search_platform_tabs.setVisible(False)
        content_layout.addWidget(self.search_platform_tabs)

        # Stacked widget for swapping panels
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # Create panels
        self.track_details_panel = TrackDetailsPanel()
        self.playlist_details_panel = PlaylistDetailsPanel()
        self.playlist_details_panel.sync_requested.connect(self._on_sync_requested)

        # Empty state panel
        self.empty_panel = QWidget()
        empty_layout = QVBoxLayout(self.empty_panel)
        self.empty_message = QLabel("Select a track or playlist to view details")
        self.empty_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_message.setStyleSheet("color: #888; margin: 20px;")
        empty_layout.addWidget(self.empty_message)

        # Search panel
        self.search_panel = SearchPanel()

        # Sync center
        self.sync_center = SyncCenter()

        # Add panels to stacked widget
        self.stack.addWidget(self.track_details_panel)
        self.stack.addWidget(self.playlist_details_panel)
        self.stack.addWidget(self.empty_panel)
        self.stack.addWidget(self.search_panel)
        self.stack.addWidget(self.sync_center)

        # Set initial state
        self.stack.setCurrentWidget(self.empty_panel)

    def _on_view_changed(self, view_name: str) -> None:
        """Handle view selection from navigation bar.

        Args:
            view_name: Name of the selected view
        """
        self._current_view = view_name

        if view_name == "details":
            # Show details view based on selection
            self.search_platform_tabs.setVisible(False)
            self._update_details_view()
        elif view_name == "search":
            # Show search view
            self.search_platform_tabs.setVisible(True)
            self.stack.setCurrentWidget(self.search_panel)

            # Set current search platform
            self.search_panel.set_platform(self._current_search_platform)
        elif view_name == "sync":
            # Show sync center
            self.search_platform_tabs.setVisible(False)
            self.stack.setCurrentWidget(self.sync_center)

    def _on_search_platform_changed(self, platform_name: str) -> None:
        """Handle search platform change.

        Args:
            platform_name: Name of the selected platform
        """
        self._current_search_platform = platform_name

        # Update search panel if it's visible
        if self._current_view == "search":
            self.search_panel.set_platform(platform_name)

    def _on_track_selected(self, track: Any) -> None:
        """Handle track selection.

        Args:
            track: The selected track
        """
        # Set selection state flags
        self._has_track_selection = track is not None

        # When a track is selected, clear playlist selection to avoid ambiguity
        if track is not None:
            self._has_playlist_selection = False
            # Also clear the current playlist in selection state to ensure consistency
            self.selection_state.set_selected_playlist(None)

        # Always switch to details view when a track is selected
        if track is not None and self._current_view != "details":
            self.nav_bar.set_current_view("details")
            self._current_view = "details"
            self.search_platform_tabs.setVisible(False)

        # Update details view
        if self._current_view == "details":
            self._update_details_view()

        # Update navigation bar state
        has_selection = self._has_track_selection or self._has_playlist_selection
        self.nav_bar.set_details_enabled(has_selection)

        if not track:
            return

        # Store current track ID
        self._current_track_id = track.track_id

        # Get track from database by ID if it's a local track
        if hasattr(track, "is_local") and track.is_local:
            # Show loading indicator
            self.show_loading("Loading track details...")

            # Get track details from database
            def get_track_details() -> tuple[Track | None, dict[str, TrackPlatformInfo | None]]:
                track_data = self._track_repo.get_by_id(self._current_track_id or 0)

                # Get platform info for all platforms
                platform_info = {}
                for platform in ["spotify", "discogs", "youtube", "rekordbox"]:
                    info = self._track_repo.get_platform_info(self._current_track_id or 0, platform)
                    if info:
                        platform_info[platform] = info

                return track_data, platform_info

            # Run in background thread
            thread_manager = ThreadManager()
            worker = thread_manager.run_task(get_track_details)

            # Handle results
            worker.signals.result.connect(self._handle_track_details_loaded)
            worker.signals.error.connect(self._handle_track_details_error)
            worker.signals.finished.connect(lambda: self.hide_loading())
        else:
            # For non-local tracks, just show the track details directly
            self._show_track_details(track)

    def _on_playlist_selected(self, playlist: Any) -> None:
        """Handle playlist selection.

        Args:
            playlist: The selected playlist or None
        """
        # Set selection state flags
        self._has_playlist_selection = playlist is not None

        # When a playlist is selected, clear track selection to avoid ambiguity
        if playlist is not None:
            self._has_track_selection = False
            # Also clear the current track in selection state to ensure consistency
            self.selection_state.set_selected_track(None)

        # Always switch to details view when a playlist is selected
        if playlist is not None and self._current_view != "details":
            self.nav_bar.set_current_view("details")
            self._current_view = "details"
            self.search_platform_tabs.setVisible(False)

        # Update details view
        if self._current_view == "details":
            self._update_details_view()

        # Update navigation bar state
        has_selection = self._has_track_selection or self._has_playlist_selection
        self.nav_bar.set_details_enabled(has_selection)

    def _update_details_view(self) -> None:
        """Update the details view based on current selection."""
        # Get current selections
        track = self.selection_state.get_selected_track()
        playlist = self.selection_state.current_playlist

        # Determine which panel to show based on most recent selection
        if self._has_track_selection and track is not None:
            # Show track details
            logger.debug("Showing track details panel")
            self.track_details_panel.set_track(track)
            self.stack.setCurrentWidget(self.track_details_panel)
        elif self._has_playlist_selection and playlist is not None:
            # Show playlist details
            logger.debug("Showing playlist details panel")
            self.playlist_details_panel.set_playlist(playlist)
            self.stack.setCurrentWidget(self.playlist_details_panel)
        else:
            # Show empty state
            logger.debug("Showing empty panel - no selection")
            self.stack.setCurrentWidget(self.empty_panel)

    def _handle_track_details_loaded(self, result: tuple[Track | None, dict[str, TrackPlatformInfo | None]]) -> None:
        """Handle loaded track details from database.

        Args:
            result: Tuple containing (track_data, platform_info)
        """
        track_data, platform_info = result

        if not track_data:
            logger.warning(f"Track with ID {self._current_track_id} not found in database")
            self._show_track_details(None)
            return

        # Show track details
        self._show_track_details(track_data, platform_info)

    def _handle_track_details_error(self, error: str) -> None:
        """Handle error when loading track details.

        Args:
            error: Error message
        """
        logger.error(f"Error loading track details: {error}")
        self._show_track_details(None)

    def _show_track_details(self, track: Any, platform_info: dict[str, Any] | None = None) -> None:
        """Show track details panel with the given track.

        Args:
            track: Track to display
            platform_info: Optional platform info for the track
        """
        # Set track in details panel
        self.track_details_panel.set_track(track, platform_info)

        # Show track details panel
        self.stack.setCurrentWidget(self.track_details_panel)

    def _handle_track_linked(self, track_data: dict[str, Any]) -> None:
        """Handle track linking from search panel.

        Args:
            track_data: Track data that was linked
        """
        # Emit signal to notify that track was updated
        if self._current_track_id:
            self.track_updated.emit(self._current_track_id)
            logger.debug(f"Emitted track_updated signal for track_id={self._current_track_id}")

            # SIMPLIFIED DIRECT APPROACH: Get track and force refresh now
            logger.info(f"DIRECT REFRESH: Forcing immediate reload after linking for track {self._current_track_id}")

            try:
                # Load track and all platform info directly
                track_db = self._track_repo.get_by_id(self._current_track_id)

                if not track_db:
                    logger.warning(f"Cannot find track {self._current_track_id} in database")
                    return

                # Get ALL platform info directly from DB
                all_platform_info = {}
                for platform in ["spotify", "discogs", "youtube", "rekordbox"]:
                    info = self._track_repo.get_platform_info(self._current_track_id or 0, platform)
                    if info:
                        logger.info(f"Found platform info for {platform}: {info}")
                        all_platform_info[platform] = info

                # Get the currently selected track from selection state
                current_track = self.selection_state.get_selected_track()

                if not current_track:
                    logger.warning("No track in selection state to update")
                    return

                # Force switch to the track details panel
                self.stack.setCurrentWidget(self.track_details_panel)

                # IMPORTANT: Force the track details panel to reload with fresh platform info
                logger.info(f"Setting track details with platform info for: {list(all_platform_info.keys())}")
                self.track_details_panel.set_track(current_track, all_platform_info)

            except Exception as e:
                logger.error(f"Error during direct track refresh: {e}")

    def _handle_track_added(self, track_data: dict[str, Any]) -> None:
        """Handle track add from search panel.

        Args:
            track_data: Track data that was added
        """
        # Notify data change
        self.selection_state.notify_data_changed()

    def _on_sync_requested(self, platform: str) -> None:
        """Handle sync request from playlist details panel.

        Args:
            platform: Platform to sync with
        """
        logger.info(f"Sync requested for platform: {platform}")
        # Implementation would handle the sync process
        pass

    def show_search_panel(self, platform: str = "spotify", query: str = "") -> None:
        """Public method to show search panel.

        Args:
            platform: Platform to search on
            query: Optional initial search query
        """
        # Update state
        self._current_search_platform = platform
        self.search_platform_tabs.set_current_platform(platform)

        # Switch to search view
        self.nav_bar.set_current_view("search")

        # Set search query if provided
        if query:
            self.search_panel.set_query(query)

    def show_track_details(self, track: Any | None = None) -> None:
        """Public method to show track details.

        Args:
            track: Track to display or None for currently selected
        """
        # If track provided, update selection
        if track is not None:
            self.selection_state.set_selected_track(track)

        # Switch to details view
        self.nav_bar.set_current_view("details")

    def show_playlist_details(self, playlist: Any | None = None) -> None:
        """Public method to show playlist details.

        Args:
            playlist: Playlist to display or None for currently selected
        """
        # If playlist provided, update selection
        if playlist is not None:
            self.selection_state.set_selected_playlist(playlist)

        # Switch to details view
        self.nav_bar.set_current_view("details")

    def _get_platform_client(self, platform: str) -> AbstractPlatform | None:
        """Get or create platform client.

        Args:
            platform: Platform name

        Returns:
            Platform client or None if not available
        """
        if platform not in self._platform_clients:
            from selecta.core.data.repositories.settings_repository import SettingsRepository

            settings_repo = SettingsRepository()
            client = PlatformFactory.create(platform, settings_repo)
            self._platform_clients[platform] = client

        return self._platform_clients.get(platform)
