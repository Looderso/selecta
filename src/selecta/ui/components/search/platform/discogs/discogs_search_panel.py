"""Discogs search panel for searching and displaying Discogs releases."""

import json
from typing import Any, cast

import requests
from loguru import logger
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton

from selecta.core.data.repositories.image_repository import ImageRepository
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.utils.type_helpers import column_to_int, has_artist_and_title
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.search.base_search_panel import BaseSearchPanel
from selecta.ui.components.search.platform.discogs.discogs_release_item import DiscogsReleaseItem


class DiscogsSearchPanel(BaseSearchPanel):
    """Panel for searching and displaying Discogs releases."""

    def __init__(self, parent=None) -> None:
        """Initialize the Discogs search panel.

        Args:
            parent: Parent widget
        """
        # Initialize the base search panel first
        super().__init__(parent)

        # Initialize Discogs client
        settings_repo = SettingsRepository()
        self.discogs_client = PlatformFactory.create("discogs", settings_repo)

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Update authentication status
        self._update_auth_status()

    def get_platform_name(self) -> str:
        """Get the platform name.

        Returns:
            Platform name
        """
        return "Discogs"

    def _setup_platform_ui(self) -> None:
        """Set up platform-specific UI elements."""
        # Add platform-specific UI here
        pass

    def _setup_header_content(self, header_layout: QHBoxLayout) -> None:
        """Set up Discogs-specific header content.

        Args:
            header_layout: Layout to add header content to
        """
        # Add the auth button
        self.auth_button = QPushButton("Connect")
        self.auth_button.setToolTip("Connect to Discogs")
        self.auth_button.clicked.connect(self._authenticate)
        header_layout.addWidget(self.auth_button)

        # Add status label
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #888; font-style: italic; margin-left: 10px;")
        header_layout.addWidget(self.status_label)

    def _update_auth_status(self) -> None:
        """Update the authentication status display."""
        # Check if UI has been initialized
        if not hasattr(self, "status_label") or not hasattr(self, "auth_button"):
            return

        if self.discogs_client and self.discogs_client.is_authenticated():
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #22AA22; font-style: italic; margin-left: 10px;")
            self.auth_button.setText("Reconnect")
            self.auth_button.setToolTip("Reconnect to Discogs")
        else:
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("color: #888; font-style: italic; margin-left: 10px;")
            self.auth_button.setText("Connect")
            self.auth_button.setToolTip("Connect to Discogs to search releases")

    def _authenticate(self) -> None:
        """Authenticate with Discogs."""
        if not self.discogs_client:
            settings_repo = SettingsRepository()
            self.discogs_client = PlatformFactory.create("discogs", settings_repo)
            if not self.discogs_client:
                QMessageBox.critical(self, "Error", "Failed to create Discogs client")
                return

        try:
            # Show loading widget during authentication
            self.show_loading("Connecting to Discogs...")

            # Process events to ensure loading widget is displayed
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

            # Authenticate
            result = self.discogs_client.authenticate()

            # Hide loading widget
            self.hide_loading()

            if result:
                QMessageBox.information(self, "Authentication Successful", "Successfully connected to Discogs!")
                self._update_auth_status()
            else:
                QMessageBox.warning(self, "Authentication Failed", "Failed to connect to Discogs. Please try again.")
        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error authenticating with Discogs: {e}")
            QMessageBox.critical(self, "Authentication Error", f"Error: {str(e)}")

    def _on_search(self, query: str) -> None:
        """Handle search query submission.

        Args:
            query: The search query
        """
        if not query.strip():
            self.show_message("Please enter a search term")
            return

        # Check authentication
        if not self.discogs_client or not self.discogs_client.is_authenticated():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to Discogs first using the 'Connect' button.",
            )
            return

        # Clear current results
        self.clear_results()

        # Show loading state
        self.show_loading(f"Searching Discogs for '{query}'...")

        try:
            # Run the search in a background thread
            def perform_search() -> list[Any]:
                if isinstance(self.discogs_client, DiscogsClient):
                    return self.discogs_client.search_release(query=query, limit=20)
                return []

            # Create a worker and connect signals
            thread_manager = ThreadManager()
            worker = thread_manager.run_task(perform_search)

            # Handle the results
            worker.signals.result.connect(lambda results: self._handle_search_results(results))
            worker.signals.error.connect(lambda error_msg: self._handle_search_error(error_msg))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error searching Discogs: {e}")
            self.show_message(f"Error searching Discogs: {str(e)}")

    def _handle_search_results(self, results: list[Any]) -> None:
        """Handle the search results from the background thread.

        Args:
            results: Search results from Discogs API
        """
        # Display the results
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

            release_widget = DiscogsReleaseItem(release_data)
            release_widget.link_clicked.connect(self._on_track_link)
            release_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(release_widget)
            self.result_widgets.append(release_widget)

        # Update button states based on current selection
        self._update_result_buttons()

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

    def _on_track_link(self, release_data: dict[str, Any]) -> None:
        """Handle track link button click.

        Args:
            release_data: Dictionary with release data
        """
        selected_track = self.selection_state.get_selected_track()

        if not selected_track:
            QMessageBox.warning(self, "Link Error", "No track selected. Please select a track to link with.")
            return

        try:
            # Get track ID from selected track
            if not hasattr(selected_track, "track_id"):
                QMessageBox.warning(self, "Link Error", "Invalid track selection. Missing track ID.")
                return

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
                self.track_repo.add_platform_info(track_id, "discogs", str(discogs_id), discogs_uri, platform_data_json)

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

            # Connect signals for completion and error handling
            worker.signals.result.connect(
                lambda result: self._handle_link_complete(result, release_data.get("title", "Discogs Release"))
            )
            worker.signals.error.connect(lambda err: self._handle_link_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error linking track: {e}")
            QMessageBox.critical(self, "Link Error", f"Error linking track: {str(e)}")

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
            QMessageBox.warning(self, "Add Error", "No playlist selected. Please select a playlist first.")
            return

        try:
            # Extract track info
            title = release_data.get("title", "")
            artist = release_data.get("artist", "")

            if not title or not artist:
                QMessageBox.warning(self, "Add Error", "Missing track information (title or artist)")
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

            # Connect signals for completion and error handling
            display_name = f"{artist} - {title}"
            worker.signals.result.connect(lambda result: self._handle_add_complete(result, display_name))
            worker.signals.error.connect(lambda err: self._handle_add_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error adding track: {e}")
            QMessageBox.critical(self, "Add Error", f"Error adding track: {str(e)}")

    def _handle_add_error(self, error_msg: str) -> None:
        """Handle error during track add.

        Args:
            error_msg: The error message
        """
        logger.error(f"Error adding track: {error_msg}")
        QMessageBox.critical(self, "Add Error", f"Error adding track: {error_msg}")
