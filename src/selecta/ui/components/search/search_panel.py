from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from selecta.ui.components.search.platform.discogs.discogs_search_panel import (
    DiscogsSearchPanel,
)
from selecta.ui.components.search.platform.spotify.spotify_search_panel import (
    SpotifySearchPanel,
)
from selecta.ui.components.search.platform.youtube.youtube_search_panel import (
    YouTubeSearchPanel,
)


class SearchPanel(QWidget):
    """Unified search panel that contains platform-specific search panels."""

    # Signals from the platform search panels
    track_linked = pyqtSignal(dict)  # Emits track data that was linked
    track_added = pyqtSignal(dict)  # Emits track data that was added

    def __init__(self, parent=None):
        """Initialize the search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self._current_platform = "spotify"

    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget for the platform-specific search panels
        self.stack = QStackedWidget()

        # Create platform-specific search panels
        self.spotify_search_panel = SpotifySearchPanel()
        self.discogs_search_panel = DiscogsSearchPanel()
        self.youtube_search_panel = YouTubeSearchPanel()

        # Connect signals from platform search panels
        self._connect_platform_signals(self.spotify_search_panel)
        self._connect_platform_signals(self.discogs_search_panel)
        self._connect_platform_signals(self.youtube_search_panel)

        # Add panels to stack
        self.stack.addWidget(self.spotify_search_panel)
        self.stack.addWidget(self.discogs_search_panel)
        self.stack.addWidget(self.youtube_search_panel)

        # Add stack to layout
        layout.addWidget(self.stack)

        # Set initial panel
        self.stack.setCurrentWidget(self.spotify_search_panel)

    def _connect_platform_signals(self, panel):
        """Connect signals from a platform search panel.

        Args:
            panel: Platform search panel to connect
        """
        panel.track_linked.connect(self._handle_track_linked)
        panel.track_added.connect(self._handle_track_added)

    def _handle_track_linked(self, track_data: dict[str, Any]):
        """Handle track linking from platform search panel.

        Args:
            track_data: Track data that was linked
        """
        # Re-emit the signal
        self.track_linked.emit(track_data)

    def _handle_track_added(self, track_data: dict[str, Any]):
        """Handle track addition from platform search panel.

        Args:
            track_data: Track data that was added
        """
        # Re-emit the signal
        self.track_added.emit(track_data)

    def set_platform(self, platform_name: str):
        """Set the current search platform.

        Args:
            platform_name: Name of the platform to set
        """
        self._current_platform = platform_name

        # Switch to the appropriate panel
        if platform_name == "spotify":
            self.stack.setCurrentWidget(self.spotify_search_panel)
        elif platform_name == "discogs":
            self.stack.setCurrentWidget(self.discogs_search_panel)
        elif platform_name == "youtube":
            self.stack.setCurrentWidget(self.youtube_search_panel)

    def set_query(self, query: str):
        """Set the search query for the current platform.

        Args:
            query: Search query to set
        """
        # Get the current platform panel
        current_panel = self.stack.currentWidget()

        # Set the query
        if hasattr(current_panel, "search"):
            current_panel.search(query)

    def search(self, query: str, platform: str | None = None):
        """Search for the given query on the specified or current platform.

        Args:
            query: Search query
            platform: Optional platform name to search on
        """
        # Set platform if specified
        if platform and platform != self._current_platform:
            self.set_platform(platform)

        # Set query
        self.set_query(query)
