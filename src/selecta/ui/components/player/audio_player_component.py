"""Audio player component for the bottom section of the main window."""

from loguru import logger
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.models.db import ImageSize
from selecta.ui.components.image_loader import DatabaseImageLoader


class ClickableSlider(QSlider):
    """Custom slider with exact click and dragging functionality."""

    def __init__(self, orientation, parent=None):
        """Initialize the clickable slider.

        Args:
            orientation: Qt.Orientation (Horizontal or Vertical)
            parent: Parent widget
        """
        super().__init__(orientation, parent)
        self.is_dragging = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events to seek to exact click position.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Get the option to determine the slider geometry
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            # Get the parts of the slider
            style = self.style()
            if style:
                handle_rect = style.subControlRect(
                    QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self
                )
            else:
                # Fallback if style is None
                handle_rect = QStyle.visualRect(opt.direction, opt.rect, opt.rect)

            # Check if the click is on the handle (for dragging behavior)
            handle_pos = handle_rect.contains(event.position().toPoint())

            if handle_pos:
                # If we're clicking on the handle, use default dragging behavior
                self.is_dragging = True
                return super().mousePressEvent(event)
            else:
                # If we're clicking elsewhere, jump to that position
                style = self.style()
                if style:
                    groove_rect = style.subControlRect(
                        QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
                    )
                else:
                    # Fallback if style is None
                    groove_rect = QStyle.visualRect(opt.direction, opt.rect, opt.rect)

                # For horizontal slider, calculate position
                slider_length = groove_rect.width()
                slider_min = groove_rect.x()

                # Get the click position relative to the slider
                pos = event.position().x() - slider_min

                # Calculate the value based on the click position
                value_range = self.maximum() - self.minimum()
                new_value = self.minimum() + (value_range * pos / slider_length)

                # Clamp the value to valid range
                new_value = max(self.minimum(), min(self.maximum(), new_value))

                # Set the value directly
                self.setValue(round(new_value))

                # Emit signals for consistency
                self.sliderPressed.emit()
                self.sliderMoved.emit(round(new_value))
                self.sliderReleased.emit()

                # Accept the event
                event.accept()
                return

        # For other buttons, use default behavior
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events.

        Args:
            event: Mouse event
        """
        if self.is_dragging:
            self.is_dragging = False

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move events.

        Args:
            event: Mouse event
        """
        if self.is_dragging:
            # Use default behavior when dragging
            super().mouseMoveEvent(event)
        else:
            # Ignore for clicks
            event.accept()


from selecta.core.data.models.db import Track
from selecta.core.utils.audio_player import AudioPlayerFactory, PlayerState, SpotifyAudioPlayer
from selecta.ui.components.audio_player_component import SpotifyDeviceDialog
from selecta.ui.components.player.youtube_player import create_youtube_player_window


class AudioPlayerComponent(QWidget):
    """Audio player UI component."""

    # Signal when a track is successfully loaded
    track_loaded = pyqtSignal(bool)

    # Shared image loader
    _db_image_loader = None

    def __init__(self, parent=None) -> None:
        """Initialize the audio player component.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_track = None
        self.current_track_id = None

        # Keep track of player windows if opened
        self.youtube_window = None

        # Flag to track if slider is being dragged by user
        self._slider_being_dragged = False

        # Initialize the local audio player
        self.player = AudioPlayerFactory.create_player("local")

        # Initialize the database image loader if needed
        if AudioPlayerComponent._db_image_loader is None:
            AudioPlayerComponent._db_image_loader = DatabaseImageLoader()

        # Connect to image loader signals
        AudioPlayerComponent._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)

        # Set up UI
        self._setup_ui()

        # Connect player signals
        self._connect_signals()

        # Set initial volume
        self.volume_slider.setValue(50)  # 50% volume by default
        self.player.set_volume(0.5)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 10)
        main_layout.setSpacing(5)

        # Track info layout
        track_info_layout = QHBoxLayout()
        track_info_layout.setContentsMargins(0, 0, 0, 0)

        # Album art label
        from PyQt6.QtGui import QPixmap

        self.cover_image = QLabel()
        self.cover_image.setFixedSize(50, 50)
        self.cover_image.setMinimumSize(50, 50)
        self.cover_image.setStyleSheet("background-color: #333; border: 1px solid #555;")
        self.default_pixmap = QPixmap(50, 50)
        self.default_pixmap.fill(Qt.GlobalColor.darkGray)
        self.cover_image.setPixmap(self.default_pixmap)
        self.cover_image.setScaledContents(True)
        track_info_layout.addWidget(self.cover_image)

        # Small spacing
        track_info_layout.addSpacing(10)

        # Track metadata (artist - title)
        self.track_label = QLabel("No track loaded")
        self.track_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        track_info_layout.addWidget(self.track_label, 1)  # Stretch to fill

        # Add track info layout to main layout
        main_layout.addLayout(track_info_layout)

        # Progress and time layout
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)

        # Current position
        self.position_label = QLabel("0:00")
        self.position_label.setMinimumWidth(40)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_layout.addWidget(self.position_label)

        # Progress slider - use our custom ClickableSlider
        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setTracking(True)  # Enable live tracking
        progress_layout.addWidget(self.progress_slider, 1)  # Stretch to fill

        # Duration
        self.duration_label = QLabel("0:00")
        self.duration_label.setMinimumWidth(40)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        progress_layout.addWidget(self.duration_label)

        # Add progress layout to main layout
        main_layout.addLayout(progress_layout)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Use standard Qt style icons
        from PyQt6.QtWidgets import QStyle

        # Play/Pause button
        self.play_pause_button = QPushButton()
        style = self.style()
        if style:
            self.play_pause_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        else:
            # Fallback if style is None
            self.play_pause_button.setText("▶")
        self.play_pause_button.setFixedSize(40, 40)
        controls_layout.addWidget(self.play_pause_button)

        # Store references to the icons
        style = self.style()
        if style:
            self.play_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            self.pause_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        else:
            # Use simple text fallbacks if style is None
            self.play_icon = "▶"
            self.pause_icon = "⏸"

        # Stop button
        self.stop_button = QPushButton()
        style = self.style()
        if style:
            self.stop_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        else:
            # Fallback if style is None
            self.stop_button.setText("⏹")
        self.stop_button.setFixedSize(40, 40)
        controls_layout.addWidget(self.stop_button)

        # Open in platform button (for Spotify, YouTube, etc.)
        self.open_in_platform_button = QPushButton("Open in Platform")
        self.open_in_platform_button.setVisible(False)
        self.open_in_platform_button.clicked.connect(self._open_in_platform)
        controls_layout.addWidget(self.open_in_platform_button)

        # Spotify device selection button
        self.select_device_button = QPushButton("Select Device")
        self.select_device_button.setVisible(False)
        self.select_device_button.clicked.connect(self._show_device_selection)
        controls_layout.addWidget(self.select_device_button)

        # Volume icon and label
        self.volume_label = QLabel("Vol:")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        controls_layout.addWidget(self.volume_label)

        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(100)
        controls_layout.addWidget(self.volume_slider)

        # Spacer
        controls_layout.addStretch(1)

        # Platform indicator (spotify, local, etc)
        self.platform_label = QLabel("LOCAL")
        self.platform_label.setStyleSheet("color: gray; font-size: 12px;")
        controls_layout.addWidget(self.platform_label)

        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)

        # Store properties for external platforms
        self.platform_track_url = None
        self.platform_type = None

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # UI controls
        self.play_pause_button.clicked.connect(self._toggle_playback)
        self.stop_button.clicked.connect(self._stop_playback)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.valueChanged.connect(self._on_slider_value_changed)
        self.volume_slider.valueChanged.connect(self._set_volume)

        # Connect player signals
        self._connect_player_signals()

    def _connect_player_signals(self) -> None:
        """Connect signals for the current player."""
        # Player signals
        self.player.state_changed.connect(self._on_player_state_changed)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.track_changed.connect(self._on_track_changed)
        self.player.error_occurred.connect(self._on_player_error)

    def _disconnect_player_signals(self) -> None:
        """Disconnect signals from the current player."""
        try:
            self.player.state_changed.disconnect(self._on_player_state_changed)
            self.player.position_changed.disconnect(self._on_position_changed)
            self.player.duration_changed.disconnect(self._on_duration_changed)
            self.player.track_changed.disconnect(self._on_track_changed)
            self.player.error_occurred.disconnect(self._on_player_error)
        except (TypeError, RuntimeError) as e:
            # This can happen if the signals were never connected
            logger.debug(f"Error disconnecting player signals: {e}")
            pass

    def _format_time(self, milliseconds: int) -> str:
        """Format milliseconds as MM:SS.

        Args:
            milliseconds: Time in milliseconds

        Returns:
            Formatted time string (MM:SS)
        """
        if milliseconds <= 0:
            return "0:00"

        seconds = int(milliseconds / 1000)
        minutes = int(seconds / 60)
        seconds_remainder = seconds % 60

        return f"{minutes}:{seconds_remainder:02d}"

    def _toggle_playback(self) -> None:
        """Toggle play/pause state."""
        if not self.current_track:
            # No track loaded, nothing to do
            return

        if self.player.is_playing:
            self.player.pause()
        else:
            self.player.play()

    def _stop_playback(self) -> None:
        """Stop playback."""
        self.player.stop()
        self.progress_slider.setValue(0)
        self.position_label.setText("0:00")

    def _on_slider_pressed(self) -> None:
        """Handle slider press - stop updating position from player."""
        # Flag to prevent position updates from audio player while user is dragging
        self._slider_being_dragged = True

    def _on_slider_moved(self, value) -> None:
        """Handle slider being moved - update position label.

        Args:
            value: New slider value (0-100)
        """
        # Update the position label with the position represented by the slider
        if self.player.get_duration() > 0:
            position = int(value / 100.0 * self.player.get_duration())
            self.position_label.setText(self._format_time(position))

    def _on_slider_released(self) -> None:
        """Handle slider release - seek to new position."""
        # Get the position from the slider (0-100) and convert to milliseconds
        value = self.progress_slider.value()
        position = int(value / 100.0 * self.player.get_duration())

        # Seek to the position
        self.player.seek(position)

        # Reset drag flag
        self._slider_being_dragged = False

    def _on_slider_value_changed(self, value) -> None:
        """Handle slider value changes from clicks or programmatic changes.

        Args:
            value: New slider value (0-100)
        """
        # Only handle direct clicks, not programmatic changes or drags
        if not self._slider_being_dragged and self.player.get_duration() > 0:
            # Check if this is from a click (not from the player updating)
            sender = self.sender()
            if sender == self.progress_slider and self.isEnabled():
                # Convert position and seek
                position = int(value / 100.0 * self.player.get_duration())
                self.player.seek(position)

                # Update position label
                self.position_label.setText(self._format_time(position))

    def _set_volume(self, value) -> None:
        """Set the volume level.

        Args:
            value: Volume level (0-100)
        """
        # Convert 0-100 range to 0.0-1.0
        self.player.set_volume(value / 100.0)

    def _on_player_state_changed(self, state: PlayerState) -> None:
        """Handle player state changes.

        Args:
            state: New player state
        """
        if state == PlayerState.PLAYING:
            if isinstance(self.pause_icon, str):
                self.play_pause_button.setText(self.pause_icon)
            else:
                self.play_pause_button.setIcon(self.pause_icon)
        else:  # PAUSED or STOPPED
            if isinstance(self.play_icon, str):
                self.play_pause_button.setText(self.play_icon)
            else:
                self.play_pause_button.setIcon(self.play_icon)

    def _on_position_changed(self, position: int) -> None:
        """Handle playback position changes.

        Args:
            position: Current position in milliseconds
        """
        # If slider is being dragged, don't update UI from player position
        if self._slider_being_dragged:
            return

        # Update position label
        self.position_label.setText(self._format_time(position))

        # Update slider (without triggering valueChanged)
        duration = self.player.get_duration()
        if duration > 0:
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(int(position / duration * 100))
            self.progress_slider.blockSignals(False)

    def _on_duration_changed(self, duration: int) -> None:
        """Handle track duration changes.

        Args:
            duration: Track duration in milliseconds
        """
        # Update duration label
        self.duration_label.setText(self._format_time(duration))

        # Reset position
        self.position_label.setText("0:00")
        self.progress_slider.setValue(0)

    def _on_track_changed(self, track: Track) -> None:
        """Handle track changes.

        Args:
            track: New track
        """
        self.current_track = track
        self.current_track_id = getattr(track, "id", None)

        # Update track info label
        self.track_label.setText(f"{track.artist} - {track.title}")

        # Load cover image from database if we have a track ID
        if self.current_track_id:
            # Reset to default cover first
            self.cover_image.setPixmap(self.default_pixmap)

            # Request image loading through the proper loader
            if AudioPlayerComponent._db_image_loader:
                AudioPlayerComponent._db_image_loader.load_track_image(self.current_track_id, ImageSize.THUMBNAIL)
            else:
                logger.debug("Image loader is not initialized")
        else:
            # No ID, try fallback methods
            logger.debug("No track ID available, using fallback methods")
            self._load_cover_fallback(track)

        # Signal that track was loaded
        self.track_loaded.emit(True)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap) -> None:
        """Handle loaded track image.

        Args:
            track_id: Track ID
            pixmap: Loaded image
        """
        logger.debug(f"Received image for track {track_id}, current track is {self.current_track_id}")
        logger.debug(f"Pixmap valid: {not pixmap.isNull()}, size: {pixmap.width()}x{pixmap.height()}")

        # Make sure this is for our current track
        if self.current_track_id == track_id:
            # Scale pixmap to fit our cover image display (50x50)
            scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio)
            self.cover_image.setPixmap(scaled_pixmap)
            self.cover_image.repaint()  # Force immediate repaint
            logger.debug(f"Set cover image for track {track_id}")
        else:
            logger.debug(f"Ignoring image for track {track_id} as it's not the current track")

    def _load_cover_fallback(self, track) -> None:
        """Load and display the cover image for a track using fallback methods.

        Args:
            track: The track to load the cover for
        """
        # Reset to default cover
        self.cover_image.setPixmap(self.default_pixmap)

        # Try to get cover from different sources
        cover_path = None

        # Check for image_path attribute
        if hasattr(track, "image_path") and track.image_path:
            cover_path = track.image_path

        # Check for cover_art_path attribute
        elif hasattr(track, "cover_art_path") and track.cover_art_path:
            cover_path = track.cover_art_path

        # Check platform metadata for image
        elif hasattr(track, "get_platform_metadata"):
            try:
                # Try Spotify first
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata and "image_url" in spotify_metadata:
                    # For remote images, we'd need to download them first
                    # For now, we'll just handle local paths
                    pass

                # Try YouTube next
                youtube_metadata = track.get_platform_metadata("youtube")
                if youtube_metadata and "thumbnail_url" in youtube_metadata:
                    # For remote images, we'd need to download them first
                    # For now, we'll just handle local paths
                    pass
            except Exception as e:
                logger.debug(f"Error getting cover from metadata: {e}")

        # If we found a cover path, try to load it
        if cover_path:
            try:
                pixmap = QPixmap(cover_path)
                if not pixmap.isNull():
                    # Scale to fit our cover image display (50x50)
                    pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio)
                    self.cover_image.setPixmap(pixmap)
                    logger.debug(f"Loaded cover image from {cover_path}")
            except Exception as e:
                logger.debug(f"Error loading cover image: {e}")

    def _on_player_error(self, error: str) -> None:
        """Handle player errors.

        Args:
            error: Error message
        """
        # Update UI to show error
        self.track_label.setText(f"Error: {error}")
        self.track_loaded.emit(False)

    def _open_in_platform(self) -> None:
        """Open the current track in its native platform (Spotify, YouTube, etc.)."""
        if self.platform_track_url:
            QDesktopServices.openUrl(QUrl(self.platform_track_url))

    def _show_device_selection(self) -> None:
        """Show the Spotify device selection dialog."""
        # Only show for Spotify tracks
        if self.platform_type != "Spotify" or not isinstance(self.player, SpotifyAudioPlayer):
            return

        # Create and show the device dialog
        dialog = SpotifyDeviceDialog(self.player, self)

        # Connect to device selected signal
        dialog.device_selected.connect(self._on_device_selected)

        # Show dialog
        dialog.exec()

    def _on_device_selected(self, device_id: str) -> None:
        """Handle device selection from dialog.

        Args:
            device_id: Selected Spotify device ID
        """
        if isinstance(self.player, SpotifyAudioPlayer):
            logger.info(f"Setting Spotify device to {device_id}")
            self.player.set_device(device_id)

            # If we have a track loaded, try to play it on the new device
            if self.current_track and self.player.spotify_track_id:
                try:
                    logger.info("Starting playback on selected device")
                    self.player.play()
                except Exception as e:
                    logger.error(f"Error starting playback on device: {e}")

    def _get_youtube_id(self, track) -> str | None:
        """Extract YouTube ID from a track.

        Args:
            track: The track to analyze

        Returns:
            YouTube video ID or None if not found
        """
        youtube_id = None

        # Check platform info directly
        if hasattr(track, "platform_info"):
            for info in track.platform_info:
                # Handle both dict and object formats
                if isinstance(info, dict):
                    if info.get("platform") == "youtube":
                        youtube_id = info.get("platform_id")
                        logger.info(f"Found YouTube platform info (dict): {youtube_id}")
                        return youtube_id
                else:
                    try:
                        if info.platform == "youtube":
                            youtube_id = info.platform_id
                            logger.info(f"Found YouTube platform info (obj): {youtube_id}")
                            return youtube_id
                    except AttributeError:
                        logger.debug(f"Unexpected platform_info type: {type(info)}")
                        continue

        # Check for direct YouTube ID attributes
        if hasattr(track, "video_id") and track.video_id:
            youtube_id = track.video_id
        elif hasattr(track, "youtube_id") and track.youtube_id:
            youtube_id = track.youtube_id
        # Check for platform metadata
        elif hasattr(track, "get_platform_metadata"):
            try:
                youtube_metadata = track.get_platform_metadata("youtube")
                if youtube_metadata and "id" in youtube_metadata:
                    youtube_id = youtube_metadata["id"]
            except Exception as e:
                logger.error(f"Error getting platform metadata: {e}")
        # Check if this is a YouTubeVideo model
        elif hasattr(track, "id") and hasattr(track, "channel_id"):
            youtube_id = track.id

        return youtube_id

    def _is_youtube_track(self, track) -> bool:
        """Check if a track should be played with the YouTube player.

        Args:
            track: The track to check

        Returns:
            True if the track is a YouTube track, False otherwise
        """
        youtube_id = self._get_youtube_id(track)
        if youtube_id:
            return True

        # Also check if the track has any YouTube-related attributes
        if hasattr(track, "__dict__"):
            track_dict = track.__dict__
            for key, value in track_dict.items():
                if isinstance(value, str) and "youtube" in key.lower() and value:
                    return True

        return False

    def _get_spotify_info(self, track) -> tuple[str | None, str | None]:
        """Extract Spotify ID and URI from a track.

        Args:
            track: The track to analyze

        Returns:
            Tuple of (spotify_id, spotify_uri) or (None, None) if not found
        """
        spotify_id = None
        spotify_uri = None

        # Check platform info directly
        if hasattr(track, "platform_info"):
            for info in track.platform_info:
                # Handle both dict and object formats
                if isinstance(info, dict):
                    if info.get("platform") == "spotify":
                        spotify_id = info.get("platform_id")
                        if spotify_id and not spotify_id.startswith("spotify:"):
                            spotify_uri = f"spotify:track:{spotify_id}"
                        else:
                            spotify_uri = spotify_id
                        return spotify_id, spotify_uri
                else:
                    try:
                        if info.platform == "spotify":
                            spotify_id = info.platform_id
                            if spotify_id and not spotify_id.startswith("spotify:"):
                                spotify_uri = f"spotify:track:{spotify_id}"
                            else:
                                spotify_uri = spotify_id
                            return spotify_id, spotify_uri
                    except AttributeError:
                        logger.debug(f"Unexpected platform_info type: {type(info)}")
                        continue

        # Check for direct Spotify ID attributes
        if hasattr(track, "spotify_id") and track.spotify_id:
            spotify_id = track.spotify_id
            spotify_uri = f"spotify:track:{spotify_id}" if not spotify_id.startswith("spotify:") else spotify_id
        # Check for URI directly
        elif hasattr(track, "uri") and track.uri and "spotify" in track.uri:
            spotify_uri = track.uri
            spotify_id = spotify_uri.split(":")[-1] if spotify_uri.startswith("spotify:track:") else spotify_uri
        # Check for platform metadata
        elif hasattr(track, "get_platform_metadata"):
            try:
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata:
                    if "id" in spotify_metadata:
                        spotify_id = spotify_metadata["id"]
                        if not spotify_id.startswith("spotify:"):
                            spotify_uri = f"spotify:track:{spotify_id}"
                        else:
                            spotify_uri = spotify_id
                    elif "uri" in spotify_metadata:
                        spotify_uri = spotify_metadata["uri"]
                        if spotify_uri.startswith("spotify:track:"):
                            spotify_id = spotify_uri.split(":")[-1]
                        else:
                            spotify_id = spotify_uri
            except Exception as e:
                logger.error(f"Error getting Spotify metadata: {e}")

        # For tracks from dict representation
        if hasattr(track, "to_display_data"):
            try:
                display_data = track.to_display_data()
                if "spotify_uri" in display_data and display_data["spotify_uri"]:
                    spotify_uri = display_data["spotify_uri"]
                    spotify_id = spotify_uri.split(":")[-1] if spotify_uri.startswith("spotify:track:") else spotify_uri
                elif "id" in display_data and "spotify" in str(track.__class__).lower():
                    spotify_id = display_data["id"]
                    spotify_uri = f"spotify:track:{spotify_id}" if not spotify_id.startswith("spotify:") else spotify_id
            except Exception as e:
                logger.error(f"Error getting display data: {e}")

        return spotify_id, spotify_uri

    def _is_spotify_track(self, track) -> bool:
        """Check if a track is a Spotify track.

        Args:
            track: The track to check

        Returns:
            True if the track is a Spotify track, False otherwise
        """
        # Check if this is a SpotifyTrackItem
        if track.__class__.__name__ == "SpotifyTrackItem":
            return True

        # Check for direct Spotify attributes
        if hasattr(track, "preview_url") and track.preview_url:
            return True

        if hasattr(track, "spotify_id") and track.spotify_id:
            return True

        # For tracks from dict representation, check if preview_url exists in display data
        if hasattr(track, "to_display_data"):
            try:
                display_data = track.to_display_data()
                if "preview_url" in display_data and display_data["preview_url"]:
                    return True
                if "spotify_uri" in display_data and display_data["spotify_uri"]:
                    return True
            except Exception as e:
                logger.error(f"Error getting display data: {e}")

        # Check for platform references
        if hasattr(track, "platforms") and isinstance(track.platforms, list) and "spotify" in track.platforms:
            return True

        # Check platform info
        if hasattr(track, "platform_info"):
            for info in track.platform_info:
                # Handle both dict and object formats
                if isinstance(info, dict):
                    if info.get("platform") == "spotify":
                        return True
                else:
                    try:
                        if info.platform == "spotify":
                            return True
                    except AttributeError:
                        continue

        # Check for platform metadata
        if hasattr(track, "get_platform_metadata"):
            try:
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata:
                    return True
            except Exception as e:
                logger.error(f"Error getting Spotify metadata: {e}")

        # Also check if track has any Spotify-related attributes
        if hasattr(track, "__dict__"):
            track_dict = track.__dict__
            for key, value in track_dict.items():
                if isinstance(value, str) and "spotify" in key.lower() and value:
                    return True

        return False

    @pyqtSlot(object)
    def load_track(self, track) -> None:
        """Load a track for playback.

        Args:
            track: Track to load
        """
        if not track:
            self.track_label.setText("No track provided")
            self.track_loaded.emit(False)
            return

        # Reset platform track URL and button visibility
        self.platform_track_url = None
        self.platform_type = None
        self.open_in_platform_button.setVisible(False)

        # Log track type information for debugging
        logger.info(f"Loading track: {track.__class__.__name__}")
        logger.info(f"Track ID: {getattr(track, 'track_id', 'unknown')}")
        logger.info(f"Track artist: {getattr(track, 'artist', 'unknown')}")
        logger.info(f"Track title: {getattr(track, 'title', 'unknown')}")

        # Log additional information to help debug
        if hasattr(track, "platform_info"):
            logger.info(f"Platform info type: {type(track.platform_info)}")
            if track.platform_info:
                sample = (
                    track.platform_info[0]
                    if isinstance(track.platform_info, list) and track.platform_info
                    else track.platform_info
                )
                logger.info(f"Platform info sample: {type(sample)} - {sample}")

        if hasattr(track, "local_path"):
            logger.info(f"Local path: {track.local_path}")

        # Check if this is a YouTube track first
        if self._is_youtube_track(track):
            logger.info("Track identified as YouTube track")
            youtube_id = self._get_youtube_id(track)
            if youtube_id:
                # Update track label
                self.track_label.setText(f"{track.artist} - {track.title} (YouTube)")
                self.platform_label.setText("YOUTUBE")
                self.track_loaded.emit(True)

                # Set platform URL for "Open in Platform" button
                self.platform_track_url = f"https://www.youtube.com/watch?v={youtube_id}"
                self.platform_type = "YouTube"
                self.open_in_platform_button.setText("Open in YouTube")
                self.open_in_platform_button.setVisible(True)

                # Launch YouTube player window if requested
                if True:  # You can add a setting here to control behavior
                    if self.youtube_window:
                        # If a window already exists, close it first
                        try:
                            self.youtube_window.close()
                        except Exception as e:
                            logger.warning(f"Error closing existing YouTube window: {e}")

                    # Create new YouTube window
                    self.youtube_window = create_youtube_player_window(youtube_id, self.window())
                return
            else:
                logger.warning("Could not find YouTube ID for track")
                self.track_label.setText("Error: Missing YouTube ID")
                self.track_loaded.emit(False)
                return

        # Check if this is a Spotify track
        is_spotify = self._is_spotify_track(track)
        logger.info(f"Is Spotify track: {is_spotify}")

        if is_spotify:
            # Get Spotify URI and ID
            spotify_id, spotify_uri = self._get_spotify_info(track)
            logger.info(f"Spotify ID: {spotify_id}, URI: {spotify_uri}")

            if spotify_uri:
                # Set platform URL for "Open in Platform" button
                self.platform_track_url = spotify_uri
                self.platform_type = "Spotify"
                self.open_in_platform_button.setText("Open in Spotify")
                self.open_in_platform_button.setVisible(True)

                # Update track label to indicate platform
                self.track_label.setText(f"{track.artist} - {track.title} (Spotify)")
                self.platform_label.setText("SPOTIFY")

                # Enable Spotify device selection button
                self.select_device_button.setText("Spotify Devices")
                self.select_device_button.setVisible(True)

                # For Spotify tracks, we'll first check if there's a local version available
                if hasattr(track, "local_path") and track.local_path:
                    logger.info("Spotify track has local path, checking for playback options")

                    # Create a Spotify player for API control
                    self._disconnect_player_signals()
                    self.player = AudioPlayerFactory.create_player("spotify")
                    self._connect_player_signals()

                    # Set volume
                    volume = self.volume_slider.value() / 100.0
                    self.player.set_volume(volume)

                    # Try to load track for direct Spotify app control
                    if self.player.load_track(track):
                        logger.info("Successfully loaded track for Spotify API control")
                        self.track_loaded.emit(True)
                    else:
                        # Fall back to local playback
                        logger.info("Falling back to local playback")
                        self._disconnect_player_signals()
                        self.player = AudioPlayerFactory.create_player("local")
                        self._connect_player_signals()
                        self.player.set_volume(volume)

                        if self.player.load_track(track):
                            # Use the same playback mechanism for consistency
                            from PyQt6.QtCore import QTimer

                            QTimer.singleShot(100, self._ensure_playback)
                            self.track_loaded.emit(True)
                        else:
                            # Failed to load local file, just open in Spotify
                            self._open_in_platform()
                            self.track_loaded.emit(False)
                else:
                    # No local path, use Spotify API to control playback
                    logger.info("Using Spotify API for playback control")

                    # Create and set up Spotify player
                    self._disconnect_player_signals()
                    self.player = AudioPlayerFactory.create_player("spotify")
                    self._connect_player_signals()

                    # Set volume
                    volume = self.volume_slider.value() / 100.0
                    self.player.set_volume(volume)

                    # Try to load track for direct control
                    if self.player.load_track(track):
                        logger.info("Successfully loaded track for Spotify API control")
                        self.track_loaded.emit(True)
                    else:
                        # Fall back to opening in Spotify
                        logger.info("Falling back to opening in Spotify app")
                        self._open_in_platform()
                        self.track_loaded.emit(True)

                return

        # For local tracks, use the local player
        logger.info("Using local player")
        current_player_class = self.player.__class__.__name__
        if current_player_class != "LocalAudioPlayer":
            logger.info(f"Switching from {current_player_class} to LocalAudioPlayer")
            self._disconnect_player_signals()
            self.player = AudioPlayerFactory.create_player("local")
            self._connect_player_signals()
            volume = self.volume_slider.value() / 100.0
            self.player.set_volume(volume)

        self.platform_label.setText("LOCAL")

        # Load with local player
        if self.player.load_track(track):
            # Track loaded successfully, player.track_changed signal will be emitted
            # Start playing immediately
            logger.info("Successfully loaded track with local player")

            # Use a timer to ensure player is fully initialized before playing
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(100, self._ensure_playback)
        else:
            # Failed to load track
            logger.warning("Failed to load track with local player")
            self.track_label.setText("Failed to load track")
            self.track_loaded.emit(False)

    def _ensure_playback(self) -> None:
        """Ensure a track is playing (used after loading a track)."""
        if self.player:
            # Force stop and play for a clean start
            self.player.stop()
            self.player.play()
            logger.info("Auto-play started")
