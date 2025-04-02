"""Spotify search panel for searching and displaying Spotify tracks."""

import json
from typing import Any, cast

from loguru import logger
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import and_

from selecta.core.data.models.db import Track
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.utils.type_helpers import column_to_int, has_artist_names
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

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()

        # Initialize spotify client
        self.settings_repo = SettingsRepository()
        self.spotify_client = PlatformFactory.create("spotify", self.settings_repo)

        # Create layout
        self._setup_ui()

        # Use the shared selection state - import here to avoid circular imports
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()

        # Connect to selection state signals
        self.selection_state.playlist_selected.connect(self._on_global_playlist_selected)
        self.selection_state.track_selected.connect(self._on_global_track_selected)
        self.selection_state.data_changed.connect(self._on_data_changed)

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

    def _on_global_playlist_selected(self, playlist: Any) -> None:
        """Handle playlist selection from the global state.

        Args:
            playlist: The selected playlist
        """
        # Update buttons based on the new selection
        self._update_track_buttons()

    def _on_global_track_selected(self, track: Any) -> None:
        """Handle track selection from the global state.

        Args:
            track: The selected track
        """
        # Update buttons based on the new selection
        self._update_track_buttons()

    def _on_data_changed(self) -> None:
        """Handle notification that the underlying data has changed."""
        # Refresh the current search results if we have a search term
        current_search = self.search_bar.get_search_text()
        if current_search:
            # Re-run the search to refresh results
            self._on_search(current_search)

    def _update_track_buttons(self) -> None:
        """Update all track item buttons based on current selection."""
        # Get button states from the selection state
        can_add = self.selection_state.is_playlist_selected()
        can_sync = self.selection_state.is_track_selected()

        # Log for debugging
        logger.debug(f"Button state update: can_add={can_add}, can_sync={can_sync}")

        # Update all result widgets
        for widget in self.result_widgets:
            if isinstance(widget, SpotifyTrackItem):
                widget.update_button_state(can_add=can_add, can_sync=can_sync)

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
            if has_artist_names(track):
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
                track_data = cast(dict[str, Any], track)

            track_widget = SpotifyTrackItem(track_data)
            track_widget.sync_clicked.connect(self._on_track_sync)
            track_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(track_widget)
            self.result_widgets.append(track_widget)

        # Update button states based on current selection
        self._update_track_buttons()

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

    def clear_results(self):
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
        selected_track = self.selection_state.get_selected_track()

        if not selected_track:
            QMessageBox.warning(
                self, "Sync Error", "No track selected. Please select a track to sync with."
            )
            return

        try:
            # Get track ID from selected track
            track_id = selected_track.track_id

            # Extract Spotify data from track_data
            spotify_id = track_data.get("id")
            spotify_uri = track_data.get("uri")

            if not spotify_id or not spotify_uri:
                QMessageBox.warning(self, "Sync Error", "Invalid Spotify track data")
                return

            # Create platform data dictionary
            platform_data = {
                "popularity": track_data.get("popularity", 0),
                "explicit": track_data.get("explicit", False),
                "preview_url": track_data.get("preview_url", ""),
            }

            # Convert to JSON
            platform_data_json = json.dumps(platform_data)

            # Add platform info to the track
            self.track_repo.add_platform_info(
                track_id, "spotify", spotify_id, spotify_uri, platform_data_json
            )

            # Emit signal with the synchronized track
            self.track_synced.emit(track_data)

            # Notify that data has changed
            self.selection_state.notify_data_changed()

            # Show success message
            self.show_message(f"Track synchronized: {track_data.get('name')}")

            # Wait a moment, then restore the search results
            QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

        except Exception as e:
            logger.exception(f"Error syncing track: {e}")
            QMessageBox.critical(self, "Sync Error", f"Error syncing track: {str(e)}")

    def _on_track_add(self, track_data: dict):
        """Handle track add button click.

        Args:
            track_data: Dictionary with track data
        """
        playlist_id = self.selection_state.get_selected_playlist_id()

        if not playlist_id:
            QMessageBox.warning(
                self, "Add Error", "No playlist selected. Please select a playlist first."
            )
            return

        try:
            # Extract track info
            title = track_data.get("name", "")
            artists = track_data.get("artists", [])
            artist = ", ".join([a.get("name", "") for a in artists])

            if not title or not artist:
                QMessageBox.warning(
                    self, "Add Error", "Missing track information (title or artist)"
                )
                return

            # Check if a track with the same title and artist already exists
            existing_track = (
                self.track_repo.session.query(Track)
                .filter(and_(Track.title == title, Track.artist == artist))
                .first()
            )

            if existing_track:
                QMessageBox.warning(self, "Add Error", f"Track already exists: {artist} - {title}")
                return

            # Get duration
            duration_ms = track_data.get("duration_ms")

            # Create a new track
            new_track_data = {
                "title": title,
                "artist": artist,
                "duration_ms": duration_ms,
            }

            # Create the track
            track = self.track_repo.create(new_track_data)

            # Add Spotify platform info
            spotify_id = track_data.get("id")
            spotify_uri = track_data.get("uri")

            if spotify_id and spotify_uri:
                # Create platform data dictionary
                platform_data = {
                    "popularity": track_data.get("popularity", 0),
                    "explicit": track_data.get("explicit", False),
                    "preview_url": track_data.get("preview_url", ""),
                }

                # Convert to JSON
                platform_data_json = json.dumps(platform_data)

                # Add platform info to the track
                self.track_repo.add_platform_info(
                    column_to_int(track.id), "spotify", spotify_id, spotify_uri, platform_data_json
                )

            # Add track to the playlist
            self.playlist_repo.add_track(playlist_id, column_to_int(track.id))

            # Emit signal with the added track
            self.track_added.emit(track_data)

            # Notify that data has changed
            self.selection_state.notify_data_changed()

            # Show success message
            self.show_message(f"Track added: {artist} - {title}")

            # Wait a moment, then restore the search results
            QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

        except Exception as e:
            logger.exception(f"Error adding track: {e}")
            QMessageBox.critical(self, "Add Error", f"Error adding track: {str(e)}")
