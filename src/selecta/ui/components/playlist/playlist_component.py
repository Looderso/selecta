# src/selecta/ui/components/playlist/playlist_component.py

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableView,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.tracks_table_model import TracksTableModel


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

        self._setup_ui()
        self._connect_signals()
        self._load_playlists()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create a splitter to allow resizing
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Playlist tree
        self.playlist_tree = QTreeView()
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.setExpandsOnDoubleClick(True)
        self.playlist_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.playlist_tree.setMinimumWidth(200)

        # Create model for the playlist tree
        self.playlist_model = PlaylistTreeModel()
        self.playlist_tree.setModel(self.playlist_model)

        # Right side - Container for track list and header
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Header with playlist info
        self.playlist_header = QLabel("Select a playlist")
        self.playlist_header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        self.right_layout.addWidget(self.playlist_header)

        # Tracks table
        self.tracks_table = QTableView()
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tracks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tracks_table.verticalHeader().setVisible(False)

        # Create model for the tracks table
        self.tracks_model = TracksTableModel()
        self.tracks_table.setModel(self.tracks_model)

        self.right_layout.addWidget(self.tracks_table)

        # Add widgets to splitter
        self.splitter.addWidget(self.playlist_tree)
        self.splitter.addWidget(self.right_container)

        # Set default sizes (1:3 ratio)
        self.splitter.setSizes([1, 3])

        layout.addWidget(self.splitter)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # When a playlist is selected, load its tracks
        self.playlist_tree.selectionModel().selectionChanged.connect(self._on_playlist_selected)

        # When a track is selected, emit signal
        self.tracks_table.selectionModel().selectionChanged.connect(self._on_track_selected)

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
        indexes = self.playlist_tree.selectionModel().selectedIndexes()
        if not indexes:
            return

        index = indexes[0]
        item = index.internalPointer()

        # If it's a folder, don't load tracks
        if item.is_folder():
            self.playlist_header.setText(f"Folder: {item.name}")
            self.tracks_model.clear()
            return

        # Load tracks for the selected playlist
        self.current_playlist_id = item.item_id
        self.playlist_header.setText(f"Playlist: {item.name} ({item.track_count} tracks)")

        tracks = self.data_provider.get_playlist_tracks(item.item_id)
        self.tracks_model.set_tracks(tracks)

        # Emit signal with the selected playlist
        self.playlist_selected.emit(item)

    def _on_track_selected(self) -> None:
        """Handle track selection."""
        indexes = self.tracks_table.selectionModel().selectedIndexes()
        if not indexes:
            return

        # Get the row of the first selected index
        row = indexes[0].row()
        track = self.tracks_model.get_track(row)

        if track:
            # Emit signal with the selected track
            self.track_selected.emit(track)

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
            tracks = self.data_provider.get_playlist_tracks(current_playlist_id)
            self.tracks_model.set_tracks(tracks)
