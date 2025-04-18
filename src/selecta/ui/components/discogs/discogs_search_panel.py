"""Discogs search panel for searching and displaying Discogs releases."""

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
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.utils.type_helpers import column_to_int, has_artist_and_title
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.discogs.discogs_track_item import DiscogsTrackItem
from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.search_bar import SearchBar


class DiscogsSearchPanel(LoadableWidget):
    """Panel for searching and displaying Discogs releases."""

    track_linked = pyqtSignal(dict)  # Emitted when a track is linked
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Discogs search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setObjectName("discogsSearchPanel")

        # Initialize attributes
        self.result_widgets: list[QWidget] = []
        self.message_label: QLabel | None = None
        self.initial_message: QLabel | None = None

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Initialize discogs client
        self.settings_repo = SettingsRepository()
        self.discogs_client = PlatformFactory.create("discogs", self.settings_repo)

        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        main_layout.addWidget(content_widget)

        # Create loading widget (will be added in show_loading)
        loading_widget = self._create_loading_widget("Searching Discogs...")
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
        self.header = QLabel("Discogs Search")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.header)

        # Search bar
        self.search_bar = SearchBar(placeholder_text="Search Discogs...")
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
        self.initial_message = QLabel("Enter a search term to find Discogs releases")
        self.initial_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.initial_message.setStyleSheet("color: #888; margin: 20px 0;")
        self.results_layout.addWidget(self.initial_message)

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

        # Initialize with an empty state
        self.show_message("Enter a search term to find Discogs releases")

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
        can_link = self.selection_state.is_track_selected()

        # Log for debugging
        logger.debug(f"Button state update: can_add={can_add}, can_link={can_link}")

        # Update all result widgets
        for widget in self.result_widgets:
            if isinstance(widget, DiscogsTrackItem):
                widget.update_button_state(can_add=can_add, can_link=can_link)

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
        self.show_loading(f"Searching Discogs for '{query}'...")

        try:
            if (
                self.discogs_client
                and self.discogs_client.is_authenticated()
                and isinstance(self.discogs_client, DiscogsClient)
            ):
                # Run the search in a background thread
                def perform_search() -> list[Any]:
                    return self.discogs_client.search_release(query, limit=10)  # type: ignore

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
                    "Not connected to Discogs. Please authenticate in the settings panel."
                )
        except Exception as e:
            self.hide_loading()
            self.show_message(f"Error searching Discogs: {str(e)}")

    def _handle_search_results(self, results: list[Any]) -> None:
        """Handle the search results from the background thread.

        Args:
            results: Search results from Discogs API
        """
        self.display_results(results)

    def _handle_search_error(self, error_msg: str) -> None:
        """Handle errors from the background thread.

        Args:
            error_msg: Error message
        """
        self.show_message(f"Error searching Discogs: {error_msg}")

    def display_results(self, results: list[Any]) -> None:
        """Display search results.

        Args:
            results: List of DiscogsRelease objects from Discogs API
        """
        # Clear current results and message
        self.clear_results()

        if not results:
            self.show_message("No results found")
            return

        # Add results to the layout
        for release in results:
            # Convert DiscogsRelease to a formatted dict for our UI
            if has_artist_and_title(release):
                # Create a compatible dict from DiscogsRelease object
                release_data: dict[str, Any] = {
                    "id": release.id,
                    "title": release.title,
                    "artist": release.artist,
                    "year": release.year,
                    "label": release.label,
                    "catno": release.catno,
                    "format": release.format,
                    "genre": release.genre,
                    "thumb_url": release.thumb_url,
                    "cover_url": release.cover_url,
                    "uri": release.uri,
                }
            else:
                # Use the release as is (assuming it's already a dict)
                release_data = cast(dict[str, Any], release)

            track_widget = DiscogsTrackItem(release_data)
            track_widget.link_clicked.connect(self._on_track_link)
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

    def _on_track_link(self, release_data: dict[str, Any]) -> None:
        """Handle track link button click.

        Args:
            release_data: Dictionary with release data
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

            # Extract Discogs data from release_data
            discogs_id = release_data.get("id")
            discogs_uri = release_data.get("uri")

            if not discogs_id or not discogs_uri:
                QMessageBox.warning(self, "Link Error", "Invalid Discogs release data")
                return

            # Get cover image URL if available
            cover_url = release_data.get("cover_url")
            thumb_url = release_data.get("thumb_url")
            image_url = cover_url or thumb_url

            # Create platform data dictionary
            platform_data = {
                "release_id": discogs_id,
                "year": release_data.get("year", ""),
                "label": release_data.get("label", ""),
                "catno": release_data.get("catno", ""),
                "format": release_data.get("format", []),
                "genre": release_data.get("genre", []),
                "artwork_url": image_url,
            }

            # Convert to JSON
            platform_data_json = json.dumps(platform_data)

            # Show loading overlay
            self.show_loading("Linking track with Discogs...")

            # Run link operation in background
            def link_task() -> dict[str, Any]:
                # Add platform info to the track
                self.track_repo.add_platform_info(
                    track_id, "discogs", str(discogs_id), discogs_uri, platform_data_json
                )

                # Download and store image if available
                if image_url:
                    try:
                        # Get the image data
                        response = requests.get(image_url, timeout=10)
                        if response.ok:
                            # Store images in database at different sizes
                            self.image_repo.resize_and_store_image(
                                original_data=response.content,
                                track_id=track_id,
                                source="discogs",
                                source_url=image_url,
                            )
                    except Exception as img_err:
                        logger.error(f"Error downloading Discogs image: {img_err}")
                        # Continue even if image download fails

                # Update genres
                if "genre" in platform_data and platform_data["genre"]:
                    try:
                        self.track_repo.set_track_genres(
                            track_id=track_id, genre_names=platform_data["genre"], source="discogs"
                        )
                    except Exception as genre_err:
                        logger.error(f"Error updating genres: {genre_err}")

                return release_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(link_task)

            worker.signals.result.connect(lambda rd: self._handle_link_complete(rd))
            worker.signals.error.connect(lambda err: self._handle_link_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error linking track: {e}")
            QMessageBox.critical(self, "Link Error", f"Error linking track: {str(e)}")

    def _handle_link_complete(self, release_data: dict[str, Any]) -> None:
        """Handle completion of track linking.

        Args:
            release_data: The release data that was linked
        """
        # Emit signal with the linked track
        self.track_linked.emit(release_data)

        # Notify that data has changed
        self.selection_state.notify_data_changed()

        # Show success message
        self.show_message(f"Track linked: {release_data.get('title')}")

        # Wait a moment, then restore the search results
        QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

    def _handle_link_error(self, error_msg: str) -> None:
        """Handle error during track linking.

        Args:
            error_msg: The error message
        """
        logger.error(f"Error linking track: {error_msg}")
        QMessageBox.critical(self, "Link Error", f"Error linking track: {error_msg}")

    def _on_track_add(self, release_data: dict[str, Any]) -> None:
        """Handle track add button click.

        Args:
            release_data: Dictionary with release data
        """
        playlist_id = self.selection_state.get_selected_playlist_id()

        if not playlist_id:
            QMessageBox.warning(
                self, "Add Error", "No playlist selected. Please select a playlist first."
            )
            return

        try:
            # Extract track info
            title = release_data.get("title", "")
            artist = release_data.get("artist", "")

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

            # Get cover image URL if available
            cover_url = release_data.get("cover_url")
            thumb_url = release_data.get("thumb_url")
            image_url = cover_url or thumb_url

            # Show loading overlay
            self.show_loading(f"Adding {artist} - {title} to playlist...")

            # Run add operation in background
            def add_task() -> dict[str, Any]:
                # Create a new track
                new_track_data = {
                    "title": title,
                    "artist": artist,
                    "year": release_data.get("year"),
                    "artwork_url": image_url,  # Keep for backward compatibility
                }

                # Create the track
                track = self.track_repo.create(new_track_data)
                track_id = column_to_int(track.id)

                # Add Discogs platform info
                discogs_id = release_data.get("id")
                discogs_uri = release_data.get("uri")

                if discogs_id and discogs_uri:
                    # Create platform data dictionary
                    platform_data = {
                        "release_id": discogs_id,
                        "year": release_data.get("year", ""),
                        "label": release_data.get("label", ""),
                        "catno": release_data.get("catno", ""),
                        "format": release_data.get("format", []),
                        "genre": release_data.get("genre", []),
                        "artwork_url": image_url,
                    }

                    # Convert to JSON
                    platform_data_json = json.dumps(platform_data)

                    # Add platform info to the track
                    self.track_repo.add_platform_info(
                        track_id,
                        "discogs",
                        str(discogs_id),
                        discogs_uri,
                        platform_data_json,
                    )

                    # Download and store image if available
                    if image_url:
                        try:
                            # Get the image data
                            response = requests.get(image_url, timeout=10)
                            if response.ok:
                                # Store images in database at different sizes
                                self.image_repo.resize_and_store_image(
                                    original_data=response.content,
                                    track_id=track_id,
                                    source="discogs",
                                    source_url=image_url,
                                )
                        except Exception as img_err:
                            logger.error(f"Error downloading Discogs image: {img_err}")
                            # Continue even if image download fails

                    # Add genres
                    if "genre" in platform_data and platform_data["genre"]:
                        try:
                            self.track_repo.set_track_genres(
                                track_id=track_id,
                                genre_names=platform_data["genre"],
                                source="discogs",
                            )
                        except Exception as genre_err:
                            logger.error(f"Error setting genres: {genre_err}")

                # Add track to the playlist
                self.playlist_repo.add_track(playlist_id, track_id)

                return release_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(add_task)

            worker.signals.result.connect(lambda td: self._handle_add_complete(td))
            worker.signals.error.connect(lambda err: self._handle_add_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error adding track: {e}")
            QMessageBox.critical(self, "Add Error", f"Error adding track: {str(e)}")

    def _handle_add_complete(self, release_data: dict[str, Any]) -> None:
        """Handle completion of track add.

        Args:
            release_data: The release data that was added
        """
        # Extract title and artist for display
        title = release_data.get("title", "")
        artist = release_data.get("artist", "")

        # Emit signal with the added track
        self.track_added.emit(release_data)

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
