from contextlib import suppress
from typing import Any

from PyQt6.QtCore import QItemSelectionModel, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.playlist.platform_icon_delegate import PlatformIconDelegate
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.track_details_panel import TrackDetailsPanel
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

        # Create stacked widget for content/loading states
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

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

        # Create tracks table
        self.tracks_table = QTableView()
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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

        # Use the shared selection state - import here to avoid circular imports
        from selecta.ui.components.selection_state import SelectionState

        self.selection_state = SelectionState()
        self.selection_state.data_changed.connect(self._on_data_changed)

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

        indexes = selection_model.selectedIndexes()
        if not indexes:
            # Clear track details if no track is selected
            self.details_panel.set_track(None)
            # Update the global selection state
            self.selection_state.set_selected_track(None)
            return

        # Get the row of the first selected index
        row = indexes[0].row()
        track = self.tracks_model.get_track(row)

        if track:
            # Update track details panel
            self.details_panel.set_track(track)

            # Update the global selection state
            self.selection_state.set_selected_track(track)

            # Emit signal with the selected track
            self.track_selected.emit(track)

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
        index = self.tracks_table.indexAt(position)
        if not index.isValid():
            return

        # Get the track at this position
        row = index.row()
        track = self.tracks_model.get_track(row)
        if not track:
            return

        # Create context menu
        menu = QMenu(self.tracks_table)

        # Add search on Spotify action
        spotify_search_action = menu.addAction("Search on Spotify")
        spotify_search_action.triggered.connect(lambda: self._search_on_spotify(track))  # type: ignore

        # Add search on Discogs action
        discogs_search_action = menu.addAction("Search on Discogs")
        discogs_search_action.triggered.connect(lambda: self._search_on_discogs(track))  # type: ignore

        # Show the menu at the cursor position
        menu.exec(self.tracks_table.viewport().mapToGlobal(position))  # type: ignore

    def _search_on_spotify(self, track: Any) -> None:
        """Search for a track on Spotify.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window to switch to the Spotify search panel
        from selecta.core.utils.type_helpers import (
            has_right_container,
            has_search_bar,
            has_show_spotify_search,
        )
        from selecta.ui.components.search_bar import SearchBar
        from selecta.ui.components.spotify.spotify_search_panel import SpotifySearchPanel

        main_window = self.window()

        # Call the show_spotify_search method on the main window
        if has_show_spotify_search(main_window):
            main_window.show_spotify_search()

            # Find the Spotify search panel in the right container
            if has_right_container(main_window):
                for i in range(main_window.right_layout.count()):
                    widget = main_window.right_layout.itemAt(i).widget()
                    if isinstance(widget, QTabWidget):
                        # The Spotify tab is at index 0
                        widget.setCurrentIndex(0)

                        # Find the Spotify search panel within the tab widget
                        spotify_panel = widget.widget(0)
                        if isinstance(spotify_panel, SpotifySearchPanel) and has_search_bar(
                            spotify_panel
                        ):
                            search_bar = spotify_panel.search_bar
                            if isinstance(search_bar, SearchBar):
                                search_bar.set_search_text(search_query)
                                spotify_panel._on_search(search_query)
                        break

    def _search_on_discogs(self, track: Any) -> None:
        """Search for a track on Discogs.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window to switch to the Discogs search panel
        from selecta.core.utils.type_helpers import (
            has_right_container,
            has_search_bar,
            has_show_discogs_search,
        )
        from selecta.ui.components.discogs.discogs_search_panel import DiscogsSearchPanel
        from selecta.ui.components.search_bar import SearchBar

        main_window = self.window()

        # Call the show_discogs_search method on the main window
        if has_show_discogs_search(main_window):
            main_window.show_discogs_search()

            # Find the Discogs search panel in the right container
            if has_right_container(main_window):
                for i in range(main_window.right_layout.count()):
                    widget = main_window.right_layout.itemAt(i).widget()
                    if isinstance(widget, QTabWidget):
                        # The Discogs tab is at index 1
                        widget.setCurrentIndex(1)

                        # Find the Discogs search panel within the tab widget
                        discogs_panel = widget.widget(1)

                        if isinstance(discogs_panel, DiscogsSearchPanel) and has_search_bar(
                            discogs_panel
                        ):
                            search_bar = discogs_panel.search_bar
                            if isinstance(search_bar, SearchBar):
                                search_bar.set_search_text(search_query)
                                discogs_panel._on_search(search_query)
                        break

    def _on_data_changed(self) -> None:
        """Handle notification that data has changed."""
        # Only refresh if we have a selected playlist
        if self.data_provider is not None and self.current_playlist_id is not None:
            self.refresh()
