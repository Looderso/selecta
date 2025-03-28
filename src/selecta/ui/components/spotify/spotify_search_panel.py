"""Spotify search panel for searching and displaying Spotify tracks."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.ui.components.search_bar import SearchBar
from selecta.ui.components.spotify.spotify_track_item import SpotifyTrackItem


class SpotifySearchPanel(QWidget):
    """Panel for searching and displaying Spotify tracks."""

    track_synced = pyqtSignal(dict)  # Emitted when a track is synced
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent=None):
        """Initialize the Spotify search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setObjectName("spotifySearchPanel")

        # Initialize attributes
        self.result_widgets = []
        self.message_label = None
        self.initial_message = None

        # Initialize spotify client
        self.settings_repo = SettingsRepository()
        self.spotify_client = PlatformFactory.create("spotify", self.settings_repo)

        # Create layout
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Header
        self.header = QLabel("Spotify Search")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.header)

        # Search bar
        self.search_bar = SearchBar(placeholder_text="Search Spotify...")
        self.search_bar.search_confirmed.connect(self._on_search)
        layout.addWidget(self.search_bar)

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
        self.initial_message = QLabel("Enter a search term to find Spotify tracks")
        self.initial_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.initial_message.setStyleSheet("color: #888; margin: 20px 0;")
        self.results_layout.addWidget(self.initial_message)

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

        # Initialize with an empty state
        self.show_message("Enter a search term to find Spotify tracks")

    def _on_search(self, query: str):
        """Handle search query submission.

        Args:
            query: The search query
        """
        if not query.strip():
            self.show_message("Please enter a search term")
            return

        # Clear current results
        self.clear_results()

        # Show loading state
        self.show_message("Searching...")

        # Perform search using the Spotify client
        try:
            if (
                self.spotify_client
                and self.spotify_client.is_authenticated()
                and isinstance(self.spotify_client, SpotifyClient)
            ):
                # Call the raw search_tracks method to get full track data with album images
                results = self.spotify_client.search_tracks(query, limit=10)
                self.display_results(results)
            else:
                self.show_message(
                    "Not connected to Spotify. Please authenticate in the settings panel."
                )
        except Exception as e:
            self.show_message(f"Error searching Spotify: {str(e)}")

    def display_results(self, results):
        """Display search results.

        Args:
            results: List of track objects from Spotify API
        """
        # Clear current results and message
        self.clear_results()

        if not results:
            self.show_message("No results found")
            return

        # Add results to the layout
        for track in results:
            # Convert SpotifyTrack to a properly formatted dict for our UI
            if hasattr(track, "artist_names") and hasattr(track, "album_name"):
                # Create a compatible dict from SpotifyTrack object
                track_data = {
                    "id": track.id,
                    "name": track.name,
                    "uri": track.uri,
                    "artists": [{"name": artist} for artist in track.artist_names],
                    "album": {
                        "name": track.album_name,
                        "id": track.album_id,
                        # We don't have images in the SpotifyTrack object
                        "images": [],
                    },
                    "duration_ms": track.duration_ms,
                    "popularity": track.popularity,
                    "explicit": track.explicit,
                }
            else:
                # Use the track as is (assuming it's already a dict)
                track_data = track

            track_widget = SpotifyTrackItem(track_data)
            track_widget.sync_clicked.connect(self._on_track_sync)
            track_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(track_widget)
            self.result_widgets.append(track_widget)

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

    def clear_results(self):
        """Clear all search results."""
        # Remove the initial message if it exists
        if hasattr(self, "initial_message") and self.initial_message:
            self.initial_message.setParent(None)
            self.initial_message = None

        # Remove any message widget
        if hasattr(self, "message_label") and self.message_label:
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
            if spacer_item and spacer_item.spacerItem():
                self.results_layout.removeItem(spacer_item)

    def show_message(self, message: str):
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

    def _on_track_sync(self, track_data: dict):
        """Handle track sync button click.

        Args:
            track_data: Dictionary with track data
        """
        # Emit signal with track data
        self.track_synced.emit(track_data)

    def _on_track_add(self, track_data: dict):
        """Handle track add button click.

        Args:
            track_data: Dictionary with track data
        """
        # Emit signal with track data
        self.track_added.emit(track_data)
