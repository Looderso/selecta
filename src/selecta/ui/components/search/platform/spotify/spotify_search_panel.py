"""Spotify search panel for searching and displaying Spotify tracks."""

import json
from typing import Any

import requests
from loguru import logger
from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QWidget
from sqlalchemy import and_

from selecta.core.data.models.db import Track
from selecta.core.data.repositories.image_repository import ImageRepository
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.utils.type_helpers import column_to_int
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.search.base_search_panel import BaseSearchPanel
from selecta.ui.components.search.platform.spotify.spotify_track_item import SpotifyTrackItem
from selecta.ui.components.search.utils import extract_title


class SpotifySearchPanel(BaseSearchPanel):
    """Panel for searching and displaying Spotify tracks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Spotify search panel.

        Args:
            parent: Parent widget
        """
        # Initialize parent class first
        super().__init__(parent)

        # Set object name
        self.setObjectName("spotifySearchPanel")

        # Initialize repositories for database operations
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()
        self.image_repo = ImageRepository()

        # Initialize spotify client
        self.settings_repo = SettingsRepository()
        self.spotify_client = PlatformFactory.create("spotify", self.settings_repo)

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Spotify"

    def _setup_platform_ui(self) -> None:
        """Set up Spotify-specific UI elements."""
        # Spotify doesn't need additional UI elements
        pass

    def _setup_header_content(self, header_layout: QHBoxLayout) -> None:
        """Set up Spotify-specific header content.

        Args:
            header_layout: Layout to add header content to
        """
        # Spotify doesn't need additional header content
        pass

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
                self.show_message("Not connected to Spotify. Please authenticate in the settings panel.")
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
            # Create a Spotify track item widget
            track_widget = SpotifyTrackItem(track)
            track_widget.link_clicked.connect(self._on_track_link)
            track_widget.add_clicked.connect(self._on_track_add)
            self.results_layout.addWidget(track_widget)
            self.result_widgets.append(track_widget)

        # Update button states based on current selection
        self._update_result_buttons()

        # Add a spacer at the end for better layout
        self.results_layout.addStretch(1)

    def _on_track_link(self, track_data: dict[str, Any]) -> None:
        """Handle track link button click.

        Args:
            track_data: Dictionary with track data
        """
        selected_track = self.selection_state.get_selected_track()

        if not selected_track:
            QMessageBox.warning(self, "Link Error", "No track selected. Please select a track to link with.")
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

            worker.signals.result.connect(lambda td: self._handle_link_complete(td, extract_title(td)))
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

    def _on_track_add(self, track_data: dict[str, Any]) -> None:
        """Handle track add button click.

        Args:
            track_data: Dictionary with track data
        """
        playlist_id = self.selection_state.get_selected_playlist_id()

        if not playlist_id:
            QMessageBox.warning(self, "Add Error", "No playlist selected. Please select a playlist first.")
            return

        try:
            # Extract track info
            title = track_data.get("name", "")
            artists = track_data.get("artists", [])
            artist = ", ".join([a.get("name", "") for a in artists])

            if not title or not artist:
                QMessageBox.warning(self, "Add Error", "Missing track information (title or artist)")
                return

            # Check if a track with the same title and artist already exists
            # This check should be quick so we'll keep it in the UI thread
            existing_track = (
                self.track_repo.session.query(Track).filter(and_(Track.title == title, Track.artist == artist)).first()
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

            worker.signals.result.connect(lambda td: self._handle_add_complete(td, f"{artist} - {title}"))
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
