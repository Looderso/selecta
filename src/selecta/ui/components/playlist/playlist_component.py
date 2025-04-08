from contextlib import suppress
from typing import Any

from loguru import logger
from PyQt6.QtCore import QItemSelectionModel, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.playlist.platform_icon_delegate import PlatformIconDelegate
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.track_details_panel import TrackDetailsPanel
from selecta.ui.components.playlist.track_quality_delegate import TrackQualityDelegate
from selecta.ui.components.playlist.tracks_table_model import TracksTableModel
from selecta.ui.components.search_bar import SearchBar


class LoadingWidget(QWidget):
    """A widget that displays a loading spinner and message."""

    def __init__(self, message: str = "Loading...", parent: QWidget | None = None) -> None:
        """Initialize the loading widget.

        Args:
            message: The message to display
            parent: Parent widget
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create spinner label
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the spinner movie
        self.spinner_movie = QMovie("resources/spinner.gif")
        if self.spinner_movie.isValid():
            self.spinner_label.setMovie(self.spinner_movie)
            self.spinner_movie.start()
        else:
            # Fallback to a text indicator
            self.spinner_label.setText("⟳")
            self.spinner_label.setStyleSheet("font-size: 48px; color: #888; margin: 10px;")

        # Create message label
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: #888; font-size: 14px; margin: 10px;")

        # Add to layout
        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_message(self, message: str) -> None:
        """Set the loading message.

        Args:
            message: The new message to display
        """
        self.message_label.setText(message)

    def showEvent(self, event: Any) -> None:
        """Handle show event.

        Args:
            event: The show event
        """
        super().showEvent(event)
        if self.spinner_movie.isValid():
            self.spinner_movie.start()

    def hideEvent(self, event: Any) -> None:
        """Handle hide event.

        Args:
            event: The hide event
        """
        if self.spinner_movie.isValid():
            self.spinner_movie.stop()
        super().hideEvent(event)


class PlaylistTreeContainer(QWidget):
    """Container for the playlist tree with loading state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the playlist tree container.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create header container for title and controls
        self.header_container = QWidget()
        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(5, 5, 5, 5)

        # Header title
        self.header_label = QLabel("Playlists")
        self.header_label.setStyleSheet("font-weight: bold;")
        self.header_layout.addWidget(self.header_label)

        # Create playlist button (hidden by default)
        self.create_button = QPushButton("+")
        self.create_button.setToolTip("Create new playlist")
        self.create_button.setFixedSize(24, 24)
        self.create_button.setVisible(False)  # Hide by default
        self.header_layout.addWidget(self.create_button)

        layout.addWidget(self.header_container)

        # Create stacked widget for content/loading states
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget, 1)  # 1 = stretch factor

        # Create tree view
        self.playlist_tree = QTreeView()
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.setExpandsOnDoubleClick(True)
        self.playlist_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.playlist_tree.setMinimumWidth(200)
        self.playlist_tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Create loading widget
        self.loading_widget = LoadingWidget("Loading playlists...")

        # Add both to stacked widget
        self.stacked_widget.addWidget(self.playlist_tree)
        self.stacked_widget.addWidget(self.loading_widget)

        # Show tree view by default
        self.stacked_widget.setCurrentWidget(self.playlist_tree)

    def show_loading(self, message: str = "Loading playlists...") -> None:
        """Show loading state.

        Args:
            message: Loading message to display
        """
        self.loading_widget.set_message(message)
        self.stacked_widget.setCurrentWidget(self.loading_widget)

    def hide_loading(self) -> None:
        """Hide loading state and show tree view."""
        self.stacked_widget.setCurrentWidget(self.playlist_tree)

    def set_platform_name(self, name: str) -> None:
        """Set the platform name in the header.

        Args:
            name: Platform name to display
        """
        self.header_label.setText(f"{name} Playlists")

    def show_create_button(self, visible: bool = True) -> None:
        """Show or hide the create playlist button.

        Args:
            visible: Whether to show the button
        """
        self.create_button.setVisible(visible)


class TrackListContainer(QWidget):
    """Container for the track list with loading state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the track list container.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Create layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Header container with playlist info and search bar
        self.header_container = QWidget()
        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(5, 5, 5, 5)

        # Header with playlist info
        self.playlist_header = QLabel("Select a playlist")
        self.playlist_header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        self.header_layout.addWidget(self.playlist_header)

        # Add search bar
        self.search_bar = SearchBar(placeholder_text="Search in playlist...")
        self.header_layout.addWidget(self.search_bar, 1)  # 1 = stretch factor

        self._layout.addWidget(self.header_container)

        # Create stacked widget for content/loading states
        self.stacked_widget = QStackedWidget()
        self._layout.addWidget(self.stacked_widget, 1)  # 1 = stretch factor

        # Create tracks table with multi-selection enabled
        self.tracks_table = QTableView()
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )  # Enable multi-selection
        self.tracks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore
        self.tracks_table.verticalHeader().setVisible(False)  # type: ignore
        self.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create loading widget
        self.loading_widget = LoadingWidget("Loading tracks...")

        # Create message widget for displaying messages
        self.message_container = QWidget()
        message_layout = QVBoxLayout(self.message_container)
        message_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label = QLabel("Select a playlist")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: #888; font-size: 16px; margin: 20px;")
        message_layout.addWidget(self.message_label)

        # Add all to stacked widget
        self.stacked_widget.addWidget(self.tracks_table)
        self.stacked_widget.addWidget(self.loading_widget)
        self.stacked_widget.addWidget(self.message_container)

        # Show message by default
        self.stacked_widget.setCurrentWidget(self.message_container)

    def show_loading(self, message: str = "Loading tracks...") -> None:
        """Show loading state.

        Args:
            message: Loading message to display
        """
        self.loading_widget.set_message(message)
        self.stacked_widget.setCurrentWidget(self.loading_widget)

    def hide_loading(self) -> None:
        """Hide loading state and show tracks table."""
        self.stacked_widget.setCurrentWidget(self.tracks_table)

    def show_message(self, message: str) -> None:
        """Show a message.

        Args:
            message: Message to display
        """
        self.message_label.setText(message)
        self.stacked_widget.setCurrentWidget(self.message_container)


class PlaylistComponent(QWidget):
    """A component for displaying and navigating playlists."""

    playlist_selected = pyqtSignal(object)  # Emits the selected playlist item
    track_selected = pyqtSignal(object)  # Emits the selected track item

    def __init__(
        self, data_provider: PlaylistDataProvider | None = None, parent: QWidget | None = None
    ) -> None:
        """Initialize the playlist component.

        Args:
            data_provider: Provider for playlist data (can be set later with set_data_provider)
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize instance variables
        self.data_provider: PlaylistDataProvider | None = None
        self.current_playlist_id: int | None = None
        self.current_tracks: list[Any] = []  # Store current tracks for search suggestions

        # Create the details panel but don't add it to our layout
        # It will be managed by the main window
        self.details_panel = TrackDetailsPanel()
        self.details_panel.setMinimumWidth(250)  # Ensure details panel has a reasonable width

        # Connect the quality changed signal directly in the constructor
        logger.debug("Connecting quality_changed signal in constructor")
        self.details_panel.quality_changed.connect(self._on_track_quality_changed)

        # Use the shared selection state - import here to avoid circular imports
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()
        self.selection_state.data_changed.connect(self._on_data_changed)
        self.selection_state.track_updated.connect(self._on_track_updated)

        # Set up the UI
        self._setup_ui()
        self._connect_signals()

        # If a data provider was given, initialize with it
        if data_provider:
            self.set_data_provider(data_provider)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Set our widget to expand both horizontally and vertically
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create a splitter to allow resizing
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create playlist tree container (left side)
        self.playlist_container = PlaylistTreeContainer()
        self.playlist_tree = self.playlist_container.playlist_tree

        # Create model for the playlist tree
        self.playlist_model = PlaylistTreeModel()
        self.playlist_tree.setModel(self.playlist_model)

        # Set context menu for playlist tree
        self.playlist_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_tree.customContextMenuRequested.connect(self._show_playlist_context_menu)

        # Create track list container (right side)
        self.track_container = TrackListContainer()
        self.tracks_table = self.track_container.tracks_table
        self.playlist_header = self.track_container.playlist_header
        self.search_bar = self.track_container.search_bar

        # Create model for the tracks table
        self.tracks_model = TracksTableModel()
        self.tracks_table.setModel(self.tracks_model)

        # Set custom delegate for the platforms column
        platforms_column_index = (
            self.tracks_model.column_keys.index("platforms")
            if "platforms" in self.tracks_model.column_keys
            else -1
        )
        if platforms_column_index >= 0:
            self.tracks_table.setItemDelegateForColumn(
                platforms_column_index, PlatformIconDelegate(self.tracks_table)
            )

        # Set custom delegate for the quality column
        quality_column_index = (
            self.tracks_model.column_keys.index("quality")
            if "quality" in self.tracks_model.column_keys
            else -1
        )
        if quality_column_index >= 0:
            self.tracks_table.setItemDelegateForColumn(
                quality_column_index, TrackQualityDelegate(self.tracks_table)
            )

        # Set context menu for tracks table
        self.tracks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_table.customContextMenuRequested.connect(self._show_track_context_menu)

        # Add containers to splitter
        self.splitter.addWidget(self.playlist_container)
        self.splitter.addWidget(self.track_container)

        # Add the splitter to the main layout
        layout.addWidget(self.splitter)

        # Set the desired proportions once the widget is shown
        QTimer.singleShot(0, self._apply_splitter_ratio)

    def _apply_splitter_ratio(self) -> None:
        """Apply the desired ratio to the splitter after widget initialization."""
        # Get the total width
        total_width = self.splitter.width()

        # Calculate sizes based on desired ratio (1:3)
        left_width = int(total_width * 0.25)  # 25% for playlist tree
        middle_width = total_width - left_width  # Remaining 75% for track list

        # Apply the sizes
        self.splitter.setSizes([left_width, middle_width])

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # When a playlist is selected, load its tracks
        playlist_tree_selection_model = self.playlist_tree.selectionModel()
        if playlist_tree_selection_model:
            playlist_tree_selection_model.selectionChanged.connect(self._on_playlist_selected)
        else:
            raise ValueError("Playlist tree selection model not available!")

        tracks_table_selection_model = self.tracks_table.selectionModel()
        if tracks_table_selection_model:
            tracks_table_selection_model.selectionChanged.connect(self._on_track_selected)
        else:
            raise ValueError("Track table selection model not available!")

        # Connect search bar signals
        self.search_bar.search_confirmed.connect(self._on_search)

        # When a search completion is selected, find and select that track
        self.search_bar.completer_activated.connect(self._on_search_completion_selected)

        # When a search completion is highlighted, highlight that track
        self.search_bar.completer_highlighted.connect(self._on_search_completion_highlighted)

    def set_data_provider(self, data_provider: PlaylistDataProvider) -> None:
        """Set or change the data provider and load playlists.

        Args:
            data_provider: The new data provider to use
        """
        # Clear current data
        self.playlist_model.clear()
        self.tracks_model.clear()
        self.current_tracks = []
        self.current_playlist_id = None
        self.playlist_header.setText("Select a playlist")
        self.details_panel.set_track(None)

        # Show message in track area
        self.track_container.show_message("Select a playlist")

        # If we had a previous provider, unregister our refresh callback
        if self.data_provider:
            with suppress(AttributeError):
                # Some providers might not have this method
                self.data_provider.unregister_refresh_callback(self.refresh)

        # Set the new provider
        self.data_provider = data_provider

        # Update the playlist tree header with platform name
        if self.data_provider:
            platform_name = self.data_provider.get_platform_name()
            self.playlist_container.set_platform_name(platform_name)

            # Show the create button only for Local Database provider
            is_local = platform_name == "Local Database"
            self.playlist_container.show_create_button(is_local)

            # Connect create button if this is the local provider
            if is_local and hasattr(self.data_provider, "create_new_playlist"):
                self.playlist_container.create_button.clicked.disconnect() if self.playlist_container.create_button.receivers(  # noqa: E501
                    self.playlist_container.create_button.clicked
                ) > 0 else None
                self.playlist_container.create_button.clicked.connect(
                    lambda: self.data_provider.create_new_playlist(self)  # type: ignore
                )

        # Register our refresh callback with the new provider
        if self.data_provider:
            self.data_provider.register_refresh_callback(self.refresh)

            # Load playlists from the new provider
            self._load_playlists()

    def _on_search_completion_highlighted(self, text: str) -> None:
        """Handle highlighting of a search completion item.

        Args:
            text: The highlighted completion text (format: "Artist - Title")
        """
        if not text or not self.current_tracks:
            return

        # Find the track that matches the highlighted suggestion
        for track in self.current_tracks:
            track_text = f"{track.artist} - {track.title}"
            if track_text == text:
                # Find the track in the current view (might be filtered)
                for row in range(self.tracks_model.rowCount()):
                    view_track = self.tracks_model.get_track(row)
                    if view_track and view_track.track_id == track.track_id:
                        # Select this track in the table
                        index = self.tracks_model.index(row, 0)
                        self.tracks_table.selectionModel().select(  # type: ignore
                            index,
                            QItemSelectionModel.SelectionFlag.ClearAndSelect
                            | QItemSelectionModel.SelectionFlag.Rows,
                        )
                        # Scroll to the selected track
                        self.tracks_table.scrollTo(index)
                        break
                break

    def _load_playlists(self) -> None:
        """Load playlists from the data provider."""
        if not self.data_provider:
            return

        # Show loading state in the playlist tree area only
        self.playlist_container.show_loading("Loading playlists...")

        def load_playlists_task() -> list[Any]:
            if self.data_provider is None:
                return []
            return self.data_provider.get_all_playlists()

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(load_playlists_task)

        worker.signals.result.connect(self._handle_playlists_loaded)
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to load playlists", err)
        )
        worker.signals.finished.connect(lambda: self.playlist_container.hide_loading())

    def _handle_playlists_loaded(self, playlists: list[Any]) -> None:
        """Handle loaded playlists.

        Args:
            playlists: List of playlist items to display
        """
        self.playlist_model.add_items(playlists)
        self._expand_all_folders()

    def _handle_loading_error(self, context: str, error_msg: str) -> None:
        """Handle loading errors.

        Args:
            context: Description of the operation that failed
            error_msg: The error message
        """
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(self, "Loading Error", f"{context}: {error_msg}")

        # Hide all loading indicators
        self.playlist_container.hide_loading()
        self.track_container.hide_loading()

    def _expand_all_folders(self) -> None:
        """Expand all folder items in the tree view."""

        def expand_recurse(parent_index: Any) -> None:
            for row in range(self.playlist_model.rowCount(parent_index)):
                index = self.playlist_model.index(row, 0, parent_index)
                item = index.internalPointer()

                if item.is_folder():
                    self.playlist_tree.expand(index)
                    expand_recurse(index)

        expand_recurse(self.playlist_tree.rootIndex())

    def _on_playlist_selected(self) -> None:
        """Handle playlist selection."""
        if not self.data_provider:
            return

        selection_model = self.playlist_tree.selectionModel()
        if selection_model is None:
            return

        indexes = selection_model.selectedIndexes()
        if not indexes:
            return

        index = indexes[0]
        item = index.internalPointer()

        # Update the global selection state
        self.selection_state.set_selected_playlist(item)

        # If it's a folder, don't load tracks
        if item.is_folder():
            self.playlist_header.setText(f"Folder: {item.name}")
            self.tracks_model.clear()
            self.details_panel.set_track(None)
            self.search_bar.set_completion_items(None)
            self.current_tracks = []
            self.track_container.show_message("This is a folder. Select a playlist to view tracks.")
            return

        # Load tracks for the selected playlist in background
        self.current_playlist_id = item.item_id
        self.playlist_header.setText(f"Loading playlist: {item.name}...")

        # Show loading state only in the track table area
        self.track_container.show_loading(f"Loading tracks for {item.name}...")

        def load_tracks_task() -> list[Any]:
            if self.data_provider is None:
                return []
            return self.data_provider.get_playlist_tracks(item.item_id)

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(load_tracks_task)

        worker.signals.result.connect(lambda tracks: self._handle_tracks_loaded(item, tracks))
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to load tracks", err)
        )
        worker.signals.finished.connect(lambda: self.track_container.hide_loading())

    def _handle_tracks_loaded(self, playlist_item: Any, tracks: list[Any]) -> None:
        """Handle loaded tracks.

        Args:
            playlist_item: The playlist item that was selected
            tracks: List of track items to display
        """
        # Make sure the tracks view is in the right state to prevent UI freezes
        # It's important to check that we're still on the same playlist before updating
        # This prevents race conditions when switching quickly between playlists
        if playlist_item.item_id != self.current_playlist_id:
            name = playlist_item.name
            logger.debug(f"Track loading finished for {name} but another playlist is now selected")
            return

        # Clear the loading state (fixes collection loading forever bug)
        self.track_container.hide_loading()

        self.current_tracks = tracks
        self.tracks_model.set_tracks(self.current_tracks)
        self.playlist_header.setText(f"Playlist: {playlist_item.name} ({len(tracks)} tracks)")

        # Update search bar suggestions with track names
        self._update_search_suggestions()

        # Clear track details since no track is selected yet
        self.details_panel.set_track(None)

        # Emit signal with the selected playlist
        self.playlist_selected.emit(playlist_item)

        # If no tracks found, show a message
        if not tracks:
            self.track_container.show_message("This playlist is empty.")

    def _update_search_suggestions(self) -> None:
        """Update search bar suggestions with current tracks."""
        if not self.current_tracks:
            self.search_bar.set_completion_items(None)
            return

        # Format suggestions as "Artist - Title"
        suggestions = [f"{track.artist} - {track.title}" for track in self.current_tracks]
        self.search_bar.set_completion_items(suggestions)

    def _on_track_selected(self) -> None:
        """Handle track selection."""
        selection_model = self.tracks_table.selectionModel()
        if selection_model is None:
            return

        selected_indexes = selection_model.selectedRows()
        if not selected_indexes:
            # Clear track details if no track is selected
            self.details_panel.set_track(None)
            # Update the global selection state
            self.selection_state.set_selected_track(None)
            return

        # Count selected tracks
        selected_count = len(selected_indexes)

        if selected_count == 1:
            # Single selection - show track details as before
            row = selected_indexes[0].row()
            track = self.tracks_model.get_track(row)

            if track:
                # Update track details panel
                self.details_panel.set_track(track)

                # Update the global selection state
                self.selection_state.set_selected_track(track)

                # Emit signal with the selected track
                self.track_selected.emit(track)
        else:
            # Multiple tracks selected - show multi-selection info
            self.details_panel.set_track(None)
            # Could show a custom "Multiple tracks selected" message in the details panel

            # Update global selection state to clear single selection
            self.selection_state.set_selected_track(None)

    def _on_search(self, search_text: str) -> None:
        """Handle search within the playlist.

        Args:
            search_text: The search text
        """
        if not self.current_tracks:
            return

        # Always show all tracks
        self.tracks_model.set_tracks(self.current_tracks)
        self.track_container.hide_loading()  # Make sure we are showing the tracks table

        if not search_text:
            return

        # Find and select the first matching track
        search_text_lower = search_text.lower()

        for row in range(self.tracks_model.rowCount()):
            track = self.tracks_model.get_track(row)
            if track and (
                search_text_lower in track.artist.lower()
                or search_text_lower in track.title.lower()
            ):
                # Select this track
                index = self.tracks_model.index(row, 0)
                self.tracks_table.selectionModel().select(  # type: ignore
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                # Scroll to the selected track
                self.tracks_table.scrollTo(index)
                break

    def _on_search_completion_selected(self, text: str) -> None:
        """Handle selection of a search completion item.

        Args:
            text: The selected completion text (format: "Artist - Title")
        """
        if not text or not self.current_tracks:
            return

        # Find the track that matches the selected suggestion
        for track in self.current_tracks:
            track_text = f"{track.artist} - {track.title}"
            if track_text == text:
                # Find the track in the current view (might be filtered)
                for row in range(self.tracks_model.rowCount()):
                    view_track = self.tracks_model.get_track(row)
                    if view_track and view_track.track_id == track.track_id:
                        # Select this track in the table
                        index = self.tracks_model.index(row, 0)
                        self.tracks_table.selectionModel().select(  # type: ignore
                            index,
                            QItemSelectionModel.SelectionFlag.ClearAndSelect
                            | QItemSelectionModel.SelectionFlag.Rows,
                        )
                        # Scroll to the selected track
                        self.tracks_table.scrollTo(index)
                        break
                break

    def refresh(self) -> None:
        """Refresh the playlist and track data."""
        if not self.data_provider:
            return

        # Remember current selections
        current_playlist_id = self.current_playlist_id

        # Show separate loading states for each section
        self.playlist_container.show_loading("Refreshing playlists...")
        if current_playlist_id is not None:
            self.track_container.show_loading("Refreshing tracks...")

        # Run the refresh in a background thread
        def refresh_task() -> dict[str, Any]:
            if self.data_provider is None:
                return {"playlists": [], "tracks": None}

            # Reload playlists
            playlists = self.data_provider.get_all_playlists()

            # Reload tracks if a playlist was selected
            tracks = None
            if current_playlist_id is not None:
                tracks = self.data_provider.get_playlist_tracks(current_playlist_id)

            return {"playlists": playlists, "tracks": tracks}

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(refresh_task)

        worker.signals.result.connect(self._handle_refresh_complete)
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to refresh data", err)
        )
        worker.signals.finished.connect(self._handle_refresh_finished)

    def _handle_refresh_finished(self) -> None:
        """Handle completion of refresh operation."""
        # Hide loading indicators
        self.playlist_container.hide_loading()
        self.track_container.hide_loading()

    def _handle_refresh_complete(self, result: dict[str, Any]) -> None:
        """Handle data from refresh operation.

        Args:
            result: Dictionary containing playlists and tracks data
        """
        # Update playlists
        self.playlist_model.clear()
        self.playlist_model.add_items(result["playlists"])
        self._expand_all_folders()

        # Update tracks if they were loaded
        if result["tracks"] is not None:
            self.current_tracks = result["tracks"]
            self.tracks_model.set_tracks(self.current_tracks)
            self._update_search_suggestions()

            # Update the playlist header
            if self.current_playlist_id is not None:
                # Find the playlist item to get its name
                for row in range(self.playlist_model.rowCount()):
                    index = self.playlist_model.index(row, 0)
                    item = index.internalPointer()
                    if hasattr(item, "item_id") and item.item_id == self.current_playlist_id:
                        self.playlist_header.setText(
                            f"Playlist: {item.name} ({len(self.current_tracks)} tracks)"
                        )
                        break

            # If no tracks, show a message
            if not self.current_tracks:
                self.track_container.show_message("This playlist is empty.")

        # Clear track details
        self.details_panel.set_track(None)

    def _show_track_context_menu(self, position: Any) -> None:
        """Show context menu for tracks table.

        Args:
            position: Position where the context menu should be shown
        """
        # Get selected tracks
        selection_model = self.tracks_table.selectionModel()
        if not selection_model:
            return

        selected_indexes = selection_model.selectedRows()
        if not selected_indexes:
            return

        # Collect all selected tracks
        selected_tracks = []
        for index in selected_indexes:
            row = index.row()
            track = self.tracks_model.get_track(row)
            if track:
                selected_tracks.append(track)

        if not selected_tracks:
            return

        # Use the first track as a reference for single-track operations
        first_track = selected_tracks[0]

        # Create context menu
        menu = QMenu(self.tracks_table)

        # Add playlist operations for local playlists
        if self.data_provider and self.data_provider.get_platform_name() == "Local Database":
            # Get current playlist
            current_playlist_id = self.current_playlist_id

            if current_playlist_id is not None:
                # In a playlist view - add option to remove from current playlist
                remove_action = menu.addAction("Remove from current playlist")
                remove_action.triggered.connect(
                    lambda: self._remove_tracks_from_playlist(current_playlist_id, selected_tracks)
                )  # type: ignore

            # Add to playlist submenu
            add_menu = menu.addMenu("Add to playlist")

            # Get all regular (non-folder) playlists
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            try:
                all_playlists = playlist_repo.get_all()
                has_playlists = False

                for playlist in all_playlists:
                    # Skip folders and the current playlist
                    if playlist.is_folder or (
                        current_playlist_id is not None and playlist.id == current_playlist_id
                    ):
                        continue

                    has_playlists = True
                    playlist_action = add_menu.addAction(playlist.name)
                    playlist_action.triggered.connect(
                        lambda checked, pid=playlist.id: self._add_tracks_to_playlist(
                            pid, selected_tracks
                        )
                    )  # type: ignore

                if not has_playlists:
                    no_playlist_action = add_menu.addAction("No playlists available")
                    no_playlist_action.setEnabled(False)

                # Add option to create a new playlist with these tracks
                add_menu.addSeparator()
                new_playlist_action = add_menu.addAction("Create new playlist...")
                new_playlist_action.triggered.connect(
                    lambda: self._create_playlist_with_tracks(selected_tracks)
                )  # type: ignore

            except Exception as e:
                logger.exception(f"Error getting playlists for context menu: {e}")

            menu.addSeparator()

        # Add search actions (only enabled for single track)
        is_single_track = len(selected_tracks) == 1

        # Add search on Spotify action
        spotify_search_action = menu.addAction("Search on Spotify")
        spotify_search_action.setEnabled(is_single_track)
        spotify_search_action.triggered.connect(lambda: self._search_on_spotify(first_track))  # type: ignore

        # Add search on Discogs action
        discogs_search_action = menu.addAction("Search on Discogs")
        discogs_search_action.setEnabled(is_single_track)
        discogs_search_action.triggered.connect(lambda: self._search_on_discogs(first_track))  # type: ignore

        # Add search on YouTube action
        youtube_search_action = menu.addAction("Search on YouTube")
        youtube_search_action.setEnabled(is_single_track)
        youtube_search_action.triggered.connect(lambda: self._search_on_youtube(first_track))  # type: ignore

        # Show the menu at the cursor position
        menu.exec(self.tracks_table.viewport().mapToGlobal(position))  # type: ignore

    def _show_playlist_context_menu(self, position: Any) -> None:
        """Show context menu for playlist tree.

        Args:
            position: Position where the context menu should be shown
        """
        # Override this method in the data provider to show appropriate context menu
        # based on if it's a local playlist or platform playlist
        if self.data_provider:
            self.data_provider.show_playlist_context_menu(self.playlist_tree, position)

    def _search_on_spotify(self, track: Any) -> None:
        """Search for a track on Spotify.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window
        main_window = self.window()

        # Call the show_spotify_search method on the main window
        if hasattr(main_window, "show_spotify_search"):
            main_window.show_spotify_search(search_query)

    def _search_on_discogs(self, track: Any) -> None:
        """Search for a track on Discogs.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window
        main_window = self.window()

        # Call the show_discogs_search method on the main window
        if hasattr(main_window, "show_discogs_search"):
            main_window.show_discogs_search(search_query)

    def _search_on_youtube(self, track: Any) -> None:
        """Search for a track on YouTube.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window
        main_window = self.window()

        # Call the show_youtube_search method on the main window
        if hasattr(main_window, "show_youtube_search"):
            main_window.show_youtube_search(search_query)

    @pyqtSlot(int, int)
    def _on_track_quality_changed(self, track_id: int, quality: int) -> None:
        """Handle quality rating changes from the details panel.

        Args:
            track_id: The track ID
            quality: The new quality rating
        """
        logger.debug(
            f"Playlist component received quality_changed signal: "
            f"track_id={track_id}, quality={quality}"
        )

        if not track_id:
            logger.warning("Invalid track ID, ignoring quality change")
            return

        # Update the track quality in the database
        from selecta.core.data.database import get_session

        # Create a track repository
        session = get_session()
        track_repo = TrackRepository(session)

        logger.info(f"Updating quality in database: track_id={track_id}, quality={quality}")
        # Set the track quality
        success = track_repo.set_track_quality(track_id, quality)

        if success:
            logger.info("Quality update successful")

            # Use our dedicated method to update the track quality in the model
            updated = self.tracks_model.update_track_quality(track_id, quality)

            if updated:
                logger.debug(f"Updated track {track_id} quality in model to {quality}")
            else:
                logger.warning(f"Could not find track {track_id} in the current model")
                logger.debug("Falling back to full refresh")
                self.refresh()
        else:
            logger.error(f"Quality update failed for track {track_id}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Quality Update Failed",
                f"Failed to update quality rating for track {track_id}.",
            )

    def _on_data_changed(self) -> None:
        """Handle notification that data has changed."""
        # Only refresh if we have a selected playlist
        if self.data_provider is not None and self.current_playlist_id is not None:
            self.refresh()

    def _on_track_updated(self, track_id: int) -> None:
        """Handle notification that a specific track has been updated.

        Args:
            track_id: The ID of the track that was updated
        """
        logger.debug(f"Playlist component handling track update for track_id={track_id}")

        # Check if we need to update our view
        if self.tracks_model:
            # Try to update just this track in the model
            updated = self.tracks_model.update_track_quality(track_id, None)

            if not updated and self.current_playlist_id is not None:
                # If the track isn't in our current view, we'll do a targeted refresh
                # of the current playlist's tracks instead of a full refresh
                self._refresh_current_playlist_tracks()

    def _refresh_current_playlist_tracks(self) -> None:
        """Refresh only the tracks for the current playlist."""
        if not self.data_provider or self.current_playlist_id is None:
            return

        # Show loading state for tracks
        self.track_container.show_loading("Refreshing tracks...")

        # Run the refresh in a background thread
        def refresh_tracks_task() -> list[Any]:
            if self.data_provider is None:
                return []

            # Just reload the tracks for the current playlist
            return self.data_provider.get_playlist_tracks(self.current_playlist_id)

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(refresh_tracks_task)

        worker.signals.result.connect(self._handle_tracks_refreshed)
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to refresh tracks", err)
        )
        worker.signals.finished.connect(lambda: self.track_container.hide_loading())

    def _handle_tracks_refreshed(self, tracks: list[Any]) -> None:
        """Handle refreshed tracks for the current playlist.

        Args:
            tracks: The refreshed list of tracks
        """
        if not tracks:
            self.track_container.show_message("This playlist is empty.")
            return

        # Update our model with the refreshed tracks
        self.current_tracks = tracks
        self.tracks_model.set_tracks(self.current_tracks)

        # Update search suggestions
        self._update_search_suggestions()

    def _add_tracks_to_playlist(self, playlist_id: int, tracks: list[Any]) -> None:
        """Add selected tracks to a playlist.

        Args:
            playlist_id: The ID of the playlist to add tracks to
            tracks: List of track objects to add
        """
        if not tracks:
            return

        try:
            # Create a repository instance
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            # Get the playlist
            playlist = playlist_repo.get_by_id(playlist_id)
            if not playlist:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.critical(self, "Error", f"Playlist with ID {playlist_id} not found.")
                return

            # Track counters
            added_count = 0
            already_exists_count = 0

            # Add each track to the playlist
            for track in tracks:
                try:
                    # Check if the track is already in the playlist
                    is_in_playlist = False
                    for pt in playlist.tracks:
                        if pt.track_id == track.track_id:
                            is_in_playlist = True
                            already_exists_count += 1
                            break

                    if not is_in_playlist:
                        playlist_repo.add_track(playlist.id, track.track_id)
                        added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add track {track.track_id} to playlist: {e}")

            # Commit changes
            session.commit()

            # Show success message
            from PyQt6.QtWidgets import QMessageBox

            if added_count > 0:
                message = (
                    f"Added {added_count} track{'s' if added_count > 1 else ''} "
                    f"to playlist '{playlist.name}'."
                )
                if already_exists_count > 0:
                    message += f"\n{already_exists_count} track{'s' if already_exists_count > 1 else ''} already in playlist."  # noqa: E501

                QMessageBox.information(self, "Tracks Added", message)
            else:
                QMessageBox.information(
                    self,
                    "No Tracks Added",
                    f"All {already_exists_count} track{'s' if already_exists_count > 1 else ''} already exist in playlist '{playlist.name}'.",  # noqa: E501
                )

            # Refresh if this is the currently displayed playlist
            if self.current_playlist_id == playlist_id:
                self.refresh()

        except Exception as e:
            logger.exception(f"Error adding tracks to playlist: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to add tracks to playlist: {str(e)}")

    def _remove_tracks_from_playlist(self, playlist_id: int, tracks: list[Any]) -> None:
        """Remove selected tracks from a playlist.

        Args:
            playlist_id: The ID of the playlist to remove tracks from
            tracks: List of track objects to remove
        """
        if not tracks:
            return

        # Confirm removal
        from PyQt6.QtWidgets import QMessageBox

        response = QMessageBox.question(
            self,
            "Remove Tracks",
            f"Are you sure you want to remove {len(tracks)} track{'s' if len(tracks) > 1 else ''} from this playlist?",  # noqa: E501
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            # Create a repository instance
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            # Get the playlist
            playlist = playlist_repo.get_by_id(playlist_id)
            if not playlist:
                QMessageBox.critical(self, "Error", f"Playlist with ID {playlist_id} not found.")
                return

            # Remove each track from the playlist
            removed_count = 0
            for track in tracks:
                try:
                    if playlist_repo.remove_track(playlist_id, track.track_id):
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove track {track.track_id} from playlist: {e}")

            # Commit changes
            session.commit()

            # Show success message
            if removed_count > 0:
                QMessageBox.information(
                    self,
                    "Tracks Removed",
                    f"Removed {removed_count} track{'s' if removed_count > 1 else ''} from playlist '{playlist.name}'.",  # noqa: E501
                )

                # Refresh the view
                self.refresh()
            else:
                QMessageBox.information(
                    self, "No Tracks Removed", "No tracks were removed from the playlist."
                )

        except Exception as e:
            logger.exception(f"Error removing tracks from playlist: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove tracks from playlist: {str(e)}")

    def _create_playlist_with_tracks(self, tracks: list[Any]) -> None:
        """Create a new playlist and add the selected tracks to it.

        Args:
            tracks: List of track objects to add to the new playlist
        """
        if not tracks:
            return

        # Import the create playlist dialog
        from selecta.core.data.models.db import Playlist
        from selecta.ui.create_playlist_dialog import CreatePlaylistDialog

        # Get all folder playlists for parent selection
        folders = []
        try:
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            all_playlists = playlist_repo.get_all()
            for pl in all_playlists:
                if pl.is_folder:
                    folders.append((pl.id, pl.name))
        except Exception as e:
            logger.warning(f"Failed to fetch folders for playlist creation: {e}")

        # Show create playlist dialog
        dialog = CreatePlaylistDialog(self, available_folders=folders)

        if dialog.exec() != CreatePlaylistDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        name = values["name"]
        is_folder = values["is_folder"]
        parent_id = values["parent_id"]

        if not name:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self, "Missing Information", "Please enter a name for the playlist."
            )
            return

        if is_folder:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Cannot Add Tracks to Folder",
                "You cannot add tracks to a folder. Please create a regular playlist instead.",
            )
            return

        try:
            # Create a repository instance
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            # Create the new playlist
            new_playlist = Playlist(
                name=name,
                is_folder=False,  # Always create as regular playlist when adding tracks
                is_local=True,
                parent_id=parent_id,
                description="",
            )

            playlist_repo.session.add(new_playlist)
            playlist_repo.session.flush()  # Get the new ID

            # Add tracks to the playlist
            added_count = 0
            for track in tracks:
                try:
                    playlist_repo.add_track(new_playlist.id, track.track_id)
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add track {track.track_id} to new playlist: {e}")

            # Commit changes
            playlist_repo.session.commit()

            # Show success message
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Playlist Created",
                f"Created playlist '{name}' with {added_count} track{'s' if added_count > 1 else ''}.",  # noqa: E501
            )

            # Refresh the view to show the new playlist
            if self.data_provider:
                self.data_provider.refresh()

        except Exception as e:
            logger.exception(f"Error creating playlist with tracks: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to create playlist: {str(e)}")
