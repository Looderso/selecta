"""Audio player component for the bottom section of the main window."""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.models.db import Track
from selecta.core.utils.audio_player import AudioPlayerFactory, PlayerState


class AudioPlayerComponent(QWidget):
    """Audio player UI component."""

    # Signal when a track is successfully loaded
    track_loaded = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        """Initialize the audio player component.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_track = None

        # Flag to track if slider is being dragged by user
        self._slider_being_dragged = False

        # Initialize the local audio player for now
        # Future: We'll use the AudioPlayerFactory with platform detection
        self.player = AudioPlayerFactory.create_player("local")

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
        self.position_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        progress_layout.addWidget(self.position_label)

        # Progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
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
        self.play_pause_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.play_pause_button.setFixedSize(40, 40)
        controls_layout.addWidget(self.play_pause_button)

        # Store references to the icons
        self.play_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)

        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setFixedSize(40, 40)
        controls_layout.addWidget(self.stop_button)

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

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # UI controls
        self.play_pause_button.clicked.connect(self._toggle_playback)
        self.stop_button.clicked.connect(self._stop_playback)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.volume_slider.valueChanged.connect(self._set_volume)

        # Player signals
        self.player.state_changed.connect(self._on_player_state_changed)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.track_changed.connect(self._on_track_changed)
        self.player.error_occurred.connect(self._on_player_error)

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
            self.play_pause_button.setIcon(self.pause_icon)
        else:  # PAUSED or STOPPED
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

        # Update track info label
        self.track_label.setText(f"{track.artist} - {track.title}")

        # Update platform label
        self.platform_label.setText("LOCAL")

        # Signal that track was loaded
        self.track_loaded.emit(True)

    def _on_player_error(self, error: str) -> None:
        """Handle player errors.

        Args:
            error: Error message
        """
        # Update UI to show error
        self.track_label.setText(f"Error: {error}")
        self.track_loaded.emit(False)

    @pyqtSlot(object)
    def load_track(self, track) -> None:
        """Load a track for playback and start playing immediately.

        Args:
            track: Track to load
        """
        if self.player.load_track(track):
            # Track loaded successfully, player.track_changed signal will be emitted
            # Start playing immediately
            self.player.play()
        else:
            # Failed to load track
            self.track_label.setText("Failed to load track")
            self.track_loaded.emit(False)
