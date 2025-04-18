"""Dynamic content controller for the main window.

This component handles switching between track details and search panels
based on context and user actions.
"""

from typing import Any, cast

from loguru import logger
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.models.db import Track, TrackPlatformInfo
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.discogs.discogs_search_panel import DiscogsSearchPanel
from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.playlist.track_details_panel import TrackDetailsPanel
from selecta.ui.components.spotify.spotify_search_panel import SpotifySearchPanel
from selecta.ui.components.youtube.youtube_search_panel import YouTubeSearchPanel


class DynamicContent(LoadableWidget):
    """Controller for switching between track details and search panels."""

    # Signal to indicate that track was updated in database
    track_updated = pyqtSignal(int)  # Emits track_id when updated

    def __init__(self, parent=None) -> None:
        """Initialize the dynamic content controller.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

        # Track the current state
        self._current_track_id = None
        self._current_platform = None
        self._track_repo = TrackRepository()
        self._platform_clients = {}  # Cache platform clients

        # Connect signals from search panels
        self.spotify_search_panel.track_linked.connect(self._handle_track_linked)
        self.spotify_search_panel.track_added.connect(self._handle_track_added)
        self.discogs_search_panel.track_linked.connect(self._handle_track_linked)
        self.discogs_search_panel.track_added.connect(self._handle_track_added)
        self.youtube_search_panel.track_linked.connect(self._handle_track_linked)
        self.youtube_search_panel.track_added.connect(self._handle_track_added)

        # Import here to avoid circular imports
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()
        self.selection_state.track_selected.connect(self._on_track_selected)

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

        # Stacked widget for swapping panels
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        # Create panels
        self.track_details_panel = TrackDetailsPanel()
        self.spotify_search_panel = SpotifySearchPanel()
        self.discogs_search_panel = DiscogsSearchPanel()
        self.youtube_search_panel = YouTubeSearchPanel()

        # Add panels to stacked widget
        self.stacked_widget.addWidget(self.track_details_panel)
        self.stacked_widget.addWidget(self.spotify_search_panel)
        self.stacked_widget.addWidget(self.discogs_search_panel)
        self.stacked_widget.addWidget(self.youtube_search_panel)

        # Create update button container (initially hidden)
        self.update_button_container = QWidget()
        update_button_layout = QHBoxLayout(self.update_button_container)
        update_button_layout.setContentsMargins(10, 5, 10, 10)

        # Create update buttons
        self.update_from_spotify_button = QPushButton("Update from Spotify")
        self.update_from_discogs_button = QPushButton("Update from Discogs")

        # Connect buttons
        self.update_from_spotify_button.clicked.connect(lambda: self._show_update_dialog("spotify"))
        self.update_from_discogs_button.clicked.connect(lambda: self._show_update_dialog("discogs"))

        # Add buttons to layout
        update_button_layout.addWidget(self.update_from_spotify_button)
        update_button_layout.addWidget(self.update_from_discogs_button)

        # Add button container to main layout
        content_layout.addWidget(self.update_button_container)
        self.update_button_container.setVisible(False)

        # Show track details panel initially
        self.stacked_widget.setCurrentWidget(self.track_details_panel)

    def _on_track_selected(self, track: Any) -> None:
        """Handle track selection.

        Args:
            track: The selected track
        """
        if not track:
            self._show_track_details(None)
            return

        # Store current track ID
        self._current_track_id = track.track_id

        # Get track from database by ID if it's a local track
        if hasattr(track, "is_local") and track.is_local:
            # Show loading indicator
            self.show_loading("Loading track details...")

            # Get track details from database
            def get_track_details() -> tuple[Track | None, dict[str, TrackPlatformInfo | None]]:
                track_data = self._track_repo.get_by_id(self._current_track_id)

                # Get platform info for all platforms
                platform_info = {}
                for platform in ["spotify", "discogs"]:
                    info = self._track_repo.get_platform_info(self._current_track_id, platform)
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

    def _handle_track_details_loaded(
        self, result: tuple[Track | None, dict[str, TrackPlatformInfo | None]]
    ) -> None:
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

        # Show update buttons for local tracks
        self.update_button_container.setVisible(True)

        # Enable/disable buttons based on available platform info
        self.update_from_spotify_button.setEnabled(platform_info.get("spotify") is not None)
        self.update_from_discogs_button.setEnabled(platform_info.get("discogs") is not None)

    def _handle_track_details_error(self, error: str) -> None:
        """Handle error when loading track details.

        Args:
            error: Error message
        """
        logger.error(f"Error loading track details: {error}")
        self._show_track_details(None)

    def _show_track_details(self, track: Any, platform_info: dict[str, Any] = None) -> None:
        """Show track details panel with the given track.

        Args:
            track: Track to display
            platform_info: Optional platform info for the track
        """
        # Set track in details panel
        self.track_details_panel.set_track(track, platform_info)

        # Show track details panel
        self.stacked_widget.setCurrentWidget(self.track_details_panel)

        # Hide update buttons for non-local tracks
        if not track or not hasattr(track, "is_local") or not track.is_local:
            self.update_button_container.setVisible(False)

    def show_search_panel(self, platform: str, query: str = "") -> None:
        """Show search panel for the given platform.

        Args:
            platform: Platform to search on ('spotify', 'discogs', or 'youtube')
            query: Optional initial search query
        """
        # Store current platform
        self._current_platform = platform

        # Show appropriate search panel
        if platform == "spotify":
            self.stacked_widget.setCurrentWidget(self.spotify_search_panel)
            if query:
                self.spotify_search_panel.search(query)
        elif platform == "discogs":
            self.stacked_widget.setCurrentWidget(self.discogs_search_panel)
            if query:
                self.discogs_search_panel.search(query)
        elif platform == "youtube":
            self.stacked_widget.setCurrentWidget(self.youtube_search_panel)
            if query:
                self.youtube_search_panel.search(query)

        # Hide update buttons when showing search panel
        self.update_button_container.setVisible(False)

    def _handle_track_linked(self, track_data: dict[str, Any]) -> None:
        """Handle track linking from search panel.

        Args:
            track_data: Track data that was linked
        """
        # Emit signal to notify that track was updated
        if self._current_track_id:
            self.track_updated.emit(self._current_track_id)

        # Reload track details if we're showing a local track
        if self._current_track_id:
            selected_track = self.selection_state.get_selected_track()
            if selected_track and hasattr(selected_track, "is_local") and selected_track.is_local:
                self._on_track_selected(selected_track)

    def _handle_track_added(self, track_data: dict[str, Any]) -> None:
        """Handle track add from search panel.

        Args:
            track_data: Track data that was added
        """
        # Notify data change
        self.selection_state.notify_data_changed()

    def _show_update_dialog(self, platform: str) -> None:
        """Show dialog for updating track from platform.

        Args:
            platform: Platform to update from ('spotify' or 'discogs')
        """
        # Implement the update dialog in the next iteration
        if not self._current_track_id:
            return

        # Show confirmation or dialog to update the track
        from PyQt6.QtWidgets import QMessageBox

        msg_box = QMessageBox()
        msg_box.setWindowTitle(f"Update from {platform.capitalize()}")
        msg_box.setText(f"Do you want to update this track with {platform.capitalize()} metadata?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

        ret = msg_box.exec()

        if ret == QMessageBox.StandardButton.Yes:
            # Show loading indicator
            self.show_loading(f"Updating track from {platform.capitalize()}...")

            # Get platform client
            client = self._get_platform_client(platform)

            if client and client.is_authenticated():
                # Get platform info
                platform_info = self._track_repo.get_platform_info(self._current_track_id, platform)

                if platform_info and platform_info.platform_id:
                    # Run update in background thread
                    thread_manager = ThreadManager()

                    # Different update functions based on platform
                    if platform == "spotify":

                        def update_func():
                            return self._update_from_spotify(platform_info.platform_id)
                    else:  # discogs

                        def update_func():
                            return self._update_from_discogs(platform_info.platform_id)

                    worker = thread_manager.run_task(update_func)

                    # Handle results
                    worker.signals.result.connect(
                        lambda result: self._handle_update_complete(result)
                    )
                    worker.signals.error.connect(lambda error: self._handle_update_error(error))
                    worker.signals.finished.connect(lambda: self.hide_loading())
                else:
                    self.hide_loading()
                    QMessageBox.warning(
                        self,
                        "Update Error",
                        f"No {platform.capitalize()} info found for this track",
                    )
            else:
                self.hide_loading()
                QMessageBox.warning(
                    self, "Authentication Error", f"Not authenticated with {platform.capitalize()}"
                )

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

    def _update_from_spotify(self, spotify_id: str) -> dict[str, Any]:
        """Update track from Spotify.

        Args:
            spotify_id: Spotify track ID

        Returns:
            Updated track data
        """
        # Get Spotify client
        client = cast(Any, self._get_platform_client("spotify"))

        # Get track details from Spotify
        track_data = client.get_track(spotify_id)

        if not track_data:
            raise ValueError(f"Track with ID {spotify_id} not found on Spotify")

        # Update track in database
        if self._current_track_id:
            # Extract track info
            title = track_data.get("name", "")
            artists = track_data.get("artists", [])
            artist = ", ".join([a.get("name", "") for a in artists]) if artists else ""
            album = track_data.get("album", {}).get("name", "")
            duration_ms = track_data.get("duration_ms", 0)

            # Update track in database
            self._track_repo.update(
                self._current_track_id,
                {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration_ms": duration_ms,
                },
            )

            # Download and update image if available
            if "album" in track_data and "images" in track_data["album"]:
                images = track_data["album"]["images"]
                if images:
                    # Find largest image for best quality
                    sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
                    if sorted_images:
                        album_image_url = sorted_images[0].get("url")
                        if album_image_url:
                            import requests

                            from selecta.core.data.repositories.image_repository import (
                                ImageRepository,
                            )

                            # Get the image data
                            response = requests.get(album_image_url, timeout=10)
                            if response.ok:
                                # Store images in database
                                image_repo = ImageRepository()
                                image_repo.resize_and_store_image(
                                    original_data=response.content,
                                    track_id=self._current_track_id,
                                    source="spotify",
                                    source_url=album_image_url,
                                )

        return track_data

    def _update_from_discogs(self, discogs_id: str) -> dict[str, Any]:
        """Update track from Discogs.

        Args:
            discogs_id: Discogs release ID

        Returns:
            Updated track data
        """
        # Get Discogs client
        client = cast(Any, self._get_platform_client("discogs"))

        # Get release details from Discogs
        release_data = client.get_release(discogs_id)

        if not release_data:
            raise ValueError(f"Release with ID {discogs_id} not found on Discogs")

        # Update track in database
        if self._current_track_id:
            # Extract track info
            title = release_data.get("title", "")
            artist = release_data.get("artist", "")
            year = release_data.get("year", "")

            # Update track in database
            self._track_repo.update(
                self._current_track_id,
                {
                    "title": title,
                    "artist": artist,
                    "year": year,
                },
            )

            # Download and update image if available
            cover_url = release_data.get("cover_url")
            thumb_url = release_data.get("thumb_url")
            image_url = cover_url or thumb_url

            if image_url:
                import requests

                from selecta.core.data.repositories.image_repository import ImageRepository

                # Get the image data
                response = requests.get(image_url, timeout=10)
                if response.ok:
                    # Store images in database
                    image_repo = ImageRepository()
                    image_repo.resize_and_store_image(
                        original_data=response.content,
                        track_id=self._current_track_id,
                        source="discogs",
                        source_url=image_url,
                    )

            # Update genres if available
            if "genre" in release_data and release_data["genre"]:
                self._track_repo.set_track_genres(
                    track_id=self._current_track_id,
                    genre_names=release_data["genre"],
                    source="discogs",
                )

        return release_data

    def _handle_update_complete(self, result: dict[str, Any]) -> None:
        """Handle completion of track update.

        Args:
            result: Updated track data
        """
        from PyQt6.QtWidgets import QMessageBox

        # Show success message
        QMessageBox.information(self, "Update Complete", "Track updated successfully!")

        # Emit signal to notify that track was updated
        if self._current_track_id:
            self.track_updated.emit(self._current_track_id)

        # Reload track details
        if self._current_track_id:
            selected_track = self.selection_state.get_selected_track()
            if selected_track:
                self._on_track_selected(selected_track)

    def _handle_update_error(self, error: str) -> None:
        """Handle error during track update.

        Args:
            error: Error message
        """
        from PyQt6.QtWidgets import QMessageBox

        logger.error(f"Error updating track: {error}")
        QMessageBox.critical(self, "Update Error", f"Error updating track: {error}")
