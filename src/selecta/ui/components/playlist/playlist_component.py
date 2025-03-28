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
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.playlist.platform_icon_delegate import PlatformIconDelegate
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.track_details_panel import TrackDetailsPanel
from selecta.ui.components.playlist.tracks_table_model import TracksTableModel
from selecta.ui.components.search_bar import SearchBar  # Import the search bar


class PlaylistComponent(QWidget):
    """A component for displaying and navigating playlists."""

    playlist_selected = pyqtSignal(object)  # Emits the selected playlist item
    track_selected = pyqtSignal(object)  # Emits the selected track item

    def __init__(self, data_provider: PlaylistDataProvider, parent=None):
        """Initialize the playlist component.

        Args:
            data_provider: Provider for playlist data
            parent: Parent widget
        """
        super().__init__(parent)
        self.data_provider = data_provider
        self.current_playlist_id = None
        self.current_tracks = []  # Store current tracks for search suggestions

        # Create the details panel but don't add it to our layout
        # It will be managed by the main window
        self.details_panel = TrackDetailsPanel()
        self.details_panel.setMinimumWidth(250)  # Ensure details panel has a reasonable width

        self._setup_ui()
        self._connect_signals()
        self._load_playlists()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
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

    def _apply_splitter_ratio(self):
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
        playlists = self.data_provider.get_all_playlists()
        self.playlist_model.add_items(playlists)

        # Automatically expand all folders
        self._expand_all_folders()

    def _expand_all_folders(self) -> None:
        """Expand all folder items in the tree view."""

        def expand_recurse(parent_index):
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

        # If it's a folder, don't load tracks
        if item.is_folder():
            self.playlist_header.setText(f"Folder: {item.name}")
            self.tracks_model.clear()
            # Clear track details
            self.details_panel.set_track(None)
            # Clear search suggestions
            self.search_bar.set_completion_items(None)
            self.current_tracks = []
            return

        # Load tracks for the selected playlist
        self.current_playlist_id = item.item_id
        self.playlist_header.setText(f"Playlist: {item.name} ({item.track_count} tracks)")

        self.current_tracks = self.data_provider.get_playlist_tracks(item.item_id)
        self.tracks_model.set_tracks(self.current_tracks)

        # Update search bar suggestions with track names
        self._update_search_suggestions()

        # Clear track details since no track is selected yet
        self.details_panel.set_track(None)

        # Emit signal with the selected playlist
        self.playlist_selected.emit(item)

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
            return

        # Get the row of the first selected index
        row = indexes[0].row()
        track = self.tracks_model.get_track(row)

        if track:
            # Update track details panel
            self.details_panel.set_track(track)

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
        for _, track in enumerate(self.current_tracks):
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

        # Reload playlists
        self.playlist_model.clear()
        self._load_playlists()

        # Reload tracks if a playlist was selected
        if current_playlist_id is not None:
            self.current_playlist_id = current_playlist_id
            self.current_tracks = self.data_provider.get_playlist_tracks(current_playlist_id)
            self.tracks_model.set_tracks(self.current_tracks)
            self._update_search_suggestions()

            # Clear track details
            self.details_panel.set_track(None)

    def _show_track_context_menu(self, position):
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
        search_action = menu.addAction("Search on Spotify")

        search_action.triggered.connect(lambda: self._search_on_spotify(track))  # type: ignore

        # Show the menu at the cursor position
        menu.exec(self.tracks_table.viewport().mapToGlobal(position))  # type: ignore

    def _search_on_spotify(self, track):
        """Search for a track on Spotify.

        Args:
            track: The track to search for
        """
        if not track:
            return

        # Create a search query using artist and title
        search_query = f"{track.artist} {track.title}"

        # Access the main window to switch to the Spotify search panel
        main_window = self.window()

        # Call the show_spotify_search method on the main window
        # This should switch to the Spotify search panel
        if hasattr(main_window, "show_spotify_search"):
            main_window.show_spotify_search()  # type: ignore

            # Find the Spotify search panel in the right container
            if hasattr(main_window, "right_container"):
                for i in range(main_window.right_layout.count()):  # type: ignore
                    widget = main_window.right_layout.itemAt(i).widget()  # type: ignore
                    if (
                        widget
                        and isinstance(widget, QWidget)
                        and widget.objectName() == "spotifySearchPanel"
                    ):
                        # Set the search query and perform search
                        if hasattr(widget, "search_bar"):
                            widget.search_bar.set_search_text(search_query)  # type: ignore
                            widget._on_search(search_query)  # type: ignore
                        break
