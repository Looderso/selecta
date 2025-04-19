"""Audio player utility for playing tracks from various sources."""

from abc import abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol

from loguru import logger
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from selecta.core.data.repositories.track_repository import TrackRepository


class PlayerState(Enum):
    """Enum for player states."""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class TrackInfo(Protocol):
    """Protocol for track information required by the player."""

    @property
    def title(self) -> str:
        """Get track title."""
        ...

    @property
    def artist(self) -> str:
        """Get track artist."""
        ...

    @property
    def duration_ms(self) -> int | None:
        """Get track duration in milliseconds."""
        ...


class AbstractAudioPlayer(QObject):
    """Abstract base class for audio players implementing different playback sources."""

    # Signals for player state changes
    state_changed = pyqtSignal(PlayerState)
    position_changed = pyqtSignal(int)  # Position in milliseconds
    duration_changed = pyqtSignal(int)  # Duration in milliseconds
    track_changed = pyqtSignal(object)  # Current track info
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(self) -> None:
        """Initialize the abstract audio player."""
        super().__init__()
        self.state = PlayerState.STOPPED
        self.current_track: TrackInfo | None = None

    @abstractmethod
    def play(self) -> None:
        """Start or resume playback."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop playback."""
        pass

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (maximum)
        """
        pass

    @abstractmethod
    def seek(self, position_ms: int) -> None:
        """Seek to position.

        Args:
            position_ms: Position in milliseconds
        """
        pass

    @abstractmethod
    def get_position(self) -> int:
        """Get current playback position.

        Returns:
            Current position in milliseconds
        """
        pass

    @abstractmethod
    def get_duration(self) -> int:
        """Get track duration.

        Returns:
            Track duration in milliseconds
        """
        pass

    @abstractmethod
    def load_track(self, track: Any) -> bool:
        """Load a track for playback.

        Args:
            track: Track object or identifier

        Returns:
            True if track loaded successfully, False otherwise
        """
        pass

    @property
    def is_playing(self) -> bool:
        """Check if player is in playing state.

        Returns:
            True if playing, False otherwise
        """
        return self.state == PlayerState.PLAYING

    @property
    def is_paused(self) -> bool:
        """Check if player is in paused state.

        Returns:
            True if paused, False otherwise
        """
        return self.state == PlayerState.PAUSED

    @property
    def is_stopped(self) -> bool:
        """Check if player is in stopped state.

        Returns:
            True if stopped, False otherwise
        """
        return self.state == PlayerState.STOPPED


class LocalAudioPlayer(AbstractAudioPlayer):
    """Audio player for local audio files."""

    def __init__(self) -> None:
        """Initialize the local audio player."""
        super().__init__()
        self.track_repo = TrackRepository()

        # Initialize Qt media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_error)

    def _on_position_changed(self, position: int) -> None:
        """Handle position change.

        Args:
            position: Current position in milliseconds
        """
        self.position_changed.emit(position)

    def _on_duration_changed(self, duration: int) -> None:
        """Handle duration change.

        Args:
            duration: Track duration in milliseconds
        """
        self.duration_changed.emit(duration)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Handle playback state changes.

        Args:
            state: Qt playback state
        """
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.state = PlayerState.PLAYING
            self.state_changed.emit(PlayerState.PLAYING)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.state = PlayerState.PAUSED
            self.state_changed.emit(PlayerState.PAUSED)
        else:  # StoppedState
            self.state = PlayerState.STOPPED
            self.state_changed.emit(PlayerState.STOPPED)

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """Handle playback errors.

        Args:
            error: Error code
            error_string: Error description
        """
        logger.error(f"Audio player error: {error} - {error_string}")
        self.error_occurred.emit(error_string)

    def play(self) -> None:
        """Start or resume playback."""
        self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        self.player.pause()

    def stop(self) -> None:
        """Stop playback."""
        self.player.stop()

    def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (maximum)
        """
        self.audio_output.setVolume(volume)

    def seek(self, position_ms: int) -> None:
        """Seek to position.

        Args:
            position_ms: Position in milliseconds
        """
        self.player.setPosition(position_ms)

    def get_position(self) -> int:
        """Get current playback position.

        Returns:
            Current position in milliseconds
        """
        return self.player.position()

    def get_duration(self) -> int:
        """Get track duration.

        Returns:
            Track duration in milliseconds
        """
        return self.player.duration()

    def load_track(self, track) -> bool:
        """Load a local track for playback.

        Args:
            track: Track object with local_path (can be Track or LocalTrackItem)

        Returns:
            True if track loaded successfully, False otherwise
        """
        if not track:
            logger.warning("No track provided")
            return False

        # If we have a track ID, get the full track object
        if isinstance(track, int):
            track = self.track_repo.get_by_id(track)
            if not track:
                logger.warning(f"Track ID {track} not found")
                return False

        # Check if track has a local path
        if not hasattr(track, "local_path") or not track.local_path:
            logger.warning("Track has no local path")
            return False

        # For Track objects from database, check is_available_locally flag
        # LocalTrackItem doesn't have this attribute but is locally available if it has a path
        if hasattr(track, "is_available_locally") and not track.is_available_locally:
            logger.warning(f"Track {track.id} is not available locally")
            return False

        # Check if the file exists
        local_path = Path(track.local_path)
        if not local_path.exists():
            logger.warning(f"Track file not found: {local_path}")
            self.error_occurred.emit(f"Track file not found: {local_path}")
            return False

        try:
            # Load the media file
            self.player.setSource(QUrl.fromLocalFile(str(local_path.absolute())))
            self.current_track = track
            self.track_changed.emit(track)
            return True
        except Exception as e:
            logger.exception(f"Error loading track: {e}")
            self.error_occurred.emit(f"Error loading track: {e}")
            return False


class AudioPlayerFactory:
    """Factory for creating audio players based on track source."""

    @staticmethod
    def create_player(platform: str) -> AbstractAudioPlayer:
        """Create a player for the specified platform.

        Args:
            platform: Platform name ('local', 'spotify', 'youtube', etc.)

        Returns:
            Audio player instance

        Raises:
            ValueError: If player for platform is not implemented
        """
        if platform == "local":
            return LocalAudioPlayer()
        # Future implementations:
        # elif platform == "spotify":
        #     return SpotifyAudioPlayer()
        else:
            raise ValueError(f"Audio player for platform '{platform}' not implemented")

    @staticmethod
    def create_player_for_track(track) -> AbstractAudioPlayer:
        """Create the appropriate player based on the track type.

        Args:
            track: Track object to determine the appropriate player

        Returns:
            Audio player instance appropriate for the track

        Raises:
            ValueError: If cannot determine appropriate player
        """
        # For all tracks, we now use the local player
        # YouTube tracks will be handled separately with the YouTube player window
        return LocalAudioPlayer()
