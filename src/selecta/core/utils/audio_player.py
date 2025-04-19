"""Audio player utility for playing tracks from various sources."""

from abc import abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol

from loguru import logger
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.spotify.auth import SpotifyAuthManager


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


class SpotifyAudioPlayer(AbstractAudioPlayer):
    """Audio player for Spotify tracks using preview URLs and Spotify Connect API."""

    def __init__(self) -> None:
        """Initialize the Spotify audio player."""
        super().__init__()
        self.settings_repo = SettingsRepository()
        self.auth_manager = SpotifyAuthManager(settings_repo=self.settings_repo)

        # Flag to determine if we're controlling the Spotify app or playing preview URLs
        self.use_spotify_app = False
        self.spotify_track_id = None
        self.spotify_api_client = None
        self.current_device_id = None

        # Try to get an authenticated Spotify client
        try:
            from selecta.core.platform.spotify.client import SpotifyClient

            self.spotify_client = SpotifyClient(settings_repo=self.settings_repo)
            # Get a direct reference to the spotipy client for playback control
            self.spotify_api_client = self.auth_manager.get_spotify_client()
        except Exception as e:
            logger.warning(f"Failed to initialize Spotify client: {e}")
            self.spotify_client = None
            self.spotify_api_client = None

        # Initialize Qt media player for preview playback
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
        logger.error(f"Spotify player error: {error} - {error_string}")
        self.error_occurred.emit(error_string)

    def play(self) -> None:
        """Start or resume playback."""
        if self.use_spotify_app and self.spotify_api_client:
            try:
                # If we have a specific track to play
                if self.spotify_track_id:
                    # If we have a specific device ID, use it, otherwise play on active device
                    if self.current_device_id:
                        self.spotify_api_client.start_playback(
                            device_id=self.current_device_id,
                            uris=[f"spotify:track:{self.spotify_track_id}"],
                        )
                    else:
                        self.spotify_api_client.start_playback(
                            uris=[f"spotify:track:{self.spotify_track_id}"]
                        )
                else:
                    # Just resume current playback if no specific track
                    if self.current_device_id:
                        self.spotify_api_client.start_playback(device_id=self.current_device_id)
                    else:
                        self.spotify_api_client.start_playback()

                # Update our internal state
                self.state = PlayerState.PLAYING
                self.state_changed.emit(PlayerState.PLAYING)
                logger.info("Started Spotify playback via API")
            except Exception as e:
                logger.error(f"Error controlling Spotify playback: {e}")
                self.error_occurred.emit(f"Error controlling Spotify: {e}")
        else:
            self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        if self.use_spotify_app and self.spotify_api_client:
            try:
                if self.current_device_id:
                    self.spotify_api_client.pause_playback(device_id=self.current_device_id)
                else:
                    self.spotify_api_client.pause_playback()

                # Update our internal state
                self.state = PlayerState.PAUSED
                self.state_changed.emit(PlayerState.PAUSED)
                logger.info("Paused Spotify playback via API")
            except Exception as e:
                logger.error(f"Error pausing Spotify playback: {e}")
                self.error_occurred.emit(f"Error pausing Spotify: {e}")
        else:
            self.player.pause()

    def stop(self) -> None:
        """Stop playback."""
        if self.use_spotify_app and self.spotify_api_client:
            try:
                if self.current_device_id:
                    self.spotify_api_client.pause_playback(device_id=self.current_device_id)
                else:
                    self.spotify_api_client.pause_playback()

                # Update our internal state
                self.state = PlayerState.STOPPED
                self.state_changed.emit(PlayerState.STOPPED)
                logger.info("Stopped Spotify playback via API")
            except Exception as e:
                logger.error(f"Error stopping Spotify playback: {e}")
                self.error_occurred.emit(f"Error stopping Spotify: {e}")
        else:
            self.player.stop()

    def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (maximum)
        """
        if self.use_spotify_app and self.spotify_api_client:
            try:
                # Spotify API expects volume as an integer 0-100
                volume_percent = int(volume * 100)

                if self.current_device_id:
                    self.spotify_api_client.volume(volume_percent, device_id=self.current_device_id)
                else:
                    self.spotify_api_client.volume(volume_percent)

                logger.info(f"Set Spotify volume to {volume_percent}% via API")
            except Exception as e:
                logger.error(f"Error setting Spotify volume: {e}")
                self.error_occurred.emit(f"Error setting Spotify volume: {e}")
        else:
            self.audio_output.setVolume(volume)

    def seek(self, position_ms: int) -> None:
        """Seek to position.

        Args:
            position_ms: Position in milliseconds
        """
        if self.use_spotify_app and self.spotify_api_client:
            try:
                if self.current_device_id:
                    self.spotify_api_client.seek_track(
                        position_ms, device_id=self.current_device_id
                    )
                else:
                    self.spotify_api_client.seek_track(position_ms)

                # Emit our own position changed signal for UI updates
                self.position_changed.emit(position_ms)
                logger.info(f"Seeked Spotify playback to {position_ms}ms via API")
            except Exception as e:
                logger.error(f"Error seeking Spotify playback: {e}")
                self.error_occurred.emit(f"Error seeking Spotify: {e}")
        else:
            self.player.setPosition(position_ms)

    def get_position(self) -> int:
        """Get current playback position.

        Returns:
            Current position in milliseconds
        """
        if self.use_spotify_app and self.spotify_api_client:
            try:
                # Get the current playback state from Spotify API
                playback_info = self.spotify_api_client.current_playback()
                if playback_info and "progress_ms" in playback_info:
                    return playback_info["progress_ms"]
                return 0
            except Exception as e:
                logger.error(f"Error getting Spotify position: {e}")
                return 0
        else:
            return self.player.position()

    def get_duration(self) -> int:
        """Get track duration.

        Returns:
            Track duration in milliseconds
        """
        if self.use_spotify_app and self.spotify_api_client:
            try:
                # Get the current playback state from Spotify API
                playback_info = self.spotify_api_client.current_playback()
                if playback_info and "item" in playback_info and playback_info["item"]:
                    return playback_info["item"].get("duration_ms", 0)
                return 0
            except Exception as e:
                logger.error(f"Error getting Spotify duration: {e}")
                return 0
        else:
            return self.player.duration()

    def _get_spotify_preview_url(self, track) -> str | None:
        """Extract Spotify preview URL from a track.

        Args:
            track: The track to analyze

        Returns:
            Preview URL or None if not found
        """
        # Check if preview_url is directly accessible
        if hasattr(track, "preview_url") and track.preview_url:
            return track.preview_url

        # Check for preview_url in display data
        if hasattr(track, "to_display_data"):
            try:
                display_data = track.to_display_data()
                if "preview_url" in display_data and display_data["preview_url"]:
                    return display_data["preview_url"]
            except Exception as e:
                logger.error(f"Error getting display data: {e}")

        # Check for platform metadata
        if hasattr(track, "get_platform_metadata"):
            try:
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata and "preview_url" in spotify_metadata:
                    return spotify_metadata["preview_url"]
            except Exception as e:
                logger.error(f"Error getting Spotify metadata: {e}")

        # Check platform info for Spotify
        if hasattr(track, "platform_info"):
            for info in track.platform_info:
                # Handle both dict and object formats
                if isinstance(info, dict):
                    if info.get("platform") == "spotify" and info.get("preview_url"):
                        return info.get("preview_url")
                else:
                    try:
                        if (
                            info.platform == "spotify"
                            and hasattr(info, "preview_url")
                            and info.preview_url
                        ):
                            return info.preview_url
                    except AttributeError:
                        continue

        # Try accessing known attributes by name
        for attr_name in ["preview", "spotify_preview_url", "preview_link"]:
            if hasattr(track, attr_name) and getattr(track, attr_name):
                value = getattr(track, attr_name)
                if isinstance(value, str) and (
                    value.startswith("http://") or value.startswith("https://")
                ):
                    return value

        # If we have a Spotify URI or ID but no preview URL, try to fetch it from the API
        spotify_id = self._get_spotify_id(track)
        if spotify_id and self.spotify_client and self.spotify_client.is_authenticated():
            logger.info(f"Attempting to fetch preview URL for Spotify ID: {spotify_id}")
            try:
                # Use a normalized format without the 'spotify:track:' prefix if present
                if spotify_id.startswith("spotify:track:"):
                    spotify_id = spotify_id.split(":")[-1]

                # Search for the track with this ID
                results = self.spotify_client.client.track(spotify_id)
                if results and "preview_url" in results and results["preview_url"]:
                    logger.info(f"Found preview URL via API: {results['preview_url']}")
                    return results["preview_url"]
            except Exception as e:
                logger.error(f"Error fetching preview URL from Spotify API: {e}")

        return None

    def _get_spotify_uri(self, track) -> str | None:
        """Extract Spotify URI from a track.

        Args:
            track: The track to analyze

        Returns:
            Spotify URI or None if not found
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
                        return spotify_uri
                else:
                    try:
                        if info.platform == "spotify":
                            spotify_id = info.platform_id
                            if spotify_id and not spotify_id.startswith("spotify:"):
                                spotify_uri = f"spotify:track:{spotify_id}"
                            else:
                                spotify_uri = spotify_id
                            return spotify_uri
                    except AttributeError:
                        logger.debug(f"Unexpected platform_info type: {type(info)}")
                        continue

        # Check for direct Spotify ID attributes
        if hasattr(track, "spotify_id") and track.spotify_id:
            spotify_id = track.spotify_id
            if not spotify_id.startswith("spotify:"):
                spotify_uri = f"spotify:track:{spotify_id}"
            else:
                spotify_uri = spotify_id
        # Check for URI directly
        elif hasattr(track, "uri") and track.uri and "spotify" in track.uri:
            spotify_uri = track.uri

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
            except Exception as e:
                logger.error(f"Error getting platform metadata: {e}")

        return spotify_uri

    def get_spotify_uri(self, track) -> str | None:
        """Get the Spotify URI for opening in Spotify app.

        Args:
            track: Track object with Spotify information

        Returns:
            Spotify URI or None if not available
        """
        return self._get_spotify_uri(track)

    def get_available_devices(self) -> list[dict]:
        """Get a list of available Spotify devices.

        Returns:
            List of device information dictionaries
        """
        if not self.spotify_api_client:
            logger.warning("Spotify API client not initialized")
            return []

        try:
            devices = self.spotify_api_client.devices()
            if devices and "devices" in devices:
                return devices["devices"]
            return []
        except Exception as e:
            logger.error(f"Error getting Spotify devices: {e}")
            return []

    def get_playback_state(self) -> dict | None:
        """Get the current Spotify playback state.

        Returns:
            Playback state information or None if not available
        """
        if not self.spotify_api_client:
            return None

        try:
            return self.spotify_api_client.current_playback()
        except Exception as e:
            logger.error(f"Error getting Spotify playback state: {e}")
            return None

    def set_device(self, device_id: str) -> bool:
        """Set the Spotify device to use for playback.

        Args:
            device_id: Spotify device ID

        Returns:
            True if successful, False otherwise
        """
        if not device_id:
            logger.warning("No device ID provided")
            return False

        self.current_device_id = device_id
        logger.info(f"Set Spotify device to {device_id}")
        return True

    def _get_spotify_id(self, track) -> tuple[str | None, str | None]:
        """Extract Spotify ID and URI from a track.

        Args:
            track: The track to analyze

        Returns:
            Tuple of (spotify_id, spotify_uri) or (None, None) if not found
        """
        spotify_id = None
        spotify_uri = None

        # First try to get the URI directly
        spotify_uri = self._get_spotify_uri(track)
        if spotify_uri:
            # Extract ID from URI if needed
            if spotify_uri.startswith("spotify:track:"):
                spotify_id = spotify_uri.split(":")[-1]
            else:
                spotify_id = spotify_uri
            return spotify_id, spotify_uri

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
            if not spotify_id.startswith("spotify:"):
                spotify_uri = f"spotify:track:{spotify_id}"
            else:
                spotify_uri = spotify_id
            return spotify_id, spotify_uri

        # Check for platform metadata
        if hasattr(track, "get_platform_metadata"):
            try:
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata and "id" in spotify_metadata:
                    spotify_id = spotify_metadata["id"]
                    if not spotify_id.startswith("spotify:"):
                        spotify_uri = f"spotify:track:{spotify_id}"
                    else:
                        spotify_uri = spotify_id
                    return spotify_id, spotify_uri
            except Exception as e:
                logger.error(f"Error getting platform metadata: {e}")

        return spotify_id, spotify_uri

    def load_track(self, track) -> bool:
        """Load a Spotify track for playback.

        Args:
            track: Track object with Spotify information

        Returns:
            True if track loaded successfully, False otherwise
        """
        if not track:
            logger.warning("No track provided")
            return False

        # Try to get Spotify ID first for direct playback
        spotify_id, spotify_uri = self._get_spotify_id(track)

        # Log the track details to help debug
        logger.info(f"Loading Spotify track: {track.__class__.__name__}")
        logger.info(f"Track ID: {spotify_id}, URI: {spotify_uri}")

        # Check if we have what we need for direct playback via Spotify API
        if spotify_id and self.spotify_api_client and self.auth_manager.get_spotify_client():
            # Store Spotify ID for play/pause/seek controls
            if spotify_id.startswith("spotify:track:"):
                self.spotify_track_id = spotify_id.split(":")[-1]
            else:
                self.spotify_track_id = spotify_id

            # Enable Spotify app control
            self.use_spotify_app = True
            self.current_track = track
            self.track_changed.emit(track)

            # Check if we have any available devices
            devices = self.get_available_devices()
            if devices:
                logger.info(f"Found {len(devices)} Spotify devices")
                # Use the first active device if available
                for device in devices:
                    if device.get("is_active", False):
                        self.current_device_id = device["id"]
                        logger.info(
                            f"Using active Spotify device: {device['name']} ({device['id']})"
                        )
                        break

                # If no active device found, use the first available one
                if not self.current_device_id and devices:
                    self.current_device_id = devices[0]["id"]
                    logger.info(
                        f"Using first Spotify device: {devices[0]['name']} ({devices[0]['id']})"
                    )

            # Try to start playback immediately if there are devices available
            if devices:
                try:
                    self.play()
                    return True
                except Exception as e:
                    logger.error(f"Error starting Spotify playback: {e}")
                    # Fall back to preview URL if direct playback fails

            # If no devices or direct playback failed, we'll still set the track as loaded
            # so the UI can show controls
            return True

        # Fall back to preview URL if direct playback not available
        preview_url = self._get_spotify_preview_url(track)
        logger.info(f"Preview URL: {preview_url}")

        if not preview_url:
            # No preview URL found
            logger.warning("No Spotify preview URL available for this track")

            # If we have an ID but no preview, we can still control Spotify app
            if spotify_id:
                self.spotify_track_id = (
                    spotify_id.split(":")[-1] if ":" in spotify_id else spotify_id
                )
                self.use_spotify_app = True
                self.current_track = track
                self.track_changed.emit(track)
                return True

            self.error_occurred.emit("No preview available for this Spotify track")
            return False

        try:
            # Use local preview playback instead of Spotify app control
            self.use_spotify_app = False

            # Load the preview URL
            self.player.setSource(QUrl(preview_url))
            self.current_track = track
            self.track_changed.emit(track)
            logger.info(f"Loaded Spotify preview for {track.title}")
            return True
        except Exception as e:
            logger.exception(f"Error loading Spotify preview: {e}")
            self.error_occurred.emit(f"Error loading Spotify preview: {e}")
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
        elif platform == "spotify":
            return SpotifyAudioPlayer()
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
        # Check if this is a Spotify track by class name
        if track.__class__.__name__ in ["SpotifyTrack", "SpotifyTrackItem"]:
            logger.info(f"Creating Spotify player based on class name: {track.__class__.__name__}")
            return SpotifyAudioPlayer()

        # Check if track dictionary data contains 'spotify' platform identifier
        if hasattr(track, "to_display_data"):
            try:
                display_data = track.to_display_data()
                if "platforms" in display_data and "spotify" in display_data["platforms"]:
                    logger.info("Creating Spotify player based on platforms in display data")
                    return SpotifyAudioPlayer()
                if "preview_url" in display_data and display_data["preview_url"]:
                    logger.info("Creating Spotify player based on preview_url in display data")
                    return SpotifyAudioPlayer()
                if "spotify_uri" in display_data and display_data["spotify_uri"]:
                    logger.info("Creating Spotify player based on spotify_uri in display data")
                    return SpotifyAudioPlayer()
            except Exception as e:
                logger.error(f"Error checking display data: {e}")

        # Check if track has platforms attribute
        if (
            hasattr(track, "platforms")
            and isinstance(track.platforms, list)
            and "spotify" in track.platforms
        ):
            logger.info("Creating Spotify player based on platforms attribute")
            return SpotifyAudioPlayer()

        # Check if this is a Spotify track by preview URL
        if hasattr(track, "preview_url") and track.preview_url:
            logger.info("Creating Spotify player based on preview_url attribute")
            return SpotifyAudioPlayer()

        # Check for Spotify platform info
        if hasattr(track, "platform_info"):
            for info in track.platform_info:
                if info.platform == "spotify":
                    logger.info("Creating Spotify player based on platform_info")
                    return SpotifyAudioPlayer()

        # Check for Spotify ID
        if hasattr(track, "spotify_id") and track.spotify_id:
            logger.info("Creating Spotify player based on spotify_id attribute")
            return SpotifyAudioPlayer()

        # Check for platform metadata
        if hasattr(track, "get_platform_metadata"):
            try:
                spotify_metadata = track.get_platform_metadata("spotify")
                if spotify_metadata:
                    logger.info("Creating Spotify player based on platform metadata")
                    return SpotifyAudioPlayer()
            except:
                pass

        # Check for any spotify-related attributes
        if hasattr(track, "__dict__"):
            try:
                track_dict = track.__dict__
                for key, value in track_dict.items():
                    if isinstance(value, str) and "spotify" in key.lower() and value:
                        logger.info(f"Creating Spotify player based on attribute: {key}")
                        return SpotifyAudioPlayer()
            except:
                pass

        # For all other tracks, we use the local player
        # YouTube tracks will be handled separately in the audio_player_component
        return LocalAudioPlayer()
