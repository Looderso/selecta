from contextlib import suppress
from typing import Any

from loguru import logger
from PyQt6.QtCore import QItemSelectionModel, QModelIndex, Qt, QTimer, pyqtSignal, pyqtSlot
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
from selecta.ui.components.playlist.icons.platform_icon_delegate import PlatformIconDelegate
from selecta.ui.components.playlist.icons.playlist_icon_delegate import PlaylistIconDelegate
from selecta.ui.components.playlist.icons.track_quality_delegate import TrackQualityDelegate
from selecta.ui.components.playlist.interfaces import IPlatformDataProvider
from selecta.ui.components.playlist.model.playlist_tree_model import PlaylistTreeModel
from selecta.ui.components.playlist.model.tracks_table_model import TracksTableModel
from selecta.ui.dialogs.collection_management_dialog import CollectionManagementDialog
from selecta.ui.widgets.loading_widget import LoadingWidget

# Import TrackDetailsPanel inside the class to avoid circular imports
from selecta.ui.widgets.search_bar import SearchBar


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

        # Create tree view with specific selection behavior settings to prevent multi-selection
        self.playlist_tree = QTreeView()
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.setExpandsOnDoubleClick(True)
        # Ensure we only allow single selection
        self.playlist_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.playlist_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

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
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Enable multi-selection
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
    play_track = pyqtSignal(object)  # Emits when track should be played
    # Removed platform-specific flag - handling should be generic for all platforms that support folders

    def __init__(self, data_provider: IPlatformDataProvider | None = None, parent: QWidget | None = None) -> None:
        """Initialize the playlist component.

        Args:
            data_provider: Provider for playlist data (can be set later with set_data_provider)
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize instance variables
        self.data_provider: IPlatformDataProvider | None = None
        self.current_playlist_id: int | None = None
        self.current_tracks: list[Any] = []  # Store current tracks for search suggestions

        # Import TrackDetailsPanel here to avoid circular imports
        from selecta.ui.components.views.track_details_panel import TrackDetailsPanel

        # Create the details panel but don't add it to our layout
        # It will be managed by the main window
        self.details_panel = TrackDetailsPanel()
        self.details_panel.setMinimumWidth(250)  # Ensure details panel has a reasonable width

        # Connect the quality changed signal directly in the constructor
        logger.debug("Connecting quality_changed signal in constructor")
        self.details_panel.quality_changed.connect(self._on_track_quality_changed)

        # Use the shared selection state - import here to avoid circular imports
        from selecta.ui.components.common.selection_state import SelectionState

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

        # Explicitly set selection mode to SingleSelection
        # This fixes an issue where clicking a playlist selects multiple items
        from PyQt6.QtWidgets import QAbstractItemView

        self.playlist_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Create model for the playlist tree
        self.playlist_model = PlaylistTreeModel()
        self.playlist_tree.setModel(self.playlist_model)

        # Set the PlaylistIconDelegate to show platform icons
        self.playlist_tree.setItemDelegate(PlaylistIconDelegate(self.playlist_tree))

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

        # Set context menu for tracks table
        self.tracks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_table.customContextMenuRequested.connect(self._show_track_context_menu)

        # Set up column delegates
        self._update_column_delegates()

        # Add containers to splitter
        self.splitter.addWidget(self.playlist_container)
        self.splitter.addWidget(self.track_container)

        # Add the splitter to the main layout
        layout.addWidget(self.splitter)

        # Set the desired proportions once the widget is shown
        QTimer.singleShot(0, self._apply_splitter_ratio)

    def _update_column_delegates(self) -> None:
        """Update the delegates for the columns in the table view.

        This should be called whenever the columns change.
        """
        # Remove any existing delegates
        for i in range(self.tracks_model.columnCount()):
            self.tracks_table.setItemDelegateForColumn(i, None)

        # Set custom delegate for the platforms column
        platforms_column_index = (
            self.tracks_model.column_keys.index("platforms") if "platforms" in self.tracks_model.column_keys else -1
        )
        if platforms_column_index >= 0:
            self.tracks_table.setItemDelegateForColumn(platforms_column_index, PlatformIconDelegate(self.tracks_table))

        # Set custom delegate for the quality column
        quality_column_index = (
            self.tracks_model.column_keys.index("quality") if "quality" in self.tracks_model.column_keys else -1
        )
        if quality_column_index >= 0:
            self.tracks_table.setItemDelegateForColumn(quality_column_index, TrackQualityDelegate(self.tracks_table))

        # Enable double-click on tracks to play them
        self.tracks_table.doubleClicked.connect(self._on_track_double_clicked)

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

        # Also connect to the clicked signal for Rekordbox-specific handling
        self.playlist_tree.clicked.connect(self._handle_tree_click)

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

    def _handle_tree_click(self, index: QModelIndex) -> None:
        """Handle clicks in the tree view for any provider with folder support.

        This ensures consistent selection behavior across all platforms with folders,
        where only a single item gets selected when clicking on a playlist item.

        Args:
            index: The index that was clicked
        """
        if not index.isValid():
            return

        # Get the item from the index
        item = index.internalPointer()
        if not item:
            return

        # Get folder status
        is_folder = item.is_folder() if hasattr(item, "is_folder") else False

        # Apply special selection handling for any platform with folders
        # Get the selection model
        selection_model = self.playlist_tree.selectionModel()
        if selection_model:
            from PyQt6.QtCore import QItemSelection, QItemSelectionModel

            # Block signals to prevent loops
            selection_model.blockSignals(True)
            selection_model.clearSelection()

            # Create a new selection with just this index
            selection = QItemSelection()
            selection.select(index, index)

            # Set the selection and current index
            selection_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.Current)
            selection_model.blockSignals(False)

            # Manually load this item if it's a valid playlist
            if not is_folder:
                # Force load the tracks for this playlist
                self.current_playlist_id = item.item_id
                self._load_playlist_tracks(item)

            # Force repaint to update selection visuals
            viewport = self.playlist_tree.viewport()
            if viewport:
                viewport.update()

            # Force processing of events to ensure the selection is updated
            from PyQt6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

    def set_data_provider(self, data_provider: IPlatformDataProvider) -> None:
        """Set or change the data provider and load playlists.

        Args:
            data_provider: The new data provider to use
        """
        # If we had a previous provider, unregister our refresh callback
        if self.data_provider:
            with suppress(AttributeError):
                # Some providers might not have this method
                self.data_provider.unregister_refresh_callback(self.refresh)

        # Set the new provider immediately to prevent race conditions
        self.data_provider = data_provider

        # Clear current data
        self.playlist_model.clear()
        self.tracks_model.clear()
        self.current_tracks = []
        self.current_playlist_id = None
        self.playlist_header.setText("Select a playlist")
        self.details_panel.set_track(None)

        # Show message in track area
        self.track_container.show_message("Select a playlist")

        # Update the playlist tree header with platform name
        if self.data_provider:
            platform_name = self.data_provider.get_platform_name()
            self.playlist_container.set_platform_name(platform_name)

            # For platforms with folders, we use a custom selection model to ensure proper selection behavior
            # Create a completely new selection model for the tree view
            from PyQt6.QtCore import QItemSelectionModel

            # Disconnect old selection model signals
            selection_model = self.playlist_tree.selectionModel()
            if selection_model:
                selection_model.selectionChanged.disconnect()

            # Create a new selection model
            new_model = QItemSelectionModel(self.playlist_model)

            # Set it as the selection model for the tree view
            self.playlist_tree.setSelectionModel(new_model)

            # Reconnect signals to the new model
            new_model.selectionChanged.connect(self._on_playlist_selected)

            # Show the create button only for Library provider
            is_library = platform_name == "Library"
            self.playlist_container.show_create_button(is_library)

            # Connect create button if this is the library provider
            if is_library and hasattr(self.data_provider, "create_new_playlist"):
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
                            QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
                        )
                        # Scroll to the selected track
                        self.tracks_table.scrollTo(index)
                        break
                break

    def _load_playlists(self) -> None:
        """Load playlists from the data provider."""
        if not self.data_provider:
            logger.warning("No data provider available - cannot load playlists")
            return

        # Log which provider we're using
        provider_name = "Unknown"
        if hasattr(self.data_provider, "get_platform_name"):
            provider_name = self.data_provider.get_platform_name()
        logger.info(f"Loading playlists from {provider_name} provider")

        # Show loading state in the playlist tree area only
        self.playlist_container.show_loading("Loading playlists...")

        def load_playlists_task() -> list[Any]:
            if self.data_provider is None:
                logger.warning("Data provider is None in playlist loading task")
                return []

            try:
                logger.debug(f"Calling get_all_playlists() on {provider_name} provider")
                playlists = self.data_provider.get_all_playlists()
                logger.debug(f"Received {len(playlists)} playlists from {provider_name} provider")
                return playlists
            except Exception as e:
                logger.error(f"Error loading playlists from {provider_name} provider: {e}")
                # Re-raise to trigger the error handler
                raise

        thread_manager = ThreadManager()
        worker = thread_manager.run_task(load_playlists_task)

        worker.signals.result.connect(self._handle_playlists_loaded)
        worker.signals.error.connect(lambda err: self._handle_loading_error("Failed to load playlists", err))
        worker.signals.finished.connect(lambda: self.playlist_container.hide_loading())

    def _handle_playlists_loaded(self, playlists: list[Any]) -> None:
        """Handle loaded playlists.

        Args:
            playlists: List of playlist items to display
        """
        logger.info(f"Handling {len(playlists)} loaded playlists")

        # Check if we have any playlists to add
        if not playlists:
            logger.warning("No playlists received from data provider")
            # Ensure loading indicator is hidden even if no playlists were found
            self.playlist_container.hide_loading()
            return

        # Log first few playlists to help diagnose issues
        if len(playlists) > 0:
            sample_count = min(3, len(playlists))
            sample_playlists = playlists[:sample_count]

            for idx, playlist in enumerate(sample_playlists):
                # Get the is_folder value from the proper method, not attribute
                is_folder_value = playlist.is_folder() if hasattr(playlist, "is_folder") else False

                playlist_info = {
                    "name": getattr(playlist, "name", "Unknown"),
                    "id": getattr(playlist, "item_id", "Unknown"),
                    "is_folder": is_folder_value,
                    "parent_id": getattr(playlist, "parent_id", None),
                    "track_count": getattr(playlist, "track_count", 0),
                }
                logger.debug(f"Sample playlist {idx+1}: {playlist_info}")

        # Call model's add_items method, which should reset the model and add these items
        logger.debug("Adding playlists to model...")
        try:
            self.playlist_model.add_items(playlists)
            logger.debug(f"Model now contains {self.playlist_model.rowCount()} root items")
        except Exception as e:
            logger.error(f"Error adding playlists to model: {e}")
            # Make sure we hide the loading indicator even if there's an error
            self.playlist_container.hide_loading()
            return

        # Expand any folders to make playlists visible
        logger.debug("Expanding all folders...")
        self._expand_all_folders()

        # Auto-select the Collection playlist if we're using the Library provider
        if (
            self.data_provider
            and hasattr(self.data_provider, "get_platform_name")
            and self.data_provider.get_platform_name() == "Library"
        ):
            logger.debug("Attempting to auto-select Collection playlist")
            # Look for the Collection playlist
            collection_found = False
            for playlist_item in playlists:
                if hasattr(playlist_item, "is_collection") and playlist_item.is_collection:
                    collection_found = True
                    logger.debug(f"Found Collection playlist with ID {playlist_item.item_id}")
                    # Find the index for this playlist
                    index_found = False
                    for row in range(self.playlist_model.rowCount()):
                        index = self.playlist_model.index(row, 0)
                        item = index.internalPointer()
                        if item and item.item_id == playlist_item.item_id:
                            # Select this playlist
                            logger.debug(f"Selecting Collection playlist at row {row}")
                            self.playlist_tree.setCurrentIndex(index)
                            index_found = True
                            # This will trigger _on_playlist_selected which will load the tracks
                            break

                    if not index_found:
                        logger.warning("Could not find Collection index in model")
                    break

            if not collection_found:
                logger.debug("No Collection playlist found to auto-select")

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

        # Reset the refreshing flag if it was set
        if hasattr(self, "_is_refreshing"):
            self._is_refreshing = False
            logger.debug("Reset refresh flag after error")

    def _expand_all_folders(self) -> None:
        """Expand all folder items in the tree view."""
        # Force the playlist tree to update right away
        self.playlist_tree.update()

        # Process any pending events to ensure UI is updated
        from PyQt6.QtCore import QCoreApplication

        QCoreApplication.processEvents()

        # Added fix for Rekordbox playlist issue
        # Check if we're using the Rekordbox provider
        if (
            self.data_provider
            and hasattr(self.data_provider, "get_platform_name")
            and self.data_provider.get_platform_name() == "Rekordbox"
        ):
            # Force manual items showing here to fix Rekordbox display issue
            self.playlist_container.hide_loading()
            self.playlist_tree.repaint()
            QCoreApplication.processEvents()

        def expand_recurse(parent_index: Any) -> None:
            rows = self.playlist_model.rowCount(parent_index)

            if rows == 0:
                return

            for row in range(rows):
                index = self.playlist_model.index(row, 0, parent_index)
                item = index.internalPointer()

                # Ensure item is valid
                if not item:
                    continue

                # Expand folders and their children
                is_folder = item.is_folder() if hasattr(item, "is_folder") else False

                if is_folder:
                    self.playlist_tree.expand(index)
                    # Process events to ensure the UI updates immediately
                    QCoreApplication.processEvents()
                    expand_recurse(index)

        # Start recursive expansion from the root
        expand_recurse(self.playlist_tree.rootIndex())

        # Ensure the playlist tree is visible
        self.playlist_container.hide_loading()
        self.playlist_tree.update()
        QCoreApplication.processEvents()

    def _load_playlist_tracks(self, item: Any) -> None:
        """Load tracks for a playlist item.

        This is a helper method that can be called directly to load tracks
        for a specific playlist item, separate from the selection callback.

        Args:
            item: The playlist item to load tracks for
        """
        if not self.data_provider or not item:
            return

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
        worker.signals.error.connect(lambda err: self._handle_loading_error("Failed to load tracks", err))
        worker.signals.finished.connect(lambda: self.track_container.hide_loading())

    def _on_playlist_selected(self) -> None:
        """Handle playlist selection."""
        if not self.data_provider:
            return

        selection_model = self.playlist_tree.selectionModel()
        if selection_model is None:
            return

        # Get the selected indexes from the selection model
        indexes = selection_model.selectedIndexes()
        if not indexes:
            return

        # For multi-selections, ensure we filter to unique indices
        if len(indexes) > 1:
            # Use internal IDs to identify unique items
            model = self.playlist_model
            unique_indices = []
            seen_internal_ids = set()

            for idx in indexes:
                # Get the internal ID for this index
                hash_key = hash((idx.internalId(), idx.row(), idx.column()))
                internal_id = model._index_internal_ids.get(hash_key, "")

                # If it has an internal ID and we haven't seen it before, add it
                if internal_id and internal_id not in seen_internal_ids:
                    seen_internal_ids.add(internal_id)
                    unique_indices.append(idx)
                # If it doesn't have an internal ID, add it anyway (fallback)
                elif not internal_id:
                    unique_indices.append(idx)

            # If we still have multiple indexes after filtering by ID, just take the first one
            if len(unique_indices) > 1:
                first_index = unique_indices[0]

                # Clear the selection and re-select only the first index
                # Using blockSignals to prevent recursive calls
                selection_model.blockSignals(True)
                selection_model.clearSelection()
                selection_model.select(
                    first_index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Current
                )
                selection_model.blockSignals(False)

                # Update our indexes list to just the first one
                indexes = [first_index]
            else:
                # We only have one unique index or none
                indexes = unique_indices

        # Ensure we have at least one index to work with
        if not indexes:
            return

        # Get the first index in our filtered list
        index = indexes[0]
        item = index.internalPointer()

        # Update the global selection state
        self.selection_state.set_selected_playlist(item)

        # Use our helper method to load tracks for this item
        self._load_playlist_tracks(item)

    def _handle_tracks_loaded(self, playlist_item: Any, tracks: list[Any]) -> None:
        """Handle loaded tracks.

        Args:
            playlist_item: The playlist item that was selected
            tracks: List of track items to display
        """
        # Make sure the tracks view is in the right state to prevent UI freezes
        # It's important to check that we're still on the same playlist before updating
        # This prevents race conditions when switching quickly between playlists
        if not hasattr(playlist_item, "item_id") or playlist_item.item_id != self.current_playlist_id:
            name = getattr(playlist_item, "name", "Unknown")
            logger.debug(f"Track loading finished for {name} but another playlist is now selected")

            # Explicitly hide loading to avoid stuck states
            self.track_container.hide_loading()

            # If necessary, force a view reset to prevent stuck state
            if self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget:
                self.track_container.show_message("Select a playlist to view tracks.")

            return

        # Clear the loading state (fixes collection loading forever bug)
        self.track_container.hide_loading()

        # Set appropriate columns based on playlist's platform type
        platform_type = "default"

        # Determine the platform type from the playlist item
        if hasattr(playlist_item, "platform_type"):
            platform_type = playlist_item.platform_type
        elif hasattr(playlist_item, "platform"):
            platform_type = playlist_item.platform
        # Special case for data providers
        elif self.data_provider and hasattr(self.data_provider, "get_platform_name"):
            platform_type = self.data_provider.get_platform_name().lower()

        # Update the table model with platform-specific columns
        self.tracks_model.set_platform(platform_type)

        # Update delegates after platform change (columns might have changed)
        self._update_column_delegates()

        # Now set the tracks
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
        else:
            # Ensure tracks table is visible if we have tracks
            logger.debug(f"Showing {len(tracks)} tracks for playlist {playlist_item.name}")

            # Force a final visual check to ensure track table is visible
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(100, lambda: self._ensure_tracks_visible())

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
            if track and (search_text_lower in track.artist.lower() or search_text_lower in track.title.lower()):
                # Select this track
                index = self.tracks_model.index(row, 0)
                self.tracks_table.selectionModel().select(  # type: ignore
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
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
                            QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
                        )
                        # Scroll to the selected track
                        self.tracks_table.scrollTo(index)
                        break
                break

    def refresh(self) -> None:
        """Refresh the playlist and track data."""
        if not self.data_provider:
            return

        # Skip if already refreshing to prevent infinite loops
        if hasattr(self, "_is_refreshing") and self._is_refreshing:
            logger.debug("Skipping refresh - already in progress")
            return

        # Skip refresh if we're already in a loading state
        if (
            self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget
            or self.playlist_container.stacked_widget.currentWidget() == self.playlist_container.loading_widget
        ):
            logger.debug("Skipping refresh - already in loading state")
            return

        # Set flag to prevent reentrant calls
        self._is_refreshing = True

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
        worker.signals.error.connect(lambda err: self._handle_loading_error("Failed to refresh data", err))
        worker.signals.finished.connect(self._handle_refresh_finished_with_cleanup)

    def _handle_refresh_finished(self) -> None:
        """Handle completion of refresh operation."""
        # Hide loading indicators
        self.playlist_container.hide_loading()
        self.track_container.hide_loading()

    def _handle_refresh_finished_with_cleanup(self) -> None:
        """Handle completion of refresh operation and reset refresh flag."""
        # Hide loading indicators with a short delay to ensure UI updates properly
        from PyQt6.QtCore import QTimer

        # First reset the refreshing flag immediately
        self._is_refreshing = False
        logger.debug("Refresh completed and flag reset")

        # Forcefully hide loading indicators immediately
        self.playlist_container.hide_loading()
        self.track_container.hide_loading()

        # If we have tracks but the loading indicator is still shown, force show tracks table
        if (
            self.current_tracks
            and self.track_container.stacked_widget.currentWidget() != self.track_container.tracks_table
        ):
            self.track_container.stacked_widget.setCurrentWidget(self.track_container.tracks_table)
            logger.debug(f"Forcing tracks table visible for {len(self.current_tracks)} tracks")

        # Then use multiple timers to ensure UI thread gets a chance to process and
        # indicators stay hidden
        QTimer.singleShot(50, lambda: self._ensure_loading_hidden())
        QTimer.singleShot(150, lambda: self._ensure_loading_hidden())
        QTimer.singleShot(300, lambda: self._ensure_loading_hidden())

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
                playlist_name = "Unknown"
                for row in range(self.playlist_model.rowCount()):
                    index = self.playlist_model.index(row, 0)
                    item = index.internalPointer()
                    if hasattr(item, "item_id") and item.item_id == self.current_playlist_id:
                        playlist_name = item.name
                        self.playlist_header.setText(f"Playlist: {playlist_name} ({len(self.current_tracks)} tracks)")
                        break

                # Make sure tracks are visible
                if self.current_tracks:
                    logger.debug(f"Showing {len(self.current_tracks)} tracks for playlist {playlist_name}")
                    self.track_container.hide_loading()
                else:
                    logger.debug(f"No tracks found for playlist {playlist_name}")
                    self.track_container.show_message("This playlist is empty.")
            else:
                # No playlist selected
                self.track_container.show_message("Select a playlist to view tracks.")

        # Clear track details
        self.details_panel.set_track(None)

        # Force UI to update
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(10, self._ensure_loading_hidden)

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

        # Get current platform
        current_platform = "unknown"
        if self.data_provider and hasattr(self.data_provider, "get_platform_name"):
            current_platform = self.data_provider.get_platform_name().lower()

        # Add playlist operations
        # Get current playlist
        current_playlist_id = self.current_playlist_id

        # Add "Add to Collection" option only for platform views (not Library)
        if current_platform != "library" and menu is not None:
            collection_action = menu.addAction("Add Selected Tracks to Collection")
            if collection_action is not None:
                collection_action.triggered.connect(lambda: self._add_tracks_to_collection(selected_tracks))  # type: ignore
            if menu is not None:
                menu.addSeparator()  # Add separator after Collection action in platform views

        # For the Library platform, add additional playlist operations
        if current_platform == "library" and current_playlist_id is not None and menu is not None:
            # In a playlist view - add option to remove from current playlist
            remove_action = menu.addAction("Remove from current playlist")
            if remove_action is not None:
                remove_action.triggered.connect(
                    lambda: self._remove_tracks_from_playlist(current_playlist_id, selected_tracks)
                )  # type: ignore

            # Add a separator before the playlist submenu
            menu.addSeparator()

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
                    # Skip folders, the current playlist, and Collection
                    # (which we handle separately)
                    if (
                        playlist.is_folder
                        or (current_playlist_id is not None and playlist.id == current_playlist_id)
                        or (hasattr(playlist, "name") and playlist.name == "Collection")
                    ):
                        continue

                    has_playlists = True
                    if add_menu is not None:
                        playlist_action = add_menu.addAction(playlist.name)
                        if playlist_action is not None:
                            playlist_action.triggered.connect(
                                lambda checked, pid=playlist.id: self._add_tracks_to_playlist(pid, selected_tracks)
                            )  # type: ignore

                if not has_playlists and add_menu is not None:
                    no_playlist_action = add_menu.addAction("No playlists available")
                    if no_playlist_action is not None:
                        no_playlist_action.setEnabled(False)

                # Add option to create a new playlist with these tracks
                if add_menu is not None:
                    add_menu.addSeparator()
                    new_playlist_action = add_menu.addAction("Create new playlist...")
                    if new_playlist_action is not None:
                        new_playlist_action.triggered.connect(
                            lambda: self._create_playlist_with_tracks(selected_tracks)
                        )  # type: ignore

            except Exception as e:
                logger.exception(f"Error getting playlists for context menu: {e}")

        # Add "Create new playlist with selected tracks" for all platforms, if not already added
        if current_platform != "library" and menu is not None:
            # Add option to create a new playlist directly
            create_playlist_action = menu.addAction("Create new playlist with selected tracks...")
            if create_playlist_action is not None:
                create_playlist_action.triggered.connect(lambda: self._create_playlist_with_tracks(selected_tracks))  # type: ignore

            menu.addSeparator()

        # Add search actions (only enabled for single track)
        is_single_track = len(selected_tracks) == 1

        # Add platform-aware search actions
        if is_single_track and menu is not None:
            # Add search on Spotify action (only if not already in Spotify view)
            if current_platform != "spotify":
                spotify_search_action = menu.addAction("Search on Spotify")
                if spotify_search_action is not None:
                    spotify_search_action.triggered.connect(lambda: self._search_on_spotify(first_track))  # type: ignore

            # Add search on Discogs action (only if not already in Discogs view)
            if current_platform != "discogs":
                discogs_search_action = menu.addAction("Search on Discogs")
                if discogs_search_action is not None:
                    discogs_search_action.triggered.connect(lambda: self._search_on_discogs(first_track))  # type: ignore

            # Add search on YouTube action (only if not already in YouTube view)
            if current_platform != "youtube":
                youtube_search_action = menu.addAction("Search on YouTube")
                if youtube_search_action is not None:
                    youtube_search_action.triggered.connect(lambda: self._search_on_youtube(first_track))  # type: ignore

            # Add search on Rekordbox action (only if not already in Rekordbox view)
            if current_platform != "rekordbox":
                rekordbox_search_action = menu.addAction("Search on Rekordbox")
                if rekordbox_search_action is not None:
                    rekordbox_search_action.setEnabled(False)  # Not implemented yet
                    # rekordbox_search_action.triggered.connect
                    # (lambda: self._search_on_rekordbox(first_track))

        # Show the menu at the cursor position
        if menu is not None and self.tracks_table is not None and self.tracks_table.viewport() is not None:
            menu.exec(self.tracks_table.viewport().mapToGlobal(position))  # type: ignore

    def _show_playlist_context_menu(self, position: Any) -> None:
        """Show context menu for playlist tree.

        Args:
            position: Position where the context menu should be shown
        """
        # If no data provider, create a minimal context menu
        if not self.data_provider:
            from PyQt6.QtWidgets import QMenu

            menu = QMenu(self.playlist_tree)

            if menu is not None:
                manage_collection_action = menu.addAction("Manage Collection...")
                if manage_collection_action is not None:
                    manage_collection_action.triggered.connect(self._show_collection_management_dialog)

                if self.playlist_tree is not None and self.playlist_tree.viewport() is not None:
                    viewport = self.playlist_tree.viewport()
                    if viewport is not None:
                        menu.exec(viewport.mapToGlobal(position))
            return

        # For all platforms that support folders, ensure consistent selection behavior
        # Get the item at the position first and ensure it's properly selected
        index = self.playlist_tree.indexAt(position)
        if index.isValid():
            # Clear any existing selection and select only this item
            selection_model = self.playlist_tree.selectionModel()
            if selection_model:
                from PyQt6.QtCore import QItemSelection, QItemSelectionModel

                # Reset selection state
                selection_model.blockSignals(True)
                selection_model.clearSelection()

                # Create a selection with just this index
                selection = QItemSelection()
                selection.select(index, index)

                # Set the selection and current index
                selection_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
                selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.Current)
                selection_model.blockSignals(False)

                # Force repaint to update selection visuals
                viewport = self.playlist_tree.viewport()
                if viewport:
                    viewport.update()

                # Force processing of events to ensure the selection is updated
                from PyQt6.QtCore import QCoreApplication

                QCoreApplication.processEvents()

        # Call the data provider's context menu handler
        try:
            if self.data_provider is not None:
                self.data_provider.show_playlist_context_menu(self.playlist_tree, position)
        except Exception as e:
            from loguru import logger

            logger.exception(f"Error showing playlist context menu: {e}")

            # Show a minimal menu in case of error
            from PyQt6.QtWidgets import QMenu

            menu = QMenu(self.playlist_tree)

            if menu is not None:
                error_action = menu.addAction("Error showing menu")
                if error_action is not None:
                    error_action.setEnabled(False)

                manage_collection_action = menu.addAction("Manage Collection...")
                if manage_collection_action is not None:
                    manage_collection_action.triggered.connect(self._show_collection_management_dialog)

                if self.playlist_tree is not None and self.playlist_tree.viewport() is not None:
                    viewport = self.playlist_tree.viewport()
                    if viewport is not None:
                        menu.exec(viewport.mapToGlobal(position))

    def _show_collection_management_dialog(self) -> None:
        """Show the Collection management dialog."""
        dialog = CollectionManagementDialog(self)

        # Connect the collection modified signal to refresh our playlist/track views
        dialog.collection_modified.connect(self.refresh)

        # Show the dialog
        dialog.exec()

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

        # Try to call the show_spotify_search method on the main window
        # The main window type is likely MainWindow from src/selecta/ui/app.py
        # Using getattr with a default to avoid attribute errors
        if main_window is not None:
            search_method = getattr(main_window, "show_spotify_search", None)
            if callable(search_method):
                search_method(search_query)

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

        # Try to call the show_discogs_search method on the main window
        if main_window is not None:
            search_method = getattr(main_window, "show_discogs_search", None)
            if callable(search_method):
                search_method(search_query)

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

        # Try to call the show_youtube_search method on the main window
        if main_window is not None:
            search_method = getattr(main_window, "show_youtube_search", None)
            if callable(search_method):
                search_method(search_query)

    @pyqtSlot(int, int)
    def _on_track_quality_changed(self, track_id: int, quality: int) -> None:
        """Handle quality rating changes from the details panel.

        Args:
            track_id: The track ID
            quality: The new quality rating
        """
        logger.debug(f"Playlist component received quality_changed signal: track_id={track_id}, quality={quality}")

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
        # Skip refresh if we're already in a loading state
        if (
            self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget
            or self.playlist_container.stacked_widget.currentWidget() == self.playlist_container.loading_widget
        ):
            logger.debug("Skipping data_changed refresh - already in loading state")
            return

        # Only refresh if we have a selected playlist
        if self.data_provider is not None and self.current_playlist_id is not None:
            # Directly execute the refresh - we already have debouncing in selection_state
            self._execute_data_changed_refresh()

    def _execute_data_changed_refresh(self) -> None:
        """Execute the actual refresh after data changes - called by timer to debounce."""
        logger.debug("Executing debounced data_changed refresh")
        self.refresh()

    def _on_track_updated(self, track_id: int) -> None:
        """Handle notification that a specific track has been updated.

        Args:
            track_id: The ID of the track that was updated
        """
        # Reduced logging
        # logger.debug(f"Playlist component handling track update for track_id={track_id}")

        # Skip update if we don't have a model or no playlist is selected
        if not self.tracks_model or self.current_playlist_id is None:
            return

        # Skip update during loading to prevent infinite refresh loops
        if self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget:
            logger.debug("Skipping track update during loading")
            return

        # Execute the update immediately without unnecessary timers
        self._execute_track_update(track_id)

    def _execute_track_update(self, track_id: int) -> None:
        """Execute the actual track update after debouncing.

        Args:
            track_id: The ID of the track to update
        """
        # Reduced logging
        # logger.debug(f"Executing debounced update for track {track_id}")

        try:
            # Force reload the track from database
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.track_repository import TrackRepository

            session = get_session()
            track_repo = TrackRepository(session)

            # Get the fresh track data with ALL updated information
            db_track = track_repo.get_by_id(track_id)
            if not db_track:
                logger.warning(f"Track {track_id} not found in database for update")
                return

            # Check if this track has been linked to any platform
            platforms = []

            # Check for platform-specific metadata
            platform_linked = False
            if hasattr(db_track, "spotify_id") and db_track.spotify_id:
                platforms.append("spotify")
                platform_linked = True

            if hasattr(db_track, "rekordbox_id") and db_track.rekordbox_id:
                platforms.append("rekordbox")
                platform_linked = True

            if hasattr(db_track, "youtube_id") and db_track.youtube_id:
                platforms.append("youtube")
                platform_linked = True

            if hasattr(db_track, "discogs_id") and db_track.discogs_id:
                platforms.append("discogs")
                platform_linked = True

            # Log the linked platforms for debugging
            if platform_linked:
                logger.debug(f"Track {track_id} is linked to platforms: {platforms}")

            # Update all tracks in the model
            track_found = False
            for i, track in enumerate(self.current_tracks):
                if hasattr(track, "track_id") and track.track_id == track_id:
                    track_found = True
                    # Replace with database track if possible
                    if hasattr(track, "_replace_with"):
                        track._replace_with(db_track)
                    else:
                        # Otherwise try updating individual fields
                        for attr in dir(db_track):
                            # Skip private attributes and methods
                            if attr.startswith("_") or callable(getattr(db_track, attr)):
                                continue

                            # Copy attribute value if it exists on both objects
                            if hasattr(track, attr):
                                setattr(track, attr, getattr(db_track, attr))

                    # Force update platform information which is most critical
                    if hasattr(track, "platforms"):
                        track.platforms = platforms

                    # Force clear cached display data
                    if hasattr(track, "_display_data"):
                        delattr(track, "_display_data")

                    # Force model to update this row
                    row_index = self.tracks_model.index(i, 0)
                    last_index = self.tracks_model.index(i, self.tracks_model.columnCount() - 1)
                    self.tracks_model.dataChanged.emit(row_index, last_index)

                    # Specifically update platforms column if it exists
                    if "platforms" in self.tracks_model.column_keys:
                        platform_col = self.tracks_model.column_keys.index("platforms")
                        platform_index = self.tracks_model.index(i, platform_col)
                        self.tracks_model.dataChanged.emit(platform_index, platform_index)

                    # Also update the details panel if this track is currently selected
                    selected_track = self.selection_state.get_selected_track()
                    if selected_track and hasattr(selected_track, "track_id") and selected_track.track_id == track_id:
                        # Update the details panel with the latest track data
                        # Reduced logging
                        # logger.debug(f"Updating details panel for track {track_id}")
                        self.details_panel.set_track(track)

                    break  # We found and updated the track

            # If track not found but platforms were updated, consider refreshing
            if not track_found and platform_linked:
                logger.debug(f"Track {track_id} not found in current view but was linked to platforms")

                # Force tracks table to be visible if we have tracks
                if (
                    self.current_tracks
                    and self.track_container.stacked_widget.currentWidget() != self.track_container.tracks_table
                ):
                    self.track_container.hide_loading()

                # Repaint all visible tracks to ensure platform icons are updated
                if self.tracks_table is not None:
                    viewport = self.tracks_table.viewport()
                    if viewport is not None:
                        viewport.update()

        except Exception as e:
            logger.error(f"Error during track update for {track_id}: {e}")
            # Fall back to a targeted refresh in case of errors
            if hasattr(self, "_refresh_current_playlist_tracks"):
                self._refresh_current_playlist_tracks()

    def _on_track_double_clicked(self, index) -> None:
        """Handle double-click on a track to play it.

        Args:
            index: The index of the clicked item
        """
        row = index.row()
        track = self.tracks_model.get_track(row)
        if track:
            # Emit signal to play the track
            self.play_track.emit(track)

    def _refresh_current_playlist_tracks(self) -> None:
        """Refresh only the tracks for the current playlist."""
        if not self.data_provider or self.current_playlist_id is None:
            return

        # Safety check - avoid refreshing if we're already loading
        if self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget:
            logger.debug("Skipping refresh - already in loading state")
            return

        # Use a debounced refresh with a timer to prevent rapid sequential refreshes
        # Add the timer as an attribute if it doesn't exist yet
        if not hasattr(self, "_refresh_timer"):
            from PyQt6.QtCore import QTimer

            self._refresh_timer = QTimer()
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.timeout.connect(self._execute_playlist_refresh)

        # Reset the timer if it's running
        if hasattr(self, "_refresh_timer") and self._refresh_timer.isActive():
            self._refresh_timer.stop()

        # Start the timer with a short delay (100ms)
        self._refresh_timer.start(100)

    def _execute_playlist_refresh(self) -> None:
        """Execute the actual playlist refresh - called by timer to debounce."""
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
        worker.signals.error.connect(lambda err: self._handle_loading_error("Failed to refresh tracks", err))
        worker.signals.finished.connect(lambda: self.track_container.hide_loading())

    def _ensure_loading_hidden(self) -> None:
        """Ensure that all loading indicators are hidden.

        This is a failsafe to recover from any state where loading indicators
        may remain visible after they should be hidden.
        """
        # Reduced loading indicators logging
        # logger.debug("Ensuring all loading indicators are hidden")
        self.playlist_container.hide_loading()
        self.track_container.hide_loading()

        # Make sure the correct widgets are visible based on state
        if not self.current_tracks:
            self.track_container.show_message("Select a playlist or refresh the view.")
        elif (
            self.current_tracks
            and self.track_container.stacked_widget.currentWidget() != self.track_container.tracks_table
        ):
            # If tracks exist but table is not visible, make it visible
            logger.debug(f"Forcing tracks table visible for {len(self.current_tracks)} tracks")
            self.track_container.stacked_widget.setCurrentWidget(self.track_container.tracks_table)

        # Force a UI update immediately without scheduling another check
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

        # Do final check immediately instead of with a timer - avoids recursive timer calls
        self._final_visibility_check()

    def _ensure_tracks_visible(self) -> None:
        """Ensure that tracks table is visible if there are tracks.

        This is a specialized method to ensure that track table is shown
        whenever tracks are loaded.
        """
        if (
            self.current_tracks
            and self.track_container.stacked_widget.currentWidget() != self.track_container.tracks_table
        ):
            logger.debug(f"Final visibility check - forcing {len(self.current_tracks)} tracks visible")
            self.track_container.stacked_widget.setCurrentWidget(self.track_container.tracks_table)

            # Force a UI update
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

    def _final_visibility_check(self) -> None:
        """Final check to ensure correct widget visibility after all operations.

        This catches any race conditions that might occur during UI updates.
        """
        # Check if tracks table should be visible but isn't
        if (
            self.current_tracks
            and self.track_container.stacked_widget.currentWidget() != self.track_container.tracks_table
            and self.track_container.stacked_widget.currentWidget() == self.track_container.loading_widget
        ):
            logger.debug("Final visibility check - forcing tracks table visible")
            self.track_container.stacked_widget.setCurrentWidget(self.track_container.tracks_table)

            # Force a UI update
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

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

        # Ensure the tracks table is visible
        self.track_container.hide_loading()

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
                message = f"Added {added_count} track{'s' if added_count > 1 else ''} to playlist '{playlist.name}'."
                if already_exists_count > 0:
                    message += (
                        f"\n{already_exists_count} track{'s' if already_exists_count > 1 else ''} already in playlist."  # noqa: E501
                    )

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
                QMessageBox.information(self, "No Tracks Removed", "No tracks were removed from the playlist.")

        except Exception as e:
            logger.exception(f"Error removing tracks from playlist: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove tracks from playlist: {str(e)}")

    def _add_tracks_to_collection(self, tracks: list[Any]) -> None:
        """Add selected tracks to the Collection playlist.

        Args:
            tracks: List of track objects to add to Collection
        """
        if not tracks:
            return

        try:
            # Get the Collection playlist
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.playlist_repository import PlaylistRepository

            session = get_session()
            playlist_repo = PlaylistRepository(session)

            # Find the Collection playlist
            collection_playlist = None
            all_playlists = playlist_repo.get_all()
            for playlist in all_playlists:
                if hasattr(playlist, "name") and playlist.name == "Collection":
                    collection_playlist = playlist
                    break

            # If Collection playlist doesn't exist, create it
            if not collection_playlist:
                playlist_data = {
                    "name": "Collection",
                    "description": "Local music collection",
                    "is_local": True,
                    "source_platform": None,
                }
                collection_playlist = playlist_repo.create(playlist_data)

            # Get current platform
            current_platform = "unknown"
            if self.data_provider and hasattr(self.data_provider, "get_platform_name"):
                current_platform = self.data_provider.get_platform_name().lower()

            # Add tracks to Collection
            from selecta.core.data.repositories.settings_repository import SettingsRepository
            from selecta.core.platform.platform_factory import PlatformFactory
            from selecta.core.platform.sync_manager import PlatformSyncManager

            # For platform tracks, we need to use the PlatformSyncManager to import them properly
            if current_platform != "library" and current_platform != "local":
                # Get the platform client
                settings_repo = SettingsRepository()
                platform_client = PlatformFactory.create(current_platform, settings_repo)

                if platform_client:
                    sync_manager = PlatformSyncManager(platform_client)

                    # Get the platform-specific track IDs
                    for track in tracks:
                        # Import the track to the local database
                        if hasattr(track, "item_id") or hasattr(track, "track_id"):
                            platform_track_id = getattr(track, "item_id", None) or getattr(track, "track_id", None)

                            if platform_track_id:
                                # Import the track to local DB
                                track_id = platform_track_id
                                local_track = sync_manager.link_manager.import_track(track_id)

                                # Add to Collection playlist
                                if local_track and local_track.id and collection_playlist:
                                    playlist_repo.add_track(collection_playlist.id, local_track.id)
            else:
                # For library tracks, just add them directly to Collection
                for track in tracks:
                    if hasattr(track, "track_id"):
                        # Check if the track is already in Collection
                        already_in_collection = False
                        collection_tracks = playlist_repo.get_playlist_tracks(collection_playlist.id)
                        for coll_track in collection_tracks:
                            if coll_track.id == track.track_id:
                                already_in_collection = True
                                break

                        # Add to Collection if not already there
                        if not already_in_collection:
                            playlist_repo.add_track(collection_playlist.id, track.track_id)

            # Show success message
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(self, "Tracks Added", f"Added {len(tracks)} tracks to Collection playlist.")

        except Exception as e:
            from loguru import logger

            logger.exception(f"Error adding tracks to Collection: {e}")

            # Show error message
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to add tracks to Collection: {str(e)}")

    def _create_playlist_with_tracks(self, tracks: list[Any]) -> None:
        """Create a new playlist and add the selected tracks to it.

        Args:
            tracks: List of track objects to add to the new playlist
        """
        if not tracks:
            return

        # Import the create playlist dialog
        from selecta.core.data.models.db import Playlist
        from selecta.ui.dialogs import CreatePlaylistDialog

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

            QMessageBox.warning(self, "Missing Information", "Please enter a name for the playlist.")
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
