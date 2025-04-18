"""Spotify search panel for searching and displaying Spotify tracks."""

import json
from typing import Any, cast

import requests
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
from selecta.core.data.repositories.image_repository import ImageRepository
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.utils.type_helpers import column_to_int, has_artist_names
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.search_bar import SearchBar
from selecta.ui.components.spotify.spotify_track_item import SpotifyTrackItem


class SpotifySearchPanel(LoadableWidget):
    """Panel for searching and displaying Spotify tracks."""

    track_linked = pyqtSignal(dict)  # Emitted when a track is linked
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Spotify search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setObjectName("spotifySearchPanel")

        # Initialize attributes
        self.result_widgets: list[QWidget] = []
        self.message_label: QLabel | None = None
        self.initial_message: QLabel | None = None

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Initialize spotify client
        self.settings_repo = SettingsRepository()
        self.spotify_client = PlatformFactory.create("spotify", self.settings_repo)

        # Initialize loading widget
        loading_widget = self._create_loading_widget("Searching Spotify...")

        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        main_layout.addWidget(content_widget)

        # Create loading widget (will be added in show_loading)
        loading_widget = self._create_loading_widget("Searching Spotify...")
        main_layout.addWidget(loading_widget)
        loading_widget.setVisible(False)

        # Setup the UI in the content widget
        self._setup_ui(content_widget)

        # Use the shared selection state - import here to avoid circular imports
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()

        # Connect to selection state signals
        self.selection_state.playlist_selected.connect(self._on_global_playlist_selected)
        self.selection_state.track_selected.connect(self._on_global_track_selected)
        self.selection_state.data_changed.connect(self._on_data_changed)

    def _setup_ui(self, content_widget: QWidget) -> None:
        """Set up the UI components.

        Args:
            content_widget: The widget to add UI components to
        """
        layout = QVBoxLayout(content_widget)
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

    def search(self, query: str) -> None:
        """Public method to perform a search.

        Args:
            query: The search query
        """
        self.search_bar.set_search_text(query)
        self._on_search(query)

    def _on_search(self, query: str) -> None:
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
        self.show_loading(f"Searching Spotify for '{query}'...")

        try:
            if (
                self.spotify_client
                and self.spotify_client.is_authenticated()
                and isinstance(self.spotify_client, SpotifyClient)
            ):
                # Run the search in a background thread
                def perform_search() -> list[Any]:
                    return self.spotify_client.search_tracks(query, limit=10)  # type: ignore

                # Create a worker and connect signals
                thread_manager = ThreadManager()
                worker = thread_manager.run_task(perform_search)

                # Handle the results
                worker.signals.result.connect(lambda results: self._handle_search_results(results))
                worker.signals.error.connect(lambda error_msg: self._handle_search_error(error_msg))
                worker.signals.finished.connect(lambda: self.hide_loading())

            else:
                self.hide_loading()
                self.show_message(
                    "Not connected to Spotify. Please authenticate in the settings panel."
                )
        except Exception as e:
            self.hide_loading()
            self.show_message(f"Error searching Spotify: {str(e)}")

    def _handle_search_results(self, results: list[Any]) -> None:
        """Handle the search results from the background thread.

        Args:
            results: Search results from Spotify API
        """
        self.display_results(results)

    def _handle_search_error(self, error_msg: str) -> None:
        """Handle errors from the background thread.

        Args:
            error_msg: Error message
        """
        self.show_message(f"Error searching Spotify: {error_msg}")

    def display_results(self, results: list[Any]) -> None:
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
                track_data: dict[str, Any] = {
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
            track_widget.sync_clicked.connect(self._on_track_link)
            track_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(track_widget)
            self.result_widgets.append(track_widget)

        # Update button states based on current selection
        self._update_track_buttons()

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

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
            if spacer_item and spacer_item.spacerItem():
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

    def _on_track_link(self, track_data: dict[str, Any]) -> None:
        """Handle track link button click.

        Args:
            track_data: Dictionary with track data
        """
        selected_track = self.selection_state.get_selected_track()

        if not selected_track:
            QMessageBox.warning(
                self, "Link Error", "No track selected. Please select a track to link with."
            )
            return

        try:
            # Get track ID from selected track
            track_id = selected_track.track_id

            # Extract Spotify data from track_data
            spotify_id = track_data.get("id")
            spotify_uri = track_data.get("uri")

            if not spotify_id or not spotify_uri:
                QMessageBox.warning(self, "Link Error", "Invalid Spotify track data")
                return

            # Get album image URLs if available
            album_image_url = None
            if "album" in track_data and "images" in track_data["album"]:
                images = track_data["album"]["images"]
                if images:
                    # Find largest image for best quality when resizing
                    sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
                    if sorted_images:
                        album_image_url = sorted_images[0].get("url")

            # Create platform data dictionary
            platform_data = {
                "popularity": track_data.get("popularity", 0),
                "explicit": track_data.get("explicit", False),
                "preview_url": track_data.get("preview_url", ""),
                "artwork_url": album_image_url,  # Store the URL for future reference
            }

            # Convert to JSON
            platform_data_json = json.dumps(platform_data)

            # Show loading overlay
            self.show_loading("Linking track with Spotify...")

            # Run link in background
            def link_task() -> dict[str, Any]:
                try:
                    # Add platform info using the repository
                    self.track_repo.add_platform_info(
                        track_id=track_id,
                        platform="spotify",
                        platform_id=spotify_id,
                        uri=spotify_uri,
                        metadata=platform_data_json,
                    )

                    # Download and store images if available
                    if album_image_url:
                        try:
                            # Get the image data
                            response = requests.get(album_image_url, timeout=10)
                            if response.ok:
                                # Store images in database at different sizes
                                self.image_repo.resize_and_store_image(
                                    original_data=response.content,
                                    track_id=track_id,
                                    source="spotify",
                                    source_url=album_image_url,
                                )
                        except Exception as img_err:
                            logger.error(f"Error downloading album image: {img_err}")
                            # Continue even if image download fails

                except Exception as e:
                    logger.error(f"Error in link_task: {e}")
                    raise

                return track_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(link_task)

            worker.signals.result.connect(lambda td: self._handle_link_complete(td))
            worker.signals.error.connect(lambda err: self._handle_link_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error linking track: {e}")
            QMessageBox.critical(self, "Link Error", f"Error linking track: {str(e)}")

    def _handle_link_complete(self, track_data: dict[str, Any]) -> None:
        """Handle completion of track linking.

        Args:
            track_data: The track data that was linked
        """
        # Emit signal with the linked track
        self.track_linked.emit(track_data)

        # Notify that data has changed
        self.selection_state.notify_data_changed()

        # Show success message
        self.show_message(f"Track linked: {track_data.get('name')}")

        # Wait a moment, then restore the search results
        QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

    def _handle_link_error(self, error_msg: str) -> None:
        """Handle error during track linking.

        Args:
            error_msg: The error message
        """
        logger.error(f"Error linking track: {error_msg}")
        QMessageBox.critical(self, "Link Error", f"Error linking track: {error_msg}")

    def _on_track_add(self, track_data: dict[str, Any]) -> None:
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
            # This check should be quick so we'll keep it in the UI thread
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

            # Get album image URLs if available
            album_image_url = None
            if "album" in track_data and "images" in track_data["album"]:
                images = track_data["album"]["images"]
                if images:
                    # Find largest image for best quality when resizing
                    sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
                    if sorted_images:
                        album_image_url = sorted_images[0].get("url")

            # Show loading overlay
            self.show_loading(f"Adding {artist} - {title} to playlist...")

            # Run add in background
            def add_task() -> dict[str, Any]:
                # Create a new track
                new_track_data = {
                    "title": title,
                    "artist": artist,
                    "duration_ms": duration_ms,
                    "year": track_data.get("album", {}).get("release_date", "")[:4]
                    if track_data.get("album", {}).get("release_date", "")
                    else None,
                    "artwork_url": album_image_url,  # Store URL for backward compatibility
                }

                # Create the track
                track = self.track_repo.create(new_track_data)
                track_id = column_to_int(track.id)

                # Add Spotify platform info
                spotify_id = track_data.get("id")
                spotify_uri = track_data.get("uri")

                if spotify_id and spotify_uri:
                    # Create platform data dictionary
                    platform_data = {
                        "popularity": track_data.get("popularity", 0),
                        "explicit": track_data.get("explicit", False),
                        "preview_url": track_data.get("preview_url", ""),
                        "artwork_url": album_image_url,
                        "album_type": track_data.get("album", {}).get("album_type"),
                        "release_date": track_data.get("album", {}).get("release_date"),
                    }

                    # Convert to JSON
                    platform_data_json = json.dumps(platform_data)

                    # Add platform info using repository
                    self.track_repo.add_platform_info(
                        track_id=track_id,
                        platform="spotify",
                        platform_id=spotify_id,
                        uri=spotify_uri,
                        metadata=platform_data_json,
                    )

                    # Download and store images if available
                    if album_image_url:
                        try:
                            # Get the image data
                            response = requests.get(album_image_url, timeout=10)
                            if response.ok:
                                # Store images in database at different sizes
                                self.image_repo.resize_and_store_image(
                                    original_data=response.content,
                                    track_id=track_id,
                                    source="spotify",
                                    source_url=album_image_url,
                                )
                        except Exception as img_err:
                            logger.error(f"Error downloading album image: {img_err}")
                            # Continue even if image download fails

                # Add track to the playlist
                self.playlist_repo.add_track(playlist_id, track_id)

                return track_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(add_task)

            worker.signals.result.connect(lambda td: self._handle_add_complete(td))
            worker.signals.error.connect(lambda err: self._handle_add_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error adding track: {e}")
            QMessageBox.critical(self, "Add Error", f"Error adding track: {str(e)}")

    def _handle_add_complete(self, track_data: dict[str, Any]) -> None:
        """Handle completion of track add.

        Args:
            track_data: The track data that was added
        """
        # Extract title and artist for display
        title = track_data.get("name", "")
        artists = track_data.get("artists", [])
        artist = ", ".join([a.get("name", "") for a in artists]) if artists else ""

        # Emit signal with the added track
        self.track_added.emit(track_data)

        # Notify that data has changed
        self.selection_state.notify_data_changed()

        # Show success message
        self.show_message(f"Track added: {artist} - {title}")

        # Wait a moment, then restore the search results
        QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

    def _handle_add_error(self, error_msg: str) -> None:
        """Handle error during track add.

        Args:
            error_msg: The error message
        """
        logger.error(f"Error adding track: {error_msg}")
        QMessageBox.critical(self, "Add Error", f"Error adding track: {error_msg}")
