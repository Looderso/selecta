"""YouTube search panel for the UI."""

import json
from typing import Any, cast

import requests
from loguru import logger
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.utils.type_helpers import column_to_int
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.platform_search_panel import PlatformSearchPanel
from selecta.ui.components.search_bar import SearchBar


class YouTubeVideoItem(QWidget):
    """Widget to display a single YouTube video search result."""

    link_clicked = pyqtSignal(dict)  # Emits video data on link button click
    add_clicked = pyqtSignal(dict)  # Emits video data on add button click

    def __init__(self, video_data: dict, parent=None):
        """Initialize the YouTube video item.

        Args:
            video_data: Dictionary with video data from YouTube API
            parent: Parent widget
        """
        super().__init__(parent)
        self.video_data = video_data
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("youtubeVideoItem")
        self.setMouseTracking(True)  # Enable mouse tracking for hover events

        # Track hover state
        self.is_hovered = False

        # Track button state
        self._can_add = False
        self._can_link = False

        # Apply styling
        self.setStyleSheet("""
            #youtubeVideoItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #youtubeVideoItem:hover {
                background-color: #333333;
            }
            #videoTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #channelName {
                font-size: 12px;
                color: #B3B3B3;
            }
            #videoDuration {
                font-size: 11px;
                color: #999999;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #FFFFFF;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(51, 51, 51, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(51, 51, 51, 0.5);
            }
            QPushButton:disabled {
                border-color: #555;
                color: #555;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Extract video info
        snippet = self.video_data.get("snippet", {})
        title = snippet.get("title", "Unknown Title")
        channel = snippet.get("channelTitle", "Unknown Channel")

        # Get duration if available
        duration_str = ""
        if "contentDetails" in self.video_data and "duration" in self.video_data["contentDetails"]:
            from selecta.core.platform.youtube.models import _parse_iso8601_duration

            duration_seconds = _parse_iso8601_duration(
                self.video_data["contentDetails"]["duration"]
            )
            if duration_seconds:
                minutes, seconds = divmod(duration_seconds, 60)
                duration_str = f"{minutes}:{seconds:02d}"

        # Thumbnail image
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(54, 54)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setStyleSheet("border-radius: 4px;")

        # Set placeholder thumbnail
        from PyQt6.QtGui import QPixmap

        placeholder = QPixmap(54, 54)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.thumbnail_label.setPixmap(placeholder)

        # Load thumbnail if available
        thumbnail_url = None
        if "thumbnails" in snippet:
            thumbnails = snippet["thumbnails"]
            for size in ["high", "medium", "default"]:
                if size in thumbnails and "url" in thumbnails[size]:
                    thumbnail_url = thumbnails[size]["url"]
                    break

        if thumbnail_url:
            self.thumbnail_label.setProperty("imageUrl", thumbnail_url)
            # We'll implement image loading later
            # For now, just set the placeholder

        layout.addWidget(self.thumbnail_label)

        # Video info (title, channel, duration)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Video title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("videoTitle")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        # Channel name
        self.channel_label = QLabel(channel)
        self.channel_label.setObjectName("channelName")
        info_layout.addWidget(self.channel_label)

        # Duration
        if duration_str:
            self.duration_label = QLabel(f"Duration: {duration_str}")
            self.duration_label.setObjectName("videoDuration")
            info_layout.addWidget(self.duration_label)

        layout.addLayout(info_layout, 1)  # 1 = stretch factor

        # Buttons layout
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setSpacing(6)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Link button
        self.link_button = QPushButton("Link")
        self.link_button.setFixedSize(60, 25)
        self.link_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_button.clicked.connect(self._on_link_clicked)
        # Initially disabled until a track is selected
        self.link_button.setEnabled(False)
        self.buttons_layout.addWidget(self.link_button)

        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.setFixedSize(60, 25)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self._on_add_clicked)
        # Initially disabled until a playlist is selected
        self.add_button.setEnabled(False)
        self.buttons_layout.addWidget(self.add_button)

        # Add the buttons layout to the main layout
        layout.addLayout(self.buttons_layout)

        # Hide buttons initially
        self.link_button.setVisible(False)
        self.add_button.setVisible(False)

    def update_button_state(self, can_add: bool = False, can_link: bool = False) -> None:
        """Update the state of the buttons based on current selection.

        Args:
            can_add: Whether the add button should be enabled
            can_link: Whether the link button should be enabled
        """
        # Store the button states
        self._can_add = can_add
        self._can_link = can_link

        # Update button states
        self.add_button.setEnabled(can_add)
        self.link_button.setEnabled(can_link)

        # Only show buttons if we're hovered and set appropriate state
        self._update_button_visibility()

    def _on_link_clicked(self):
        """Handle link button click."""
        self.link_clicked.emit(self.video_data)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.add_clicked.emit(self.video_data)

    def enterEvent(self, event):
        """Handle mouse enter events to show buttons.

        Args:
            event: The enter event
        """
        self.is_hovered = True
        self._update_button_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events to hide buttons.

        Args:
            event: The leave event
        """
        self.is_hovered = False
        self._update_button_visibility()
        super().leaveEvent(event)

    def _update_button_visibility(self):
        """Update the visibility of the buttons based on hover state."""
        if self.is_hovered:
            # When hovering, show both buttons
            self.link_button.setVisible(True)
            self.add_button.setVisible(True)

            # Make sure the enabled state is correct
            self.link_button.setEnabled(self._can_link)
            self.add_button.setEnabled(self._can_add)
        else:
            # When not hovering, hide both buttons
            self.link_button.setVisible(False)
            self.add_button.setVisible(False)


class YouTubeSearchPanel(PlatformSearchPanel):
    """Panel for searching and displaying YouTube videos."""

    track_linked = pyqtSignal(dict)  # Emitted when a track is linked
    track_added = pyqtSignal(dict)  # Emitted when a track is added

    def __init__(self, parent=None):
        """Initialize the YouTube search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setObjectName("youtubeSearchPanel")

        # Initialize attributes
        self.result_widgets = []
        self.message_label = None
        self.initial_message = None
        self.search_results = []

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Initialize YouTube client
        self.settings_repo = SettingsRepository()
        self.youtube_client = cast(
            YouTubeClient, PlatformFactory.create("youtube", self.settings_repo)
        )

        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        main_layout.addWidget(content_widget)

        # Create loading widget (will be added in show_loading)
        loading_widget = self._create_loading_widget("Searching YouTube...")
        main_layout.addWidget(loading_widget)
        loading_widget.setVisible(False)

        # Setup the UI in the content widget
        self._setup_ui(content_widget)

        # SelectionState is already initialized in the parent class

    def _setup_ui(self, content_widget: QWidget) -> None:
        """Set up the UI components.

        Args:
            content_widget: The widget to add UI components to
        """
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Header section with status and auth button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Header
        self.header = QLabel("YouTube Search")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.header)

        # Auth button
        self.auth_button = QPushButton("Connect to YouTube")
        self.auth_button.clicked.connect(self._authenticate)
        header_layout.addWidget(self.auth_button)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Status label
        self.status_label = QLabel("Not connected to YouTube")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)

        # Search bar
        self.search_bar = SearchBar(placeholder_text="Search YouTube...")
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
        self.initial_message = QLabel("Enter a search term to find YouTube videos")
        self.initial_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.initial_message.setStyleSheet("color: #888; margin: 20px 0;")
        self.results_layout.addWidget(self.initial_message)

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

        # Initialize with an empty state
        self.show_message("Enter a search term to find YouTube videos")

        # Update the auth status
        self._update_auth_status()

    def _update_auth_status(self):
        """Update the authentication status display."""
        if self.youtube_client and self.youtube_client.is_authenticated():
            self.status_label.setText("Connected to YouTube")
            self.auth_button.setText("Reconnect")
            self.auth_button.setToolTip("Reconnect to YouTube")
        else:
            self.status_label.setText("Not connected to YouTube")
            self.auth_button.setText("Connect to YouTube")
            self.auth_button.setToolTip("Connect to YouTube to search videos")

    def _authenticate(self):
        """Authenticate with YouTube."""
        if not self.youtube_client:
            self.youtube_client = cast(
                YouTubeClient, PlatformFactory.create("youtube", self.settings_repo)
            )
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
                QMessageBox.information(
                    self, "Authentication Successful", "Successfully connected to YouTube!"
                )
                self._update_auth_status()
            else:
                QMessageBox.warning(
                    self, "Authentication Failed", "Failed to connect to YouTube. Please try again."
                )
        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error authenticating with YouTube: {e}")
            QMessageBox.critical(self, "Authentication Error", f"Error: {str(e)}")

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

        # Log for debugging
        logger.debug(f"Button state update: can_add={can_add}, can_link={can_link}")

        # Update all result widgets
        for widget in self.result_widgets:
            if isinstance(widget, YouTubeVideoItem):
                widget.update_button_state(can_add=can_add, can_link=can_link)

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

        # Check authentication
        if not self.youtube_client or not self.youtube_client.is_authenticated():
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to YouTube first using the 'Connect to YouTube' button.",
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

    def _handle_search_results(self, results: list) -> None:
        """Handle the search results from the background thread.

        Args:
            results: Search results from YouTube API
        """
        # Save the results
        self.search_results = results
        self.display_results(results)

    def _handle_search_error(self, error_msg: str) -> None:
        """Handle errors from the background thread.

        Args:
            error_msg: Error message
        """
        self.show_message(f"Error searching YouTube: {error_msg}")

    def display_results(self, results: list) -> None:
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
            QMessageBox.warning(
                self, "Link Error", "No track selected. Please select a track to link with."
            )
            return

        try:
            # Get track ID from selected track
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
                self.track_repo.add_platform_info(
                    track_id, "youtube", video_id, video_url, platform_data_json
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

                return video_data

            thread_manager = ThreadManager()
            worker = thread_manager.run_task(link_task)

            worker.signals.result.connect(lambda vd: self._handle_link_complete(vd))
            worker.signals.error.connect(lambda err: self._handle_link_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error linking track: {e}")
            QMessageBox.critical(self, "Link Error", f"Error linking track: {str(e)}")

    def _handle_link_complete(self, video_data: dict[str, Any]) -> None:
        """Handle completion of track linking.

        Args:
            video_data: The video data that was linked
        """
        # Extract title for display
        snippet = video_data.get("snippet", {})
        title = snippet.get("title", "")
        
        # Use the standardized implementation from the base class
        super()._handle_link_complete(video_data, title)

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
            QMessageBox.warning(
                self, "Add Error", "No playlist selected. Please select a playlist first."
            )
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

            # Check if a track with the same title already exists
            existing_track = (
                self.track_repo.session.query(Track).filter(and_(Track.title == title)).first()
            )

            if existing_track:
                QMessageBox.warning(self, "Add Error", f"Track already exists: {title}")
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

            worker.signals.result.connect(lambda vd: self._handle_add_complete(vd))
            worker.signals.error.connect(lambda err: self._handle_add_error(err))
            worker.signals.finished.connect(lambda: self.hide_loading())

        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error adding track: {e}")
            QMessageBox.critical(self, "Add Error", f"Error adding track: {str(e)}")

    def _handle_add_complete(self, video_data: dict[str, Any]) -> None:
        """Handle completion of track add.

        Args:
            video_data: The video data that was added
        """
        # Extract title for display
        snippet = video_data.get("snippet", {})
        title = snippet.get("title", "")

        # Emit signal with the added track
        self.track_added.emit(video_data)

        # Notify that data has changed
        self.selection_state.notify_data_changed()

        # Show success message
        self.show_message(f"Track added: {title}")

        # Wait a moment, then restore the search results
        QTimer.singleShot(2000, lambda: self._on_search(self.search_bar.get_search_text()))

    def _handle_add_error(self, error_msg: str) -> None:
        """Handle error during track add.

        Args:
            error_msg: The error message
        """
        logger.error(f"Error adding track: {error_msg}")
        QMessageBox.critical(self, "Add Error", f"Error adding track: {error_msg}")
