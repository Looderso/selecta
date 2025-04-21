"""YouTube search panel for the UI."""

import json
from typing import Any, cast

import requests
from loguru import logger
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton

from selecta.core.data.repositories.image_repository import ImageRepository
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.utils.type_helpers import column_to_int
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.search.base_search_panel import BaseSearchPanel
from selecta.ui.components.search.platform.youtube.youtube_video_item import YouTubeVideoItem


class YouTubeSearchPanel(BaseSearchPanel):
    """Panel for searching and displaying YouTube videos."""

    def __init__(self, parent=None) -> None:
        """Initialize the YouTube search panel.

        Args:
            parent: Parent widget
        """
        # Initialize the base search panel first
        super().__init__(parent)

        # Initialize YouTube client
        settings_repo = SettingsRepository()
        self.youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube", settings_repo))

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Store search results
        self.search_results: list[dict[str, Any]] = []

        # Update authentication status
        self._update_auth_status()

    def get_platform_name(self) -> str:
        """Get the platform name.

        Returns:
            Platform name
        """
        return "YouTube"

    def _setup_platform_ui(self) -> None:
        """Set up platform-specific UI elements."""
        # Add platform-specific UI here
        pass

    def _setup_header_content(self, header_layout: QHBoxLayout) -> None:
        """Set up YouTube-specific header content.

        Args:
            header_layout: Layout to add header content to
        """
        # Add the auth button
        self.auth_button = QPushButton("Connect")
        self.auth_button.setToolTip("Connect to YouTube")
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

        if self.youtube_client and self.youtube_client.is_authenticated():
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #22AA22; font-style: italic; margin-left: 10px;")
            self.auth_button.setText("Reconnect")
            self.auth_button.setToolTip("Reconnect to YouTube")
        else:
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("color: #888; font-style: italic; margin-left: 10px;")
            self.auth_button.setText("Connect")
            self.auth_button.setToolTip("Connect to YouTube to search videos")

    def _authenticate(self) -> None:
        """Authenticate with YouTube."""
        if not self.youtube_client:
            settings_repo = SettingsRepository()
            self.youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube", settings_repo))
            if not self.youtube_client:
                QMessageBox.critical(self, "Error", "Failed to create YouTube client")
                return

        try:
            # Show loading widget during authentication
            self.show_loading("Connecting to YouTube...")

            # Process events to ensure loading widget is displayed
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

            # Authenticate
            result = self.youtube_client.authenticate()

            # Hide loading widget
            self.hide_loading()

            if result:
                QMessageBox.information(self, "Authentication Successful", "Successfully connected to YouTube!")
                self._update_auth_status()
            else:
                QMessageBox.warning(self, "Authentication Failed", "Failed to connect to YouTube. Please try again.")
        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error authenticating with YouTube: {e}")
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
        if not self.youtube_client or not self.youtube_client.is_authenticated():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to YouTube first using the 'Connect' button.",
            )
            return

        # Clear current results
        self.clear_results()

        # Show loading state
        self.show_loading(f"Searching YouTube for '{query}'...")

        try:
            # Run the search in a background thread
            def perform_search() -> list[Any]:
                return self.youtube_client.search_tracks(query, limit=20)

            # Create a worker and connect signals
            thread_manager = ThreadManager()
            worker = thread_manager.run_task(perform_search)

            # Handle the results
            worker.signals.result.connect(lambda results: self._handle_search_results(results))
            worker.signals.error.connect(lambda error_msg: self._handle_search_error(error_msg))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error searching YouTube: {e}")
            self.show_message(f"Error searching YouTube: {str(e)}")

    def _handle_search_results(self, results: list[dict[str, Any]]) -> None:
        """Handle the search results from the background thread.

        Args:
            results: Search results from YouTube API
        """
        # Save the results
        self.search_results = results

        # Display the results
        self.display_results(results)

    def _handle_search_error(self, error_msg: str) -> None:
        """Handle errors from the background thread.

        Args:
            error_msg: Error message
        """
        self.show_message(f"Error searching YouTube: {error_msg}")

    def display_results(self, results: list[dict[str, Any]]) -> None:
        """Display search results.

        Args:
            results: List of video objects from YouTube API
        """
        # Clear current results and message
        self.clear_results()

        if not results:
            self.show_message("No results found")
            return

        # Add results to the layout
        for video in results:
            video_widget = YouTubeVideoItem(video)
            video_widget.link_clicked.connect(self._on_track_link)
            video_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(video_widget)
            self.result_widgets.append(video_widget)

        # Update button states based on current selection
        self._update_result_buttons()

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

    def _on_track_link(self, video_data: dict[str, Any]) -> None:
        """Handle track link button click.

        Args:
            video_data: Dictionary with video data
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

            # Extract YouTube data from video_data
            snippet = video_data.get("snippet", {})
            video_id = video_data.get("id", {}).get("videoId", "")

            if not video_id:
                QMessageBox.warning(self, "Link Error", "Invalid YouTube video data")
                return

            # Get video URL
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Get thumbnail URL if available
            thumbnail_url = None
            if "thumbnails" in snippet:
                thumbnails = snippet["thumbnails"]
                for size in ["high", "medium", "default"]:
                    if size in thumbnails and "url" in thumbnails[size]:
                        thumbnail_url = thumbnails[size]["url"]
                        break

            # Create platform data dictionary
            platform_data = {
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "thumbnail_url": thumbnail_url,
            }

            # Get duration if available
            if "contentDetails" in video_data and "duration" in video_data["contentDetails"]:
                from selecta.core.platform.youtube.models import _parse_iso8601_duration

                duration_str = video_data["contentDetails"]["duration"]
                duration_seconds = _parse_iso8601_duration(duration_str) or 0
                platform_data["duration_seconds"] = duration_seconds

            # Convert to JSON
            platform_data_json = json.dumps(platform_data)

            # Show loading overlay
            self.show_loading("Linking track with YouTube...")

            # Run link operation in background
            def link_task() -> dict[str, Any]:
                # Add platform info to the track
                self.track_repo.add_platform_info(track_id, "youtube", video_id, video_url, platform_data_json)

                # Download and store thumbnail if available
                if thumbnail_url:
                    try:
                        # Get the image data
                        response = requests.get(thumbnail_url, timeout=10)
                        if response.ok:
                            # Store images in database at different sizes
                            self.image_repo.resize_and_store_image(
                                original_data=response.content,
                                track_id=track_id,
                                source="youtube",
                                source_url=thumbnail_url,
                            )
                    except Exception as img_err:
                        logger.error(f"Error downloading YouTube thumbnail: {img_err}")
                        # Continue even if image download fails

                return video_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(link_task)

            # Connect signals for completion and error handling
            worker.signals.result.connect(
                lambda result: self._handle_link_complete(result, snippet.get("title", "YouTube Video"))
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

    def _on_track_add(self, video_data: dict[str, Any]) -> None:
        """Handle track add button click.

        Args:
            video_data: Dictionary with video data
        """
        playlist_id = self.selection_state.get_selected_playlist_id()

        if not playlist_id:
            QMessageBox.warning(self, "Add Error", "No playlist selected. Please select a playlist first.")
            return

        try:
            # Extract video info
            snippet = video_data.get("snippet", {})
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            video_id = video_data.get("id", {}).get("videoId", "")

            if not video_id or not title:
                QMessageBox.warning(self, "Add Error", "Missing video information (title or ID)")
                return

            # Get video URL
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Get thumbnail URL if available
            thumbnail_url = None
            if "thumbnails" in snippet:
                thumbnails = snippet["thumbnails"]
                for size in ["high", "medium", "default"]:
                    if size in thumbnails and "url" in thumbnails[size]:
                        thumbnail_url = thumbnails[size]["url"]
                        break

            # Get duration if available
            duration_seconds = 0
            if "contentDetails" in video_data and "duration" in video_data["contentDetails"]:
                from selecta.core.platform.youtube.models import _parse_iso8601_duration

                duration_str = video_data["contentDetails"]["duration"]
                duration_seconds = _parse_iso8601_duration(duration_str) or 0

            # Show loading overlay
            self.show_loading(f"Adding {title} to playlist...")

            # Run add operation in background
            def add_task() -> dict[str, Any]:
                # Create a new track
                new_track_data = {
                    "title": title,
                    "artist": channel,  # Use channel as artist
                    # Convert seconds to milliseconds for the database
                    "duration_ms": duration_seconds * 1000 if duration_seconds else None,
                }

                # Create the track
                track = self.track_repo.create(new_track_data)
                track_id = column_to_int(track.id)

                # Add YouTube platform info
                if video_id:
                    # Create platform data dictionary
                    platform_data = {
                        "title": title,
                        "channel": channel,
                        "thumbnail_url": thumbnail_url,
                        "duration_seconds": duration_seconds,
                    }

                    # Convert to JSON
                    platform_data_json = json.dumps(platform_data)

                    # Add platform info to the track
                    self.track_repo.add_platform_info(
                        track_id,
                        "youtube",
                        video_id,
                        video_url,
                        platform_data_json,
                    )

                    # Download and store thumbnail if available
                    if thumbnail_url:
                        try:
                            # Get the image data
                            response = requests.get(thumbnail_url, timeout=10)
                            if response.ok:
                                # Store images in database at different sizes
                                self.image_repo.resize_and_store_image(
                                    original_data=response.content,
                                    track_id=track_id,
                                    source="youtube",
                                    source_url=thumbnail_url,
                                )
                        except Exception as img_err:
                            logger.error(f"Error downloading YouTube thumbnail: {img_err}")
                            # Continue even if image download fails

                # Add track to the playlist
                self.playlist_repo.add_track(playlist_id, track_id)

                return video_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(add_task)

            # Connect signals for completion and error handling
            worker.signals.result.connect(
                lambda result: self._handle_add_complete(result, snippet.get("title", "YouTube Video"))
            )
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
