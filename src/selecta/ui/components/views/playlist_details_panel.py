from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.common.selection_state import SelectionState


class PlatformDistributionBar(QWidget):
    """Widget showing the distribution of tracks across platforms."""

    def __init__(self, parent=None):
        """Initialize the platform distribution bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._platform_counts = {}
        self._total_tracks = 0
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)

    def set_data(self, platform_counts: dict[str, int], total_tracks: int):
        """Set the platform distribution data.

        Args:
            platform_counts: Dictionary mapping platform names to track counts
            total_tracks: Total number of tracks
        """
        self._platform_counts = platform_counts
        self._total_tracks = total_tracks
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Paint the distribution bar.

        Args:
            event: Paint event
        """
        if not self._total_tracks or not self._platform_counts:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Define platform colors
        platform_colors = {
            "spotify": QColor(30, 215, 96),  # Spotify green
            "rekordbox": QColor(0, 128, 255),  # Rekordbox blue
            "discogs": QColor(255, 128, 0),  # Discogs orange
            "youtube": QColor(255, 0, 0),  # YouTube red
            "local": QColor(150, 150, 150),  # Grey for local
            "other": QColor(100, 100, 100),  # Dark grey for others
        }

        # Draw the bars
        x = 0
        width = self.width()
        height = self.height()

        # Sort platforms to ensure consistent order
        sorted_platforms = sorted(self._platform_counts.items(), key=lambda x: (x[0] != "local", x[0]))

        for platform, count in sorted_platforms:
            # Calculate segment width
            segment_width = int((count / self._total_tracks) * width)

            # Set color
            color = platform_colors.get(platform, platform_colors["other"])
            painter.fillRect(x, 0, segment_width, height, color)

            # Move to next segment
            x += segment_width

        # Draw border around the entire bar
        painter.setPen(QColor(50, 50, 50))
        painter.drawRect(0, 0, width - 1, height - 1)


class PlaylistDetailsPanel(QWidget):
    """Panel showing detailed information about a playlist."""

    sync_requested = pyqtSignal(str)  # Emits platform to sync with

    def __init__(self, parent=None):
        """Initialize the playlist details panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self._current_playlist = None

        # Connect to selection state
        self.selection_state = SelectionState()
        self.selection_state.playlist_selected.connect(self.set_playlist)

    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(15)

        # Header section
        self.header_label = QLabel("Playlist Details")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(self.header_label)

        # Basic info section
        info_group = QGroupBox("Information")
        info_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)

        # Statistics layout - simple vertical layout
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)

        # Basic stats
        self.track_count_label = QLabel("Tracks: 0")
        stats_layout.addWidget(self.track_count_label)

        # Optional stats that may not be available for all platforms
        self.duration_label = QLabel("Duration: Unknown")
        self.bpm_label = QLabel("BPM range: Unknown")

        # Add to layout
        stats_layout.addWidget(self.duration_label)
        stats_layout.addWidget(self.bpm_label)

        info_layout.addLayout(stats_layout)
        content_layout.addWidget(info_group)

        # Platform distribution section
        platform_group = QGroupBox("Platform Distribution")
        platform_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        platform_layout = QVBoxLayout(platform_group)
        platform_layout.setSpacing(10)

        # Distribution bar
        self.platform_distribution_bar = PlatformDistributionBar()
        platform_layout.addWidget(self.platform_distribution_bar)

        # Platform stats labels
        self.platform_stats_container = QWidget()
        platform_stats_layout = QVBoxLayout(self.platform_stats_container)
        platform_stats_layout.setContentsMargins(0, 0, 0, 0)
        platform_stats_layout.setSpacing(4)

        self.local_count_label = QLabel("Local: 0 tracks")
        self.spotify_count_label = QLabel("Spotify: 0 tracks")
        self.rekordbox_count_label = QLabel("Rekordbox: 0 tracks")
        self.discogs_count_label = QLabel("Discogs: 0 tracks")
        self.youtube_count_label = QLabel("YouTube: 0 tracks")

        platform_stats_layout.addWidget(self.local_count_label)
        platform_stats_layout.addWidget(self.spotify_count_label)
        platform_stats_layout.addWidget(self.rekordbox_count_label)
        platform_stats_layout.addWidget(self.discogs_count_label)
        platform_stats_layout.addWidget(self.youtube_count_label)

        platform_layout.addWidget(self.platform_stats_container)
        content_layout.addWidget(platform_group)

        # Sync section
        sync_group = QGroupBox("Synchronization")
        sync_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setSpacing(10)

        self.sync_status_label = QLabel("Sync Status: Unknown")
        sync_layout.addWidget(self.sync_status_label)

        # Sync buttons
        sync_buttons_layout = QHBoxLayout()
        sync_buttons_layout.setSpacing(8)

        self.sync_spotify_button = QPushButton("Sync with Spotify")
        self.sync_spotify_button.clicked.connect(lambda: self.sync_requested.emit("spotify"))

        self.sync_rekordbox_button = QPushButton("Sync with Rekordbox")
        self.sync_rekordbox_button.clicked.connect(lambda: self.sync_requested.emit("rekordbox"))

        self.sync_discogs_button = QPushButton("Sync with Discogs")
        self.sync_discogs_button.clicked.connect(lambda: self.sync_requested.emit("discogs"))

        sync_buttons_layout.addWidget(self.sync_spotify_button)
        sync_buttons_layout.addWidget(self.sync_rekordbox_button)
        sync_buttons_layout.addWidget(self.sync_discogs_button)

        sync_layout.addLayout(sync_buttons_layout)
        content_layout.addWidget(sync_group)

        # Add stretch at the end to push everything to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Initial state - disabled buttons
        self._set_buttons_enabled(False)

    def set_playlist(self, playlist):
        """Set the playlist to display.

        Args:
            playlist: Playlist object to display
        """
        self._current_playlist = playlist

        if playlist is None:
            # Clear display and disable buttons
            self.header_label.setText("No Playlist Selected")

            # Hide all stat labels
            self.track_count_label.setVisible(False)
            self.duration_label.setVisible(False)
            self.bpm_label.setVisible(False)

            # Clear platform stats
            self._reset_platform_stats()

            # Clear sync status
            self.sync_status_label.setText("Sync Status: Unknown")

            # Disable buttons
            self._set_buttons_enabled(False)
            return

        # Update header with playlist name
        playlist_name = getattr(playlist, "name", "Untitled Playlist")
        self.header_label.setText(playlist_name)

        # Calculate and display statistics
        self._calculate_playlist_statistics(playlist)

        # Update platform stats
        self._update_platform_stats(playlist)

        # Update sync status
        self._update_sync_status(playlist)

        # Enable buttons based on playlist type
        self._set_buttons_enabled(True)
        self._update_button_availability(playlist)

    def _calculate_playlist_statistics(self, playlist):
        """Calculate and display playlist statistics.

        Args:
            playlist: Playlist object
        """
        # For debugging
        from loguru import logger

        # Basic stats - always show track count
        track_count = getattr(playlist, "track_count", 0)

        # If playlist has get_tracks method, get actual tracks
        tracks = []
        if hasattr(playlist, "get_tracks"):
            try:
                tracks = playlist.get_tracks()
                # Update track count if needed
                if not track_count and tracks:
                    track_count = len(tracks)
            except Exception as e:
                logger.error(f"Error getting tracks: {e}")

        # Show track count if available
        if track_count > 0:
            self.track_count_label.setText(f"Tracks: {track_count}")
            self.track_count_label.setVisible(True)
        else:
            self.track_count_label.setVisible(False)

        # DURATION CALCULATION
        logger.debug(f"Calculating duration for playlist: {getattr(playlist, 'name', 'Unknown')}")
        duration_ms = 0

        # Method 1: Check if playlist has duration_ms attribute
        if hasattr(playlist, "duration_ms") and playlist.duration_ms:
            try:
                duration_ms = int(playlist.duration_ms)
                logger.debug(f"Found duration_ms attribute: {duration_ms}ms")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting duration_ms: {e}")

        # Method 2: Calculate from tracks if available and duration not found
        if duration_ms <= 0 and tracks:
            # Sum durations of all tracks with duration
            track_durations = []
            for t in tracks:
                if hasattr(t, "duration_ms") and t.duration_ms:
                    try:
                        dur = int(t.duration_ms)
                        if dur > 0:
                            track_durations.append(dur)
                    except (ValueError, TypeError):
                        pass

            if track_durations:
                duration_ms = sum(track_durations)
                logger.debug(f"Calculated duration from {len(track_durations)} tracks: {duration_ms}ms")

        # Display duration if we have a valid total
        if duration_ms > 0:
            total_seconds = duration_ms // 1000
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                duration_text = f"Duration: {hours}h {minutes}m {seconds}s"
            else:
                duration_text = f"Duration: {minutes}m {seconds}s"

            self.duration_label.setText(duration_text)
            self.duration_label.setVisible(True)
            logger.debug(f"Showing duration: {duration_text}")
        else:
            self.duration_label.setVisible(False)
            logger.debug("No valid duration found, hiding duration label")

        # BPM RANGE CALCULATION
        logger.debug("Calculating BPM range")
        bpm_values = []

        # Method 1: Check if some tracks have BPM
        if tracks:
            for t in tracks:
                # Try multiple ways of accessing BPM
                if hasattr(t, "bpm") and t.bpm is not None:
                    try:
                        bpm_value = float(t.bpm)
                        if bpm_value > 0:
                            bpm_values.append(bpm_value)
                    except (ValueError, TypeError):
                        # Skip values that can't be converted to float
                        pass
                elif hasattr(t, "get_bpm") and callable(t.get_bpm):
                    try:
                        bpm_value = float(t.get_bpm())
                        if bpm_value > 0:
                            bpm_values.append(bpm_value)
                    except (ValueError, TypeError):
                        pass

            logger.debug(f"Found {len(bpm_values)} tracks with BPM values")

        # Display BPM info if we have any valid values
        if bpm_values:
            min_bpm = min(bpm_values)
            max_bpm = max(bpm_values)
            avg_bpm = sum(bpm_values) / len(bpm_values)

            if min_bpm == max_bpm:
                self.bpm_label.setText(f"BPM: {min_bpm:.1f}")
                logger.debug(f"All tracks have same BPM: {min_bpm:.1f}")
            else:
                bpm_text = f"BPM range: {min_bpm:.1f} - {max_bpm:.1f} (avg: {avg_bpm:.1f})"
                if len(bpm_values) < track_count:
                    percent = (len(bpm_values) / track_count) * 100
                    bpm_text += f" ({len(bpm_values)}/{track_count} tracks, {percent:.0f}%)"

                self.bpm_label.setText(bpm_text)
                logger.debug(f"BPM range: {min_bpm:.1f} - {max_bpm:.1f}")

            self.bpm_label.setVisible(True)
        else:
            self.bpm_label.setVisible(False)
            logger.debug("No BPM data available, hiding BPM label")

    def _reset_platform_stats(self):
        """Reset platform statistics to default values and hide all platform stats."""
        # Hide all platform label counts
        self.local_count_label.setVisible(False)
        self.spotify_count_label.setVisible(False)
        self.rekordbox_count_label.setVisible(False)
        self.discogs_count_label.setVisible(False)
        self.youtube_count_label.setVisible(False)

        # Reset and hide platform distribution bar
        self.platform_distribution_bar.set_data({}, 0)
        self.platform_distribution_bar.setVisible(False)

    def _update_platform_stats(self, playlist):
        """Update platform statistics display.

        Args:
            playlist: Playlist object with platform data
        """
        # Default empty stats
        platform_counts = {"local": 0, "spotify": 0, "rekordbox": 0, "discogs": 0, "youtube": 0}

        # Track counts for each platform
        has_tracks = False
        total_tracks = 0

        # Get tracks if available
        if hasattr(playlist, "get_tracks"):
            tracks = playlist.get_tracks()
            total_tracks = len(tracks)

            if total_tracks > 0:
                has_tracks = True

                # Count tracks per platform
                for track in tracks:
                    # Track is considered local by default
                    platform_counts["local"] += 1

                    # Check each platform connection
                    for platform in ["spotify", "rekordbox", "discogs", "youtube"]:
                        # Check if track has platform_info for this platform
                        has_platform = False

                        # Method 1: platform_info dict
                        if hasattr(track, "platform_info") and isinstance(track.platform_info, dict):
                            has_platform = platform in track.platform_info and track.platform_info[platform] is not None

                        # Method 2: has_platform_info method
                        elif hasattr(track, "has_platform_info"):
                            has_platform = track.has_platform_info(platform)

                        # Method 3: platform-specific attributes
                        elif (
                            platform == "spotify"
                            and hasattr(track, "spotify_id")
                            and track.spotify_id
                            or platform == "rekordbox"
                            and hasattr(track, "rekordbox_id")
                            and track.rekordbox_id
                            or (
                                platform == "discogs"
                                and hasattr(track, "discogs_id")
                                and track.discogs_id
                                or platform == "youtube"
                                and hasattr(track, "youtube_id")
                                and track.youtube_id
                            )
                        ):
                            has_platform = True

                        if has_platform:
                            platform_counts[platform] += 1

        # If no tracks or get_tracks method not available, try to get the platform
        if not has_tracks:
            platform = getattr(playlist, "platform", "local")
            if platform in platform_counts:
                platform_counts[platform] = 1
                total_tracks = 1
                has_tracks = True

        # Show platform distribution section only if we have tracks
        if has_tracks:
            # Show/hide platform count labels based on whether tracks exist for that platform
            self.local_count_label.setVisible(platform_counts["local"] > 0)
            self.spotify_count_label.setVisible(platform_counts["spotify"] > 0)
            self.rekordbox_count_label.setVisible(platform_counts["rekordbox"] > 0)
            self.discogs_count_label.setVisible(platform_counts["discogs"] > 0)
            self.youtube_count_label.setVisible(platform_counts["youtube"] > 0)

            # Update text for visible labels
            if platform_counts["local"] > 0:
                self.local_count_label.setText(f"Local: {platform_counts['local']} tracks")
            if platform_counts["spotify"] > 0:
                self.spotify_count_label.setText(f"Spotify: {platform_counts['spotify']} tracks")
            if platform_counts["rekordbox"] > 0:
                self.rekordbox_count_label.setText(f"Rekordbox: {platform_counts['rekordbox']} tracks")
            if platform_counts["discogs"] > 0:
                self.discogs_count_label.setText(f"Discogs: {platform_counts['discogs']} tracks")
            if platform_counts["youtube"] > 0:
                self.youtube_count_label.setText(f"YouTube: {platform_counts['youtube']} tracks")

            # Update platform distribution bar
            self.platform_distribution_bar.set_data(platform_counts, total_tracks)
            self.platform_distribution_bar.setVisible(True)
        else:
            # Hide all platform stats if no tracks
            self._reset_platform_stats()

    def _update_sync_status(self, playlist):
        """Update synchronization status display.

        Args:
            playlist: Playlist object with sync data
        """
        # Get the source platform of the playlist
        platform = getattr(playlist, "platform", "local")

        if platform == "local":
            self.sync_status_label.setText("Local playlist - can be synced to external platforms")
        else:
            # Check if we have last_synced attribute
            last_synced = getattr(playlist, "last_synced", None)
            if last_synced:
                self.sync_status_label.setText(f"Last synced with {platform.capitalize()}: {last_synced}")
            else:
                self.sync_status_label.setText(f"Source: {platform.capitalize()} - No sync history available")

    def _set_buttons_enabled(self, enabled):
        """Enable or disable all sync buttons.

        Args:
            enabled: Whether buttons should be enabled
        """
        self.sync_spotify_button.setEnabled(enabled)
        self.sync_rekordbox_button.setEnabled(enabled)
        self.sync_discogs_button.setEnabled(enabled)

    def _update_button_availability(self, playlist):
        """Update which platform buttons should be available.

        Args:
            playlist: Playlist object
        """
        # Get the source platform of the playlist
        platform = getattr(playlist, "platform", "local")

        # Disable button for source platform (can't sync to itself)
        self.sync_spotify_button.setEnabled(platform != "spotify")
        self.sync_rekordbox_button.setEnabled(platform != "rekordbox")
        self.sync_discogs_button.setEnabled(platform != "discogs")

        # YouTube doesn't support importing playlists, so no button for it
