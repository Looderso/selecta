"""Dialog for managing Collection tracks and detecting duplicates."""

import os

from loguru import logger
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.duplicate_detector import DuplicateDetector
from selecta.ui.themes.theme_manager import ThemeManager


class CollectionManagementDialog(QDialog):
    """Dialog for managing Collection tracks and detecting duplicates."""

    # Signal emitted when collection is modified
    collection_modified = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the Collection management dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Collection Management")
        self.setMinimumSize(QSize(900, 600))
        self.setModal(True)

        # Create duplicate detector
        self.duplicate_detector = DuplicateDetector()
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()

        # Track data
        self.potential_duplicates = []
        self.orphaned_tracks = []
        self.selected_duplicates = set()
        self.selected_orphans = set()

        # Load theme
        self.theme_manager = ThemeManager()

        # Set up UI
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Tab widget for different sections
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #2D2D30;
                color: #CCCCCC;
                padding: 8px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background-color: #3E3E42;
            }
            QTabBar::tab:selected {
                border-bottom: 2px solid #007ACC;
            }
        """)

        # Duplicates tab
        self.duplicates_tab = QWidget()
        self.tabs.addTab(self.duplicates_tab, "Duplicate Tracks")

        # Orphaned tracks tab
        self.orphans_tab = QWidget()
        self.tabs.addTab(self.orphans_tab, "Orphaned Tracks")

        # Set up each tab
        self._setup_duplicates_tab()
        self._setup_orphans_tab()

        main_layout.addWidget(self.tabs)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_current_tab)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch(1)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Connect tab change signal
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Load initial data for the first tab
        self._refresh_duplicates()

    def _setup_duplicates_tab(self):
        """Set up the Duplicates tab."""
        layout = QVBoxLayout(self.duplicates_tab)
        layout.setSpacing(10)

        # Controls section
        controls_group = QGroupBox("Duplicate Detection Controls")
        controls_layout = QHBoxLayout(controls_group)

        # Similarity threshold
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("Similarity Threshold:")
        threshold_layout.addWidget(threshold_label)

        threshold_slider_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(50)
        self.threshold_slider.setMaximum(95)
        self.threshold_slider.setValue(85)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(5)

        self.threshold_value_label = QLabel("85%")

        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)

        threshold_slider_layout.addWidget(self.threshold_slider)
        threshold_slider_layout.addWidget(self.threshold_value_label)

        threshold_layout.addLayout(threshold_slider_layout)
        controls_layout.addLayout(threshold_layout)

        # Scan button
        self.scan_duplicates_button = QPushButton("Scan for Duplicates")
        self.scan_duplicates_button.clicked.connect(self._refresh_duplicates)
        controls_layout.addWidget(self.scan_duplicates_button)

        # Merge selected button
        self.merge_selected_button = QPushButton("Merge Selected")
        self.merge_selected_button.clicked.connect(self._merge_selected_duplicates)
        self.merge_selected_button.setEnabled(False)
        controls_layout.addWidget(self.merge_selected_button)

        layout.addWidget(controls_group)

        # Duplicates table
        self.duplicates_table = QTableWidget()
        self.duplicates_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.duplicates_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.duplicates_table.setColumnCount(7)
        self.duplicates_table.setHorizontalHeaderLabels(
            ["Select", "Title", "Artist", "Album", "Duration", "Platforms", "Local Path"]
        )

        # Set up header
        header = self.duplicates_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        # Connect selection change
        self.duplicates_table.itemSelectionChanged.connect(self._on_duplicate_selection_changed)
        # Connect checkbox changes
        self.duplicates_table.itemChanged.connect(self._on_duplicate_checkbox_changed)

        layout.addWidget(self.duplicates_table)

        # Instructions
        instructions = QLabel(
            "This tab helps you find and manage potential duplicate tracks in your Collection. "
            "Adjust the similarity threshold to control how strict the duplicate detection is. "
            "Lower values find more potential duplicates but may include false positives.\n\n"
            "To merge duplicates, select the checkboxes of tracks you want to keep and "
            "click 'Merge Selected'."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #AAAAAA; font-style: italic;")
        layout.addWidget(instructions)

    def _setup_orphans_tab(self):
        """Set up the Orphaned Tracks tab."""
        layout = QVBoxLayout(self.orphans_tab)
        layout.setSpacing(10)

        # Controls section
        controls_group = QGroupBox("Orphaned Tracks Controls")
        controls_layout = QHBoxLayout(controls_group)

        # Description
        description = QLabel("Orphaned tracks are tracks in your Collection that don't appear in any other playlist.")
        description.setWordWrap(True)
        controls_layout.addWidget(description)

        # Scan button
        self.scan_orphans_button = QPushButton("Find Orphaned Tracks")
        self.scan_orphans_button.clicked.connect(self._refresh_orphans)
        controls_layout.addWidget(self.scan_orphans_button)

        # Create playlist button
        self.create_playlist_button = QPushButton("Create Playlist from Selected")
        self.create_playlist_button.clicked.connect(self._create_playlist_from_selected)
        self.create_playlist_button.setEnabled(False)
        controls_layout.addWidget(self.create_playlist_button)

        # Remove button
        self.remove_selected_button = QPushButton("Remove Selected from Collection")
        self.remove_selected_button.clicked.connect(self._remove_selected_from_collection)
        self.remove_selected_button.setEnabled(False)
        controls_layout.addWidget(self.remove_selected_button)

        layout.addWidget(controls_group)

        # Orphans table
        self.orphans_table = QTableWidget()
        self.orphans_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.orphans_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.orphans_table.setColumnCount(7)
        self.orphans_table.setHorizontalHeaderLabels(
            ["Select", "Title", "Artist", "Album", "Duration", "Platforms", "Local Path"]
        )

        # Set up header
        header = self.orphans_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        # Connect selection change
        self.orphans_table.itemSelectionChanged.connect(self._on_orphan_selection_changed)
        # Connect checkbox changes
        self.orphans_table.itemChanged.connect(self._on_orphan_checkbox_changed)

        layout.addWidget(self.orphans_table)

        # Instructions
        instructions = QLabel(
            "This tab shows tracks that exist in your Collection "
            "but don't appear in any other playlist. "
            "You can create a new playlist from selected tracks or remove them "
            "from your Collection."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #AAAAAA; font-style: italic;")
        layout.addWidget(instructions)

    def _on_threshold_changed(self, value):
        """Handle threshold slider value change.

        Args:
            value: New threshold value
        """
        self.threshold_value_label.setText(f"{value}%")

    def _on_tab_changed(self, index):
        """Handle tab change.

        Args:
            index: New tab index
        """
        if index == 0:  # Duplicates tab
            self._refresh_duplicates()
        else:  # Orphans tab
            self._refresh_orphans()

    def _refresh_current_tab(self):
        """Refresh the currently active tab."""
        current_index = self.tabs.currentIndex()
        if current_index == 0:  # Duplicates tab
            self._refresh_duplicates()
        else:  # Orphans tab
            self._refresh_orphans()

    def _refresh_duplicates(self):
        """Refresh the duplicates list."""
        # Show a progress dialog
        progress = QProgressDialog("Scanning for duplicates...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(10)

        # Clear existing data
        self.duplicates_table.setRowCount(0)
        self.duplicates_table.clearContents()
        self.potential_duplicates = []
        self.selected_duplicates.clear()
        self.merge_selected_button.setEnabled(False)

        try:
            # Get threshold value
            threshold = self.threshold_slider.value() / 100.0

            # Update progress dialog
            progress.setValue(30)
            QApplication.processEvents()

            # Find potential duplicates
            self.potential_duplicates = self.duplicate_detector.find_potential_duplicates(threshold)

            # Update progress dialog
            progress.setValue(70)
            QApplication.processEvents()

            # Populate table with duplicates
            row = 0
            for group in self.potential_duplicates:
                # Add a separator row before each group except the first
                if row > 0:
                    self.duplicates_table.insertRow(row)
                    separator_item = QTableWidgetItem("---")
                    separator_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    separator_item.setBackground(Qt.GlobalColor.darkGray)
                    self.duplicates_table.setItem(row, 1, separator_item)
                    row += 1

                # Add group items
                is_first_in_group = True
                for track in group:
                    self.duplicates_table.insertRow(row)

                    # Track ID stored as hidden data in first column
                    # Get track ID with type checking
                    track_id = track["id"] if isinstance(track, dict) and "id" in track else 0

                    # Checkbox for selection (first in group is checked by default)
                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    checkbox_item.setCheckState(Qt.CheckState.Checked if is_first_in_group else Qt.CheckState.Unchecked)
                    if is_first_in_group:
                        self.selected_duplicates.add(track_id)
                    checkbox_item.setData(Qt.ItemDataRole.UserRole, track_id)
                    self.duplicates_table.setItem(row, 0, checkbox_item)

                    # Track information with type checking
                    is_valid_dict = isinstance(track, dict)
                    # Safe dictionary access that works with type checking
                    title = track["title"] if is_valid_dict and "title" in track else ""
                    artist = track["artist"] if is_valid_dict and "artist" in track else ""
                    album = track["album"] if is_valid_dict and "album" in track else ""

                    self.duplicates_table.setItem(row, 1, QTableWidgetItem(title))
                    self.duplicates_table.setItem(row, 2, QTableWidgetItem(artist))
                    self.duplicates_table.setItem(row, 3, QTableWidgetItem(album))

                    # Duration in minutes:seconds with type checking
                    is_valid_dict = isinstance(track, dict)
                    duration_ms = track["duration_ms"] if is_valid_dict and "duration_ms" in track else 0
                    # Ensure duration_ms is an integer for division
                    is_valid_type = isinstance(duration_ms, int | float | str)
                    duration_ms_int = int(duration_ms) if is_valid_type else 0
                    minutes = duration_ms_int // 60000
                    seconds = (duration_ms_int % 60000) // 1000
                    duration_str = f"{minutes}:{seconds:02d}"
                    self.duplicates_table.setItem(row, 4, QTableWidgetItem(duration_str))

                    # Platforms with type checking
                    is_valid_dict = isinstance(track, dict)
                    platforms = track["platforms"] if is_valid_dict and "platforms" in track else []
                    is_list = isinstance(platforms, list)
                    platforms_str = ", ".join(platforms) if is_list else str(platforms)
                    self.duplicates_table.setItem(row, 5, QTableWidgetItem(platforms_str))

                    # Local path (shortened) with type checking
                    is_valid_dict = isinstance(track, dict)
                    path = track["local_path"] if is_valid_dict and "local_path" in track else ""
                    path_display = os.path.basename(path) if path else ""
                    path_item = QTableWidgetItem(path_display)
                    path_item.setToolTip(path)
                    self.duplicates_table.setItem(row, 6, QTableWidgetItem(path_display))

                    # Add similarity info for duplicate tracks with type checking
                    is_valid_dict = isinstance(track, dict)
                    has_similarity = is_valid_dict and "similarity" in track

                    if has_similarity:
                        # Access similarity with proper type checking
                        similarity = track["similarity"]
                        # Check if similarity can be converted to a number
                        try:
                            # First check if similarity is not None before conversion
                            similarity_pct = int(float(similarity) * 100) if similarity is not None else 0
                        except (ValueError, TypeError):
                            similarity_pct = 0

                        # Apply highlighting to cells
                        for col in range(1, 7):
                            item = self.duplicates_table.item(row, col)
                            if item is not None:
                                item.setToolTip(f"Similarity: {similarity_pct}%")
                                item.setBackground(
                                    Qt.GlobalColor.darkGreen if similarity_pct > 90 else Qt.GlobalColor.darkBlue
                                )

                    row += 1
                    is_first_in_group = False

            # Update merge button state
            self._update_merge_button_state()

            # Close progress dialog
            progress.setValue(100)

            # Show result message
            if self.potential_duplicates:
                self.duplicates_table.setFocus()
                QMessageBox.information(
                    self,
                    "Duplicates Found",
                    f"Found {len(self.potential_duplicates)} potential duplicate groups.",
                )
            else:
                QMessageBox.information(
                    self,
                    "No Duplicates",
                    "No potential duplicates found. Try lowering the similarity threshold.",
                )

        except Exception as e:
            logger.exception(f"Error scanning for duplicates: {e}")
            QMessageBox.critical(self, "Error", f"Failed to scan for duplicates: {str(e)}")
        finally:
            progress.close()

    def _refresh_orphans(self):
        """Refresh the orphaned tracks list."""
        # Show a progress dialog
        progress = QProgressDialog("Finding orphaned tracks...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(10)

        # Clear existing data
        self.orphans_table.setRowCount(0)
        self.orphans_table.clearContents()
        self.orphaned_tracks = []
        self.selected_orphans.clear()
        self.create_playlist_button.setEnabled(False)
        self.remove_selected_button.setEnabled(False)

        try:
            # Update progress dialog
            progress.setValue(30)
            QApplication.processEvents()

            # Find orphaned tracks
            self.orphaned_tracks = self.duplicate_detector.find_orphaned_tracks()

            # Update progress dialog
            progress.setValue(70)
            QApplication.processEvents()

            # Populate table with orphaned tracks
            for row, track in enumerate(self.orphaned_tracks):
                self.orphans_table.insertRow(row)

                # Track ID stored as hidden data in first column with type checking
                is_valid_dict = isinstance(track, dict)
                track_id = track["id"] if is_valid_dict and "id" in track else 0

                # Checkbox for selection
                checkbox_item = QTableWidgetItem()
                checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
                checkbox_item.setData(Qt.ItemDataRole.UserRole, track_id)
                self.orphans_table.setItem(row, 0, checkbox_item)

                # Track information with type checking
                title = track["title"] if is_valid_dict and "title" in track else ""
                artist = track["artist"] if is_valid_dict and "artist" in track else ""
                album = track["album"] if is_valid_dict and "album" in track else ""

                self.orphans_table.setItem(row, 1, QTableWidgetItem(title))
                self.orphans_table.setItem(row, 2, QTableWidgetItem(artist))
                self.orphans_table.setItem(row, 3, QTableWidgetItem(album))

                # Duration in minutes:seconds with type checking
                duration_ms = track["duration_ms"] if is_valid_dict and "duration_ms" in track else 0

                # Ensure duration_ms is valid for integer operations
                try:
                    duration_ms_int = int(duration_ms)
                    minutes = duration_ms_int // 60000
                    seconds = (duration_ms_int % 60000) // 1000
                    duration_str = f"{minutes}:{seconds:02d}"
                except (ValueError, TypeError):
                    duration_str = "0:00"

                self.orphans_table.setItem(row, 4, QTableWidgetItem(duration_str))

                # Platforms with type checking
                platforms = track["platforms"] if is_valid_dict and "platforms" in track else []
                is_list = isinstance(platforms, list)
                platforms_str = ", ".join(platforms) if is_list else str(platforms)
                self.orphans_table.setItem(row, 5, QTableWidgetItem(platforms_str))

                # Local path (shortened) with type checking
                path = track["local_path"] if is_valid_dict and "local_path" in track else ""
                path_display = os.path.basename(path) if path else ""
                path_item = QTableWidgetItem(path_display)
                path_item.setToolTip(path)
                self.orphans_table.setItem(row, 6, QTableWidgetItem(path_display))

            # Close progress dialog
            progress.setValue(100)

            # Show result message
            if self.orphaned_tracks:
                self.orphans_table.setFocus()
                QMessageBox.information(
                    self,
                    "Orphaned Tracks Found",
                    f"Found {len(self.orphaned_tracks)} tracks that are in your Collection "
                    f"but not in any other playlist.",
                )
            else:
                QMessageBox.information(
                    self,
                    "No Orphaned Tracks",
                    "No orphaned tracks found. " "All tracks in your Collection are in at least one playlist.",
                )

        except Exception as e:
            logger.exception(f"Error finding orphaned tracks: {e}")
            QMessageBox.critical(self, "Error", f"Failed to find orphaned tracks: {str(e)}")
        finally:
            progress.close()

    def _on_duplicate_selection_changed(self):
        """Handle selection change in duplicates table."""
        # Update merge button state
        self._update_merge_button_state()

    def _on_duplicate_checkbox_changed(self, item):
        """Handle checkbox state change in duplicates table.

        Args:
            item: Changed item
        """
        # Check if this is a checkbox item (column 0)
        if item.column() != 0:
            return

        # Get track ID
        track_id = item.data(Qt.ItemDataRole.UserRole)
        if not track_id:
            return

        # Update selected duplicates set
        if item.checkState() == Qt.CheckState.Checked:
            self.selected_duplicates.add(track_id)
        else:
            self.selected_duplicates.discard(track_id)

        # Update merge button state
        self._update_merge_button_state()

    def _on_orphan_selection_changed(self):
        """Handle selection change in orphans table."""
        # Update buttons state
        self._update_orphan_buttons_state()

    def _on_orphan_checkbox_changed(self, item):
        """Handle checkbox state change in orphans table.

        Args:
            item: Changed item
        """
        # Check if this is a checkbox item (column 0)
        if item.column() != 0:
            return

        # Get track ID
        track_id = item.data(Qt.ItemDataRole.UserRole)
        if not track_id:
            return

        # Update selected orphans set
        if item.checkState() == Qt.CheckState.Checked:
            self.selected_orphans.add(track_id)
        else:
            self.selected_orphans.discard(track_id)

        # Update buttons state
        self._update_orphan_buttons_state()

    def _update_merge_button_state(self):
        """Update the state of the merge button based on selection."""
        # Enable merge button if at least one track is selected
        self.merge_selected_button.setEnabled(len(self.selected_duplicates) > 0)

    def _update_orphan_buttons_state(self):
        """Update the state of the orphan-related buttons based on selection."""
        has_selection = len(self.selected_orphans) > 0
        self.create_playlist_button.setEnabled(has_selection)
        self.remove_selected_button.setEnabled(has_selection)

    def _merge_selected_duplicates(self):
        """Merge selected duplicate tracks."""
        # Ensure at least one track is selected
        if not self.selected_duplicates:
            QMessageBox.warning(self, "No Selection", "Please select at least one track to keep.")
            return

        # Organize tracks by group
        groups_to_merge = []
        selected_track_ids = set(self.selected_duplicates)

        # Ensure we have a list of potential duplicates before processing
        if not isinstance(self.potential_duplicates, list):
            QMessageBox.warning(self, "Error", "Invalid duplicate data structure.")
            return

        for group in self.potential_duplicates:
            # Ensure group is a list
            if not isinstance(group, list):
                continue

            # Get track IDs in this group with type checking
            group_track_ids = set()
            for track in group:
                if isinstance(track, dict) and "id" in track:
                    track_id = track["id"]
                    if track_id is not None:
                        group_track_ids.add(track_id)

            # Check if any track in this group is selected
            if group_track_ids.intersection(selected_track_ids):
                # Determine which tracks to keep and which to merge
                tracks_to_keep = []
                tracks_to_merge = []

                for track in group:
                    # Skip invalid tracks
                    if not isinstance(track, dict) or "id" not in track:
                        continue

                    track_id = track["id"]
                    if track_id in selected_track_ids:
                        tracks_to_keep.append(track)
                    else:
                        tracks_to_merge.append(track)

                # Only add to merge list if there are tracks to merge and keep
                if tracks_to_merge and tracks_to_keep:
                    groups_to_merge.append({"keep": tracks_to_keep, "merge": tracks_to_merge})

        # If no groups to merge, show message
        if not groups_to_merge:
            QMessageBox.information(
                self,
                "Nothing to Merge",
                "No tracks to merge. Please select only one track from each duplicate group.",
            )
            return

        # Confirm merge with type checking
        merge_count = sum(
            len(group["merge"])
            for group in groups_to_merge
            if isinstance(group, dict) and "merge" in group and isinstance(group["merge"], list)
        )
        keep_count = sum(
            len(group["keep"])
            for group in groups_to_merge
            if isinstance(group, dict) and "keep" in group and isinstance(group["keep"], list)
        )

        response = QMessageBox.question(
            self,
            "Confirm Merge",
            f"This will merge {merge_count} tracks into {keep_count} tracks. "
            f"The platform links and metadata from merged tracks will be preserved. "
            f"This cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Show progress dialog
        progress = QProgressDialog("Merging tracks...", "Cancel", 0, len(groups_to_merge), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)

        try:
            # Process each group
            merged_count = 0

            for i, group in enumerate(groups_to_merge):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                QApplication.processEvents()

                # Type checking for group
                is_valid_group = isinstance(group, dict)
                has_keep = is_valid_group and "keep" in group and isinstance(group["keep"], list)
                has_merge = is_valid_group and "merge" in group and isinstance(group["merge"], list)

                if not (has_keep and has_merge):
                    continue  # Skip invalid groups

                # Merge tracks in this group
                for keep_track in group["keep"]:
                    # Type check keep_track
                    is_valid_keep = isinstance(keep_track, dict) and "id" in keep_track
                    if not is_valid_keep:
                        continue

                    for merge_track in group["merge"]:
                        # Type check merge_track
                        is_valid_merge = isinstance(merge_track, dict) and "id" in merge_track
                        if not is_valid_merge:
                            continue

                        # Merge platform info
                        keep_id = keep_track["id"] if isinstance(keep_track, dict) and "id" in keep_track else 0
                        merge_id = merge_track["id"] if isinstance(merge_track, dict) and "id" in merge_track else 0

                        self._merge_track_platforms(keep_id, merge_id)

                        # Remove merged track from all playlists and add keeper track
                        self._replace_track_in_playlists(merge_id, keep_id)

                        # Mark the merged track for deletion
                        self.track_repo.update(merge_id, {"status": "deleted"})

                        merged_count += 1

            progress.setValue(len(groups_to_merge))

            # Show success message
            QMessageBox.information(
                self,
                "Merge Complete",
                f"Successfully merged {merged_count} tracks into {keep_count} tracks.",
            )

            # Emit signal that collection was modified
            self.collection_modified.emit()

            # Refresh the duplicates list
            self._refresh_duplicates()

        except Exception as e:
            logger.exception(f"Error merging tracks: {e}")
            QMessageBox.critical(self, "Merge Error", f"An error occurred during merge: {str(e)}")
        finally:
            progress.close()

    def _merge_track_platforms(self, keep_track_id: int, merge_track_id: int):
        """Merge platform information from one track to another.

        Args:
            keep_track_id: ID of the track to keep
            merge_track_id: ID of the track to merge from
        """
        try:
            # Validate inputs
            try:
                keep_track_id_int = int(keep_track_id)
                merge_track_id_int = int(merge_track_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid track IDs: keep={keep_track_id}, merge={merge_track_id}")
                return

            # Get the track to merge from
            merge_track = self.track_repo.get_by_id(merge_track_id_int)
            if merge_track is None:
                logger.warning(f"Merge track {merge_track_id_int} not found")
                return

            # For each platform info, add to keep track if not already present
            if merge_track.platform_info is not None:
                # Get keeper track's platforms first to avoid multiple DB queries
                keep_track = self.track_repo.get_by_id(keep_track_id_int)
                if keep_track is None:
                    logger.warning(f"Keep track {keep_track_id_int} not found")
                    return

                # Build a dictionary of existing platform info
                keeper_platforms = {}
                if keep_track.platform_info is not None:
                    keeper_platforms = {
                        info.platform: info.platform_id
                        for info in keep_track.platform_info
                        if hasattr(info, "platform") and hasattr(info, "platform_id")
                    }

                # Process each platform info from the merge track
                for platform_info in merge_track.platform_info:
                    # Skip invalid platform_info objects
                    has_platform = hasattr(platform_info, "platform")
                    has_platform_id = hasattr(platform_info, "platform_id")
                    if not (has_platform and has_platform_id):
                        continue

                    # Get platform details
                    platform = platform_info.platform
                    platform_id = platform_info.platform_id

                    # Get optional attributes safely
                    uri = getattr(platform_info, "uri", None)
                    metadata = getattr(platform_info, "metadata", None)

                    # If keeper doesn't have this platform info, add it
                    if platform not in keeper_platforms:
                        self.track_repo.add_platform_info(
                            track_id=keep_track_id_int,
                            platform=platform,
                            platform_id=platform_id,
                            uri=uri,
                            metadata=metadata,
                        )
                        logger.info(f"Added {platform} info from track {merge_track_id_int} " f"to {keep_track_id_int}")

        except Exception as e:
            logger.exception(f"Error merging track platforms: {e}")
            raise

    def _replace_track_in_playlists(self, old_track_id: int, new_track_id: int):
        """Replace a track with another track in all playlists.

        Args:
            old_track_id: ID of the track to replace
            new_track_id: ID of the replacement track
        """
        try:
            # Validate inputs
            try:
                old_track_id_int = int(old_track_id)
                new_track_id_int = int(new_track_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid track IDs: old={old_track_id}, new={new_track_id}")
                return

            # Get all playlists containing the old track
            from sqlalchemy import select
            from sqlalchemy.exc import SQLAlchemyError

            from selecta.core.data.models.db import PlaylistTrack

            # Get session safely
            session = getattr(self.playlist_repo, "session", None)
            if session is None:
                logger.error("No database session available")
                return

            try:
                # Find all playlist-track associations for the old track
                stmt = select(PlaylistTrack).where(PlaylistTrack.track_id == old_track_id_int)
                playlist_tracks = session.execute(stmt).scalars().all()

                for pt in playlist_tracks:
                    # Check attributes exist
                    if not hasattr(pt, "playlist_id") or not hasattr(pt, "position"):
                        logger.warning(f"Invalid PlaylistTrack object: {pt}")
                        continue

                    playlist_id = pt.playlist_id
                    position = pt.position

                    # Check if the new track is already in this playlist
                    existing_stmt = select(PlaylistTrack).where(
                        PlaylistTrack.playlist_id == playlist_id,
                        PlaylistTrack.track_id == new_track_id_int,
                    )
                    existing = session.execute(existing_stmt).scalar_one_or_none()

                    if not existing:
                        # Add the new track to the playlist
                        self.playlist_repo.add_track(playlist_id, new_track_id_int, position)

                    # Remove the old track from the playlist
                    session.delete(pt)

                session.commit()

            except SQLAlchemyError as db_error:
                session.rollback()
                logger.exception(f"Database error while replacing tracks: {db_error}")
                raise

        except Exception as e:
            logger.exception(f"Error replacing track in playlists: {e}")
            raise

    def _create_playlist_from_selected(self):
        """Create a new playlist from selected orphaned tracks."""
        # Ensure at least one track is selected
        if not self.selected_orphans:
            QMessageBox.warning(self, "No Selection", "Please select at least one track.")
            return

        # Prompt for playlist name
        from PyQt6.QtWidgets import QInputDialog

        playlist_name, ok = QInputDialog.getText(
            self, "New Playlist", "Enter a name for the new playlist:", text="Orphaned Tracks"
        )

        if not ok or not playlist_name:
            return

        # Create the playlist
        try:
            # Create new playlist
            playlist_data = {
                "name": playlist_name,
                "description": "Created from orphaned tracks",
                "is_local": True,
                "source_platform": None,
            }

            new_playlist = self.playlist_repo.create(playlist_data)

            # Check if playlist was created successfully
            if new_playlist is None or not hasattr(new_playlist, "id"):
                QMessageBox.critical(self, "Error", "Failed to create playlist: invalid playlist object")
                return

            # Add selected tracks to the playlist
            valid_tracks_added = 0
            for track_id in self.selected_orphans:
                try:
                    # Convert to int if needed
                    track_id_int = int(track_id)
                    self.playlist_repo.add_track(new_playlist.id, track_id_int)
                    valid_tracks_added += 1
                except (ValueError, TypeError):
                    logger.warning(f"Invalid track ID: {track_id}")
                    continue

            # Show success message
            QMessageBox.information(
                self,
                "Playlist Created",
                f"Created playlist '{playlist_name}' with {valid_tracks_added} tracks.",
            )

            # Emit signal that collection was modified
            self.collection_modified.emit()

            # Refresh the orphans list
            self._refresh_orphans()

        except Exception as e:
            logger.exception(f"Error creating playlist: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create playlist: {str(e)}")

    def _remove_selected_from_collection(self):
        """Remove selected orphaned tracks from the Collection playlist."""
        # Ensure at least one track is selected
        if not self.selected_orphans:
            QMessageBox.warning(self, "No Selection", "Please select at least one track.")
            return

        # Confirm removal
        response = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove {len(self.selected_orphans)} tracks from your Collection? "
            f"The tracks will remain in the database but won't be in the Collection playlist.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Remove tracks from Collection
        try:
            # Get collection playlist ID with type checking
            collection_id = self.duplicate_detector.get_collection_playlist_id()
            if collection_id is None:
                QMessageBox.critical(self, "Error", "Collection playlist not found.")
                return

            try:
                # Ensure collection_id is an integer
                collection_id_int = int(collection_id)
            except (ValueError, TypeError):
                logger.error(f"Invalid collection ID: {collection_id}")
                QMessageBox.critical(self, "Error", "Invalid collection playlist ID.")
                return

            # For each selected track
            removed_count = 0
            for track_id in self.selected_orphans:
                try:
                    # Convert to int if needed
                    track_id_int = int(track_id)
                    # Remove from Collection playlist
                    result = self.playlist_repo.remove_track(collection_id_int, track_id_int)
                    if result:
                        removed_count += 1
                except (ValueError, TypeError):
                    logger.warning(f"Invalid track ID: {track_id}")
                    continue
                except Exception as track_error:
                    logger.warning(f"Error removing track {track_id}: {track_error}")
                    continue

            # Show success message
            QMessageBox.information(self, "Removal Complete", f"Removed {removed_count} tracks from your Collection.")

            # Emit signal that collection was modified
            self.collection_modified.emit()

            # Refresh the orphans list
            self._refresh_orphans()

        except Exception as e:
            logger.exception(f"Error removing tracks from Collection: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove tracks: {str(e)}")
