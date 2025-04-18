import sys
from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from selecta.core.utils.type_helpers import (
    has_auth_panel,
    has_details_panel,
    has_horizontal_splitter,
    has_is_authenticated,
    has_platform_clients,
)
from selecta.ui.components.navigation_bar import NavigationBar
from selecta.ui.components.side_drawer import SideDrawer
from selecta.ui.dialogs import ImportRekordboxDialog
from selecta.ui.themes.theme_manager import Theme, ThemeManager


class SelectaMainWindow(QMainWindow):
    """Main application window for Selecta."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Selecta")
        # Set a reasonable minimum size but don't constrain maximum
        self.setMinimumSize(800, 600)

        # Resize to fill available screen space
        self.resize_to_available_screen()

        # Setup central widget and main layout
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create the navigation bar
        self.nav_bar = NavigationBar(self)
        self.main_layout.addWidget(self.nav_bar)

        # Create the content layout (below navigation bar)
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget, 1)  # 1 = stretch factor

        # Create the main splitter for left and right sides
        self.horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.horizontal_splitter.setHandleWidth(2)
        self.horizontal_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.content_layout.addWidget(self.horizontal_splitter)

        # Left side - Contains playlist on top and empty space at bottom
        self.left_widget = QWidget()
        self.left_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)

        # Create vertical splitter for playlist and bottom component
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setHandleWidth(2)
        self.vertical_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.left_layout.addWidget(self.vertical_splitter)

        # Top component for playlist
        self.playlist_container = QWidget()
        self.playlist_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(0, 0, 0, 0)

        # Bottom component (empty for now)
        self.bottom_container = QWidget()
        self.bottom_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.bottom_layout = QVBoxLayout(self.bottom_container)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Add both to vertical splitter
        self.vertical_splitter.addWidget(self.playlist_container)
        self.vertical_splitter.addWidget(self.bottom_container)

        # Set initial sizes for vertical splitter (90% for playlist, 10% for bottom)
        self.vertical_splitter.setSizes([900, 100])  # Proportional values (9:1 ratio)

        # Right side - For adaptive content
        self.right_container = QWidget()
        self.right_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Add left and right to horizontal splitter
        self.horizontal_splitter.addWidget(self.left_widget)
        self.horizontal_splitter.addWidget(self.right_container)

        # Set initial sizes for horizontal splitter (3/4 for left, 1/4 for right)
        self.horizontal_splitter.setSizes([750, 250])  # Proportional values (3:1 ratio)

        # Create the side drawer
        self.side_drawer = SideDrawer(self)
        self.side_drawer.hide()  # Hidden by default

        # Connect signals
        self.nav_bar.settings_button_clicked.connect(self.toggle_side_drawer)

        # Connect the new platform signals
        self.nav_bar.local_button_clicked.connect(lambda: self.switch_platform("local"))
        self.nav_bar.spotify_button_clicked.connect(lambda: self.switch_platform("spotify"))
        self.nav_bar.rekordbox_button_clicked.connect(lambda: self.switch_platform("rekordbox"))
        self.nav_bar.discogs_button_clicked.connect(lambda: self.switch_platform("discogs"))
        self.nav_bar.youtube_button_clicked.connect(lambda: self.switch_platform("youtube"))

        # Track the current platform
        self.current_platform = "local"

        # Initialize selection state
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()

        # Dynamic content will be created later
        self.dynamic_content = None

    def resize_to_available_screen(self):
        """Resize the window to fill the available screen space."""
        # Get the primary screen
        screen = QApplication.primaryScreen()
        if screen:
            # Get the available geometry (this accounts for taskbars, docks, etc.)
            available_geometry = screen.availableGeometry()

            # Set the window size to match the available screen space
            self.setGeometry(available_geometry)

    def resizeEvent(self, event):
        """Handle resize events to maintain splitter proportions."""
        super().resizeEvent(event)

        # Update splitter sizes when the window is resized
        if has_horizontal_splitter(self):
            # Maintain the 3:1 horizontal ratio
            total_width = self.horizontal_splitter.width()
            left_width = int(total_width * 0.75)  # 75% for left side
            right_width = total_width - left_width  # 25% for right side
            self.horizontal_splitter.setSizes([left_width, right_width])

            # For vertical splitter, prioritize the playlist section by giving it more space
            total_height = self.vertical_splitter.height()
            top_height = int(total_height * 0.9)  # 90% for top section
            bottom_height = total_height - top_height  # 10% for bottom section
            self.vertical_splitter.setSizes([top_height, bottom_height])

    def toggle_side_drawer(self):
        """Toggle the visibility of the side drawer."""
        if self.side_drawer.isVisible():
            self.side_drawer.hide_drawer()
        else:
            self.side_drawer.show_drawer()

    def set_playlist_content(self, widget):
        """Set the content widget in the playlist area."""
        # Clear the current content
        self._clear_layout(self.playlist_layout)

        # Add the new content
        self.playlist_layout.addWidget(widget)

    def set_bottom_content(self, widget):
        """Set the content widget in the bottom area."""
        # Clear the current content
        self._clear_layout(self.bottom_layout)

        # Add the new content
        self.bottom_layout.addWidget(widget)

    def set_right_content(self, widget):
        """Set the content widget in the right area."""
        # Clear the current content
        self._clear_layout(self.right_layout)

        # Add the new content
        self.right_layout.addWidget(widget)

    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        if layout is None:
            return

        # Remove all widgets from the layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def switch_platform(self, platform: str):
        """Switch to the specified platform.

        Args:
            platform: Platform name ('local', 'spotify', 'rekordbox', 'discogs')
        """
        from loguru import logger

        if platform == self.current_platform:
            # Even if it's the same platform, force a refresh to ensure
            # up-to-date authentication status
            logger.debug(f"Refreshing current platform: {platform}")
        else:
            logger.debug(f"Switching platform from {self.current_platform} to {platform}")
            self.current_platform = platform

        # Update the navigation bar
        self.nav_bar.set_active_platform(platform)

        # Store persistent client references to avoid recreating them
        if not has_platform_clients(self):
            self._platform_clients: dict[str, Any] = {}

        # Create the appropriate data provider using cached clients
        try:
            # Always recreate the client to ensure fresh authentication status
            from selecta.core.data.repositories.settings_repository import SettingsRepository

            settings_repo = SettingsRepository()

            authenticated = False
            # Use Any for now to avoid Union complexity
            data_provider: Any = None

            if platform == "local":
                from selecta.ui.components.playlist.local.local_playlist_data_provider import (
                    LocalPlaylistDataProvider,
                )

                data_provider = LocalPlaylistDataProvider()
                authenticated = True  # Local is always authenticated

            elif platform == "spotify":
                from selecta.core.platform.platform_factory import PlatformFactory
                from selecta.ui.components.playlist.spotify.spotify_playlist_data_provider import (
                    SpotifyPlaylistDataProvider,
                )

                # Recreate client to get fresh auth status
                self._platform_clients["spotify"] = PlatformFactory.create("spotify", settings_repo)
                spotify_client = self._platform_clients["spotify"]

                if spotify_client is None:
                    authenticated = False
                else:
                    spotify_provider = SpotifyPlaylistDataProvider(client=spotify_client)
                    data_provider = spotify_provider
                    if has_is_authenticated(spotify_provider.client):
                        authenticated = spotify_provider.client.is_authenticated()
                    else:
                        authenticated = False

            elif platform == "rekordbox":
                from selecta.core.platform.platform_factory import PlatformFactory
                from selecta.ui.components.playlist.rekordbox.rekordbox_playlist_data_provider import (  # noqa: E501
                    RekordboxPlaylistDataProvider,
                )

                # Recreate client to get fresh auth status
                self._platform_clients["rekordbox"] = PlatformFactory.create(
                    "rekordbox", settings_repo
                )
                rekordbox_client = self._platform_clients["rekordbox"]

                # Double-check authentication status
                authenticated = False

                if rekordbox_client is None:
                    authenticated = False
                else:
                    rekordbox_provider = RekordboxPlaylistDataProvider(client=rekordbox_client)
                    data_provider = rekordbox_provider
                    if has_is_authenticated(rekordbox_client):
                        authenticated = rekordbox_client.is_authenticated()
                    else:
                        authenticated = False

                logger.debug(f"Rekordbox authenticated: {authenticated}")

            elif platform == "discogs":
                from selecta.core.platform.platform_factory import PlatformFactory
                from selecta.ui.components.playlist.discogs.discogs_playlist_data_provider import (
                    DiscogsPlaylistDataProvider,
                )

                # Recreate client to get fresh auth status
                self._platform_clients["discogs"] = PlatformFactory.create("discogs", settings_repo)
                discogs_client = self._platform_clients["discogs"]

                if discogs_client is None:
                    authenticated = False
                else:
                    discogs_provider = DiscogsPlaylistDataProvider(client=discogs_client)
                    data_provider = discogs_provider
                    if has_is_authenticated(discogs_provider.client):
                        authenticated = discogs_provider.client.is_authenticated()
                    else:
                        authenticated = False

            elif platform == "youtube":
                from selecta.core.platform.platform_factory import PlatformFactory
                from selecta.ui.components.playlist.youtube.youtube_playlist_data_provider import (
                    YouTubePlaylistDataProvider,
                )

                # Recreate client to get fresh auth status
                self._platform_clients["youtube"] = PlatformFactory.create("youtube", settings_repo)
                youtube_client = self._platform_clients["youtube"]

                if youtube_client is None:
                    authenticated = False
                else:
                    youtube_provider = YouTubePlaylistDataProvider(client=youtube_client)
                    data_provider = youtube_provider
                    if has_is_authenticated(youtube_provider.client):
                        authenticated = youtube_provider.client.is_authenticated()
                        logger.debug(f"YouTube client authenticated: {authenticated}")
                    else:
                        authenticated = False
                        logger.debug("YouTube client doesn't have is_authenticated method")

            else:
                return  # Invalid platform

            # Check if the data provider is authenticated
            if not authenticated:
                # Show authentication message
                self._show_auth_required_message(platform)
            elif data_provider is not None:
                # Only create the playlist view if authenticated and data_provider exists
                self._create_playlist_view(data_provider)

        except Exception as e:
            from loguru import logger

            logger.exception(f"Error creating data provider for {platform}: {e}")

            # Show error message
            self._show_platform_error_message(platform, str(e))

    def _create_playlist_view(self, data_provider, is_authenticated=True):
        """Create or update the playlist view with the given data provider.

        Args:
            data_provider: The playlist data provider
            is_authenticated: Whether the platform is authenticated
        """
        from selecta.ui.components.playlist.playlist_component import PlaylistComponent

        # Check if we already have a playlist component in the playlist area
        playlist_component = None
        for i in range(self.playlist_layout.count()):
            widget = self.playlist_layout.itemAt(i).widget()
            if isinstance(widget, PlaylistComponent):
                playlist_component = widget
                break

        # Initialize audio player in the bottom section if it's not already there
        from selecta.ui.components.player.audio_player_component import AudioPlayerComponent

        # Check if we already have an audio player
        audio_player = None
        for i in range(self.bottom_layout.count()):
            widget = self.bottom_layout.itemAt(i).widget()
            if isinstance(widget, AudioPlayerComponent):
                audio_player = widget
                break

        # Create audio player if it doesn't exist
        if not audio_player:
            audio_player = AudioPlayerComponent()
            self.set_bottom_content(audio_player)
            self.audio_player = audio_player

        # If we don't have a playlist component yet, create one
        if not playlist_component:
            playlist_component = PlaylistComponent()
            self.set_playlist_content(playlist_component)

            # Make sure we have the dynamic content set up
            self._setup_search_panels()

        # Make sure the play_track signal is connected to the audio player
        # First disconnect any existing connections to avoid duplicates
        from contextlib import suppress

        with suppress(Exception):
            playlist_component.play_track.disconnect(self.audio_player.load_track)

        # Connect the signal
        playlist_component.play_track.connect(self.audio_player.load_track)

        # Update the data provider in the existing component
        playlist_component.set_data_provider(data_provider)

    def _on_track_updated(self, track_id: int):
        """Handle track updated signal from dynamic content.

        Args:
            track_id: The ID of the updated track
        """
        # Refresh the UI if needed
        self.selection_state.notify_data_changed()

    def _show_auth_required_message(self, platform: str):
        """Show a message when authentication is required.

        Args:
            platform: Platform name
        """
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        # Create a widget for the message
        auth_widget = QWidget()
        layout = QVBoxLayout(auth_widget)

        # Add message
        message = QLabel(f"Authentication required for {platform.capitalize()}.")
        message.setStyleSheet("font-size: 16px; margin-bottom: 20px;")
        layout.addWidget(message)

        # Add explanation
        explanation = QLabel(
            f"You need to authenticate with {platform.capitalize()} to view your playlists. "
            "Click the button below to authenticate."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # Add authenticate button
        auth_button = QPushButton(f"Authenticate with {platform.capitalize()}")
        auth_button.clicked.connect(lambda: self._authenticate_platform(platform))
        layout.addWidget(auth_button)

        # Add spacer
        layout.addStretch(1)

        # Set the widget as the playlist content
        self.set_playlist_content(auth_widget)

    def _authenticate_platform(self, platform: str):
        """Authenticate with the specified platform.

        Args:
            platform: Platform name
        """
        # Show the settings drawer
        self.toggle_side_drawer()

        # Find the platform auth widget in the side drawer
        if has_auth_panel(self.side_drawer):
            # Call the appropriate authentication method
            if platform == "spotify":
                self.side_drawer.auth_panel._authenticate_spotify()
                # Refresh the UI after authentication
                self.switch_platform("spotify")
            elif platform == "rekordbox":
                self.side_drawer.auth_panel._authenticate_rekordbox()
                # Refresh the UI after authentication
                self.switch_platform("rekordbox")
            elif platform == "discogs":
                self.side_drawer.auth_panel._authenticate_discogs()
                # Refresh the UI after authentication
                self.switch_platform("discogs")
            elif platform == "youtube":
                self.side_drawer.auth_panel._authenticate_youtube()
                # Refresh the UI after authentication
                self.switch_platform("youtube")

    def show_playlists(self):
        """Show playlists content for the current platform."""
        from selecta.ui.components.player.audio_player_component import AudioPlayerComponent
        from selecta.ui.components.playlist_content import PlaylistContent

        # Create playlist content
        playlist_content = PlaylistContent()
        self.set_playlist_content(playlist_content)

        # Create audio player for bottom content
        audio_player = AudioPlayerComponent()
        self.set_bottom_content(audio_player)

        # Store reference to audio player
        self.audio_player = audio_player

        # Set up the search panels if they don't exist yet
        self._setup_search_panels()

        # Store a reference to the details panel for switching later
        if has_details_panel(playlist_content):
            self.track_details_panel = playlist_content.playlist_component.details_panel

            # Connect track double-click to the audio player
            playlist_content.playlist_component.play_track.connect(self.audio_player.load_track)

        # Switch to the current platform
        self.switch_platform(getattr(self, "current_platform", "local"))

    def _setup_search_panels(self):
        """Set up the dynamic content component in the right container."""
        from selecta.ui.components.dynamic_content import DynamicContent

        # Create the dynamic content component
        self.dynamic_content = DynamicContent()

        # Set as right content instead of bottom content
        self.set_right_content(self.dynamic_content)

        # Connect signals
        self.dynamic_content.track_updated.connect(self._on_track_updated)

    def show_spotify_search(self, initial_search=None):
        """Show Spotify search panel in the right area."""
        # Make sure dynamic content is set up
        self._setup_search_panels()

        # Show spotify search panel
        if hasattr(self, "dynamic_content"):
            self.dynamic_content.show_search_panel("spotify", initial_search)

    def show_discogs_search(self, initial_search=None):
        """Show Discogs search panel in the right area."""
        # Make sure dynamic content is set up
        self._setup_search_panels()

        # Show discogs search panel
        if hasattr(self, "dynamic_content"):
            self.dynamic_content.show_search_panel("discogs", initial_search)

    def show_youtube_search(self, initial_search=None):
        """Show YouTube search panel in the right area."""
        # Make sure dynamic content is set up
        self._setup_search_panels()

        # Show YouTube search panel
        if hasattr(self, "dynamic_content"):
            self.dynamic_content.show_search_panel("youtube", initial_search)

    def show_tracks(self):
        """Show tracks content."""
        from selecta.ui.components.main_content import MainContent

        # Add main content to playlist area for now
        self.set_playlist_content(MainContent())

        # Make sure dynamic content is set up
        self._setup_search_panels()

        # Clear right side
        empty_widget = QWidget()
        self.set_right_content(empty_widget)

    def show_vinyl(self):
        """Show vinyl content."""
        from selecta.ui.components.main_content import MainContent

        # Add main content to playlist area for now
        self.set_playlist_content(MainContent())

        # Make sure dynamic content is set up
        self._setup_search_panels()

        # Clear right side
        empty_widget = QWidget()
        self.set_right_content(empty_widget)

    def _show_platform_error_message(self, platform: str, error_message: str):
        """Show an error message when there's a problem with a platform.

        Args:
            platform: Platform name
            error_message: Error message
        """
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        # Create a widget for the message
        error_widget = QWidget()
        layout = QVBoxLayout(error_widget)

        # Add message
        message = QLabel(f"Error with {platform.capitalize()} platform")
        message.setStyleSheet("font-size: 16px; margin-bottom: 20px;")
        layout.addWidget(message)

        # Add explanation
        explanation = QLabel(
            f"There was an error connecting to {platform.capitalize()}. Error: {error_message}"
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # Add try again button
        retry_button = QPushButton("Try Again")
        retry_button.clicked.connect(lambda: self.switch_platform(platform))
        layout.addWidget(retry_button)

        # Add spacer
        layout.addStretch(1)

        # Set the widget as the playlist content
        self.set_playlist_content(error_widget)

    def on_local_database_folder_changed(self, folder_path: str):
        """Handle when the local database folder is changed.

        Args:
            folder_path: The new folder path
        """
        from loguru import logger

        logger.info(f"Local database folder changed to: {folder_path}")

        # Show a notification to the user
        from PyQt6.QtWidgets import QMessageBox

        # Ask if the user wants to scan the folder now
        response = QMessageBox.question(
            self,
            "Scan Folder?",
            f"Do you want to scan the folder '{folder_path}' for music files now?\n\n"
            "This may take a while depending on the number of files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if response == QMessageBox.StandardButton.Yes:
            # Start the scanning process
            self._scan_local_database_folder(folder_path)

    def _scan_local_database_folder(self, folder_path: str):
        """Scan the local database folder for music files.

        Args:
            folder_path: Path to scan
        """
        from loguru import logger
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog

        try:
            # Create a progress dialog
            progress = QProgressDialog("Scanning folder for music files...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setWindowTitle("Scanning Music Files")
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)
            progress.show()

            # Import needed module for scanning
            import time
            from pathlib import Path

            # Start scanning
            logger.info(f"Starting scan of folder: {folder_path}")
            audio_extensions = {".mp3", ".flac", ".wav", ".aac", ".m4a", ".ogg", ".aiff"}
            folder = Path(folder_path)

            # First, count the total files to process
            # Since this might take a while, update the progress dialog
            progress.setLabelText("Counting files...")
            progress.setValue(10)

            # Process events to keep UI responsive
            from PyQt6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

            # Count files using a simplified approach to avoid traversing twice
            audio_files = [
                f
                for f in folder.glob("**/*")
                if f.is_file() and f.suffix.lower() in audio_extensions
            ]
            total_files = len(audio_files)

            if total_files == 0:
                progress.close()
                QMessageBox.information(
                    self,
                    "No Music Files Found",
                    f"No music files were found in the folder '{folder_path}'.\n\n"
                    "Please select a different folder or add music files to this folder.",
                )
                return

            # Update progress
            progress.setLabelText(f"Found {total_files} music files. Starting import...")
            progress.setValue(20)
            QCoreApplication.processEvents()

            # Simulate processing for now
            # In a real implementation, this would add each file to the database
            for i, file_path in enumerate(audio_files):
                # Check if user canceled
                if progress.wasCanceled():
                    logger.info("Scan canceled by user")
                    break

                # Update progress every 10 files to avoid too many UI updates
                if i % 10 == 0 or i == total_files - 1:
                    percent_done = 20 + int(80 * i / total_files)
                    progress.setValue(percent_done)
                    progress.setLabelText(
                        f"Processing file {i + 1} of {total_files}: {file_path.name}"
                    )
                    QCoreApplication.processEvents()

                # Simulate processing each file
                # In a real implementation, you would:
                # 1. Extract metadata from the audio file
                # 2. Create a Track record in the database
                # 3. Associate it with the correct album/artist/etc.
                time.sleep(0.01)  # Simulate a small delay for processing

            # Scan complete
            progress.setValue(100)
            progress.close()

            # Show success message
            QMessageBox.information(
                self,
                "Scan Complete",
                f"Successfully scanned {folder_path}.\n\nFound {total_files} music files.",
            )

            # Refresh the UI to show the new files
            # For now this is just a placeholder - we'll need to implement actual UI updates
            # when we integrate this with the file scanning and database functionality
            logger.info("Scan complete - UI refresh would happen here")

            # If in local platform mode, refresh the view
            if self.current_platform == "local":
                self.switch_platform("local")

        except Exception as e:
            logger.exception(f"Error scanning folder: {e}")
            QMessageBox.critical(
                self, "Scan Error", f"An error occurred while scanning the folder:\n\n{str(e)}"
            )

    def on_import_rekordbox(self):
        """Handle import from Rekordbox request."""
        from loguru import logger

        logger.info("Import from Rekordbox requested")

        # Get the local database folder
        from selecta.core.data.repositories.settings_repository import SettingsRepository

        settings_repo = SettingsRepository()
        folder_path = settings_repo.get_local_database_folder()

        if not folder_path:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "No Folder Selected",
                "Please select a local database folder before importing.",
            )
            return

        # Create and show the import dialog
        import_dialog = ImportRekordboxDialog(self)

        # Show the dialog and wait for it to close
        result = import_dialog.exec()

        if result == 1:  # QDialog.Accepted
            logger.info("Import from Rekordbox completed")

            # Refresh the UI if we're on the local platform
            if self.current_platform == "local":
                self.switch_platform("local")

    def on_import_covers(self):
        """Handle import covers from audio metadata request."""
        from loguru import logger

        logger.info("Import covers from audio files requested")

        # Get the local database folder
        from selecta.core.data.repositories.settings_repository import SettingsRepository

        settings_repo = SettingsRepository()
        folder_path = settings_repo.get_local_database_folder()

        if not folder_path:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "No Folder Selected",
                "Please select a local database folder before importing covers.",
            )
            return

        # Create and show the import dialog
        from selecta.ui.dialogs import ImportCoversDialog

        import_dialog = ImportCoversDialog(self)

        # Show the dialog and wait for it to close
        result = import_dialog.exec()

        if result == 1:  # QDialog.Accepted
            logger.info("Import covers completed")

            # Refresh the UI if we're on the local platform
            if self.current_platform == "local":
                self.switch_platform("local")


def run_app():
    """Run the PyQt application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Selecta")
    app.setOrganizationName("Looderso")

    # Apply theming
    ThemeManager.apply_theme(app, Theme.DARK)

    # Initialize PyQtToast if available
    try:
        from pyqttoast import Toast, ToastPosition

        # Set global toast settings
        Toast.setPosition(ToastPosition.BOTTOM_MIDDLE)
        Toast.setMaximumOnScreen(3)  # Max 3 toasts at once
        Toast.setSpacing(15)  # Space between toasts
        Toast.setOffset(30, 60)  # Offset from edges
        logger.info("Initialized PyQtToast for notifications")
    except ImportError:
        logger.warning("PyQtToast not available, will use fallback notifications")
    except Exception as e:
        logger.error(f"Error initializing PyQtToast: {e}")

    # Create and show the main window
    window = SelectaMainWindow()

    # Set up the initial view with local playlists
    window.switch_platform("local")

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
