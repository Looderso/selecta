from typing import Any

from PyQt6.QtCore import QItemSelectionModel, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.core.utils.worker import ThreadManager
from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.playlist.platform_icon_delegate import PlatformIconDelegate
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.track_details_panel import TrackDetailsPanel
from selecta.ui.components.playlist.tracks_table_model import TracksTableModel
from selecta.ui.components.search_bar import SearchBar


class PlaylistComponent(LoadableWidget):
    """A component for displaying and navigating playlists."""

    playlist_selected = pyqtSignal(object)  # Emits the selected playlist item
    track_selected = pyqtSignal(object)  # Emits the selected track item

    def __init__(self, data_provider: PlaylistDataProvider, parent: QWidget | None = None) -> None:
        """Initialize the playlist component.

        Args:
            data_provider: Provider for playlist data
            parent: Parent widget
        """
        super().__init__(parent)
        self.data_provider = data_provider
        self.data_provider.register_refresh_callback(self.refresh)

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

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget
        content_widget = QWidget()
        self.set_content_widget(content_widget)
        main_layout.addWidget(content_widget)

        # Create loading widget (will be added in show_loading)
        loading_widget = self._create_loading_widget("Loading playlists...")
        main_layout.addWidget(loading_widget)
        loading_widget.setVisible(False)

        # Setup the UI in the content widget
        self._setup_ui(content_widget)
        self._connect_signals()
        self._load_playlists()

    def _setup_ui(self, content_widget: QWidget) -> None:
        """Set up the UI components.

        Args:
            content_widget: The widget to add UI components to
        """
        layout = QHBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Set our widget to expand both horizontally and vertically
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create a splitter to allow resizing
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Left side - Playlist tree
        self.playlist_tree = QTreeView()
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.setExpandsOnDoubleClick(True)
        self.playlist_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.playlist_tree.setMinimumWidth(200)  # Ensure playlist tree has a reasonable width
        self.playlist_tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Create model for the playlist tree
        self.playlist_model = PlaylistTreeModel()
        self.playlist_tree.setModel(self.playlist_model)

        # Middle - Container for track list and header
        self.middle_container = QWidget()
        self.middle_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.middle_layout = QVBoxLayout(self.middle_container)
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)

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

        self.middle_layout.addWidget(self.header_container)

        # Tracks table
        self.tracks_table = QTableView()
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tracks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore
        self.tracks_table.verticalHeader().setVisible(False)  # type: ignore
        self.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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

        self.middle_layout.addWidget(self.tracks_table, 1)  # Add with stretch factor of 1

        self.tracks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_table.customContextMenuRequested.connect(self._show_track_context_menu)
        # Add widgets to splitter
        self.splitter.addWidget(self.playlist_tree)
        self.splitter.addWidget(self.middle_container)

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
        self.show_loading("Loading playlists...")

        def load_playlists_task() -> list[Any]:
            return self.data_provider.get_all_playlists()

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(load_playlists_task)

        worker.signals.result.connect(self._handle_playlists_loaded)
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to load playlists", err)
        )
        worker.signals.finished.connect(lambda: self.hide_loading())

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
        indexes = self.playlist_tree.selectionModel().selectedIndexes()  # type: ignore
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
            return

        # Load tracks for the selected playlist in background
        self.current_playlist_id = item.item_id
        self.playlist_header.setText(f"Loading playlist: {item.name}...")

        self.show_loading(f"Loading tracks for {item.name}...")

        def load_tracks_task() -> list[Any]:
            return self.data_provider.get_playlist_tracks(item.item_id)

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(load_tracks_task)

        worker.signals.result.connect(lambda tracks: self._handle_tracks_loaded(item, tracks))
        worker.signals.error.connect(
            lambda err: self._handle_loading_error("Failed to load tracks", err)
        )
        worker.signals.finished.connect(lambda: self.hide_loading())

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
        indexes = self.tracks_table.selectionModel().selectedIndexes()  # type: ignore
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
        # Remember current selections
        current_playlist_id = self.current_playlist_id

        # Show loading state
        self.show_loading("Refreshing playlists and tracks...")

        # Run the refresh in a background thread
        def refresh_task() -> dict[str, Any]:
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
        worker.signals.finished.connect(lambda: self.hide_loading())

    def _handle_refresh_complete(self, result: dict[str, Any]) -> None:
        """Handle completion of refresh operation.

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
        if self.current_playlist_id is not None:
            self.refresh()
