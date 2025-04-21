"""Dialog for previewing and selecting sync changes."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.types import SyncPreview, SyncResult, TrackChange


class SyncPreviewDialog(QDialog):
    """Dialog showing sync changes preview with options to select which changes to apply."""

    def __init__(
        self,
        parent=None,
        *,
        sync_preview: SyncPreview,
    ):
        """Initialize the sync preview dialog.

        Args:
            parent: Parent widget
            sync_preview: SyncPreview object with changes to display
        """
        super().__init__(parent)
        self.sync_preview = sync_preview
        self.selected_changes: dict[str, bool] = {}
        self.change_items: dict[str, QTreeWidgetItem] = {}
        self.section_checkboxes = {}

        self._setup_ui()
        self._initialize_changes()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Set window properties
        self.setWindowTitle(f"Sync Preview - {self.sync_preview.platform.capitalize()}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        # Main layout
        layout = QVBoxLayout(self)

        # Summary header
        header_layout = QHBoxLayout()
        platform_icon_label = QLabel()
        # TODO: Add platform icon
        header_layout.addWidget(platform_icon_label)

        info_layout = QVBoxLayout()
        title_label = QLabel(
            f"<h3>Sync: {self.sync_preview.library_playlist_name} ↔ "
            f"{self.sync_preview.platform_playlist_name}</h3>"
        )
        info_layout.addWidget(title_label)

        # Last sync info
        if self.sync_preview.last_synced:
            last_sync_formatted = self.sync_preview.last_synced.strftime("%Y-%m-%d %H:%M")
            last_sync_label = QLabel(f"Last synced: {last_sync_formatted}")
        else:
            last_sync_label = QLabel("First sync - no previous sync state")
            last_sync_label.setStyleSheet("color: orange;")
        info_layout.addWidget(last_sync_label)

        # Show personal/shared status
        if self.sync_preview.is_personal_playlist:
            playlist_type_label = QLabel("Personal playlist: full bidirectional sync available")
            playlist_type_label.setStyleSheet("color: green;")
        else:
            playlist_type_label = QLabel(
                "Shared/public playlist: import-only, no bidirectional sync"
            )
            playlist_type_label.setStyleSheet("color: orange;")
        info_layout.addWidget(playlist_type_label)

        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Changes summary
        changes_count = self._count_all_changes()
        if changes_count > 0:
            summary_label = QLabel(f"<b>{changes_count} changes detected</b>")
        else:
            summary_label = QLabel("<b>No changes detected - playlists are in sync</b>")
            summary_label.setStyleSheet("color: green;")
        layout.addWidget(summary_label)

        # Errors and warnings
        if self.sync_preview.errors:
            error_box = QGroupBox("Errors")
            error_layout = QVBoxLayout(error_box)
            for error in self.sync_preview.errors:
                error_label = QLabel(error)
                error_label.setStyleSheet("color: red;")
                error_layout.addWidget(error_label)
            layout.addWidget(error_box)

        if self.sync_preview.warnings:
            warning_box = QGroupBox("Warnings")
            warning_layout = QVBoxLayout(warning_box)
            for warning in self.sync_preview.warnings:
                warning_label = QLabel(warning)
                warning_label.setStyleSheet("color: orange;")
                warning_layout.addWidget(warning_label)
            layout.addWidget(warning_box)

        # Create scroll area with changes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        # Add change sections
        if self.sync_preview.platform_additions:
            self._add_change_section(
                scroll_layout,
                "Platform Additions",
                "Tracks added on platform - will be imported to library",
                self.sync_preview.platform_additions,
                "platform_additions",
            )

        if self.sync_preview.platform_removals:
            self._add_change_section(
                scroll_layout,
                "Platform Removals",
                "Tracks removed from platform - will be removed from library playlist",
                self.sync_preview.platform_removals,
                "platform_removals",
            )

        if self.sync_preview.is_personal_playlist:
            if self.sync_preview.library_additions:
                self._add_change_section(
                    scroll_layout,
                    "Library Additions",
                    "Tracks added to library - will be exported to platform",
                    self.sync_preview.library_additions,
                    "library_additions",
                )

            if self.sync_preview.library_removals:
                self._add_change_section(
                    scroll_layout,
                    "Library Removals",
                    "Tracks removed from library - will be removed from platform playlist",
                    self.sync_preview.library_removals,
                    "library_removals",
                )

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Button row
        button_layout = QHBoxLayout()

        # Select/deselect all buttons
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self._select_all_changes)
        button_layout.addWidget(select_all_button)

        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self._deselect_all_changes)
        button_layout.addWidget(deselect_all_button)

        button_layout.addStretch()

        # Cancel and apply buttons
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.apply_button = QPushButton("Apply Selected Changes")
        self.apply_button.clicked.connect(self.accept)
        self.apply_button.setDefault(True)
        if changes_count == 0:
            self.apply_button.setEnabled(False)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _add_change_section(
        self,
        parent_layout: QVBoxLayout,
        title: str,
        description: str,
        changes: list[TrackChange],
        section_id: str,
    ):
        """Add a section for a category of changes.

        Args:
            parent_layout: Layout to add the section to
            title: Section title
            description: Section description
            changes: List of changes in this category
            section_id: Identifier for this section
        """
        # Create section group box
        section_box = QGroupBox(f"{title} ({len(changes)})")
        section_layout = QVBoxLayout(section_box)

        # Add description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        section_layout.addWidget(desc_label)

        # Add tree widget for changes
        tree = QTreeWidget()
        tree.setHeaderLabels(["Track", "Artist", "Action"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)
        section_layout.addWidget(tree)

        # Add "Select All" checkbox for this section
        section_checkbox = QCheckBox("Select All in This Section")
        section_checkbox.setChecked(True)
        section_checkbox.toggled.connect(lambda checked: self._toggle_section(section_id, checked))
        section_layout.addWidget(section_checkbox)
        self.section_checkboxes[section_id] = section_checkbox

        # Add the section to parent layout
        parent_layout.addWidget(section_box)

    def _initialize_changes(self):
        """Initialize the changes list with data from sync preview."""
        # Process platform additions
        self._populate_change_section(
            "platform_additions", self.sync_preview.platform_additions, "Import to library"
        )

        # Process platform removals
        self._populate_change_section(
            "platform_removals", self.sync_preview.platform_removals, "Remove from library"
        )

        # Process library additions (if personal playlist)
        if self.sync_preview.is_personal_playlist:
            self._populate_change_section(
                "library_additions", self.sync_preview.library_additions, "Export to platform"
            )

            # Process library removals
            self._populate_change_section(
                "library_removals", self.sync_preview.library_removals, "Remove from platform"
            )

        # Set all changes as selected by default
        for change_id in self.change_items:
            self.selected_changes[change_id] = True

        # Resize columns
        for section_id in [
            "platform_additions",
            "platform_removals",
            "library_additions",
            "library_removals",
        ]:
            if section_id in self.section_checkboxes:
                section_box = self.section_checkboxes[section_id].parent()
                if section_box:
                    for tree in section_box.findChildren(QTreeWidget):
                        for i in range(tree.columnCount()):
                            tree.resizeColumnToContents(i)

    def _populate_change_section(
        self,
        section_id: str,
        changes: list[TrackChange],
        action_text: str,
    ):
        """Populate a change section with track items.

        Args:
            section_id: Section identifier
            changes: List of changes to display
            action_text: Text describing the action
        """
        if not changes:
            return

        # Find the tree widget in this section
        section_box = self.section_checkboxes.get(section_id, None)
        if not section_box:
            return

        parent = section_box.parent()
        if not parent:
            return

        trees = parent.findChildren(QTreeWidget)
        if not trees:
            return

        tree = trees[0]

        # Add items for each change
        for change in changes:
            item = QTreeWidgetItem(tree)
            item.setText(0, change.track_title)
            item.setText(1, change.track_artist)
            item.setText(2, action_text)
            item.setData(0, Qt.ItemDataRole.UserRole, change.change_id)
            item.setCheckState(0, Qt.CheckState.Checked)

            # Store reference to item
            self.change_items[change.change_id] = item

            # Connect checkstate change
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

        # Set up the connection for checkbox changes
        tree.itemChanged.connect(self._item_changed)

    def _item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state changes.

        Args:
            item: The item that changed
            column: The column that changed
        """
        if column == 0:  # First column has the checkbox
            change_id = item.data(0, Qt.ItemDataRole.UserRole)
            if change_id:
                is_checked = item.checkState(0) == Qt.CheckState.Checked
                self.selected_changes[change_id] = is_checked
                self._update_section_checkboxes()

    def _toggle_section(self, section_id: str, checked: bool):
        """Toggle selection for all changes in a section.

        Args:
            section_id: Section identifier
            checked: Whether to check or uncheck items
        """
        # Get the changes for this section
        changes = []
        if section_id == "platform_additions":
            changes = self.sync_preview.platform_additions
        elif section_id == "platform_removals":
            changes = self.sync_preview.platform_removals
        elif section_id == "library_additions":
            changes = self.sync_preview.library_additions
        elif section_id == "library_removals":
            changes = self.sync_preview.library_removals

        # Update all items in this section
        for change in changes:
            self.selected_changes[change.change_id] = checked
            if change.change_id in self.change_items:
                item = self.change_items[change.change_id]
                # Temporarily disconnect to avoid recursion
                parent = item.treeWidget()
                if parent:
                    parent.itemChanged.disconnect(self._item_changed)
                item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                if parent:
                    parent.itemChanged.connect(self._item_changed)

    def _select_all_changes(self):
        """Select all changes in all sections."""
        for section_id in self.section_checkboxes:
            checkbox = self.section_checkboxes[section_id]
            checkbox.setChecked(True)

    def _deselect_all_changes(self):
        """Deselect all changes in all sections."""
        for section_id in self.section_checkboxes:
            checkbox = self.section_checkboxes[section_id]
            checkbox.setChecked(False)

    def _update_section_checkboxes(self):
        """Update section checkboxes based on individual item states."""
        # For each section, check if all items are checked
        for section_id in [
            "platform_additions",
            "platform_removals",
            "library_additions",
            "library_removals",
        ]:
            if section_id not in self.section_checkboxes:
                continue

            # Get the changes for this section
            changes = []
            if section_id == "platform_additions":
                changes = self.sync_preview.platform_additions
            elif section_id == "platform_removals":
                changes = self.sync_preview.platform_removals
            elif section_id == "library_additions":
                changes = self.sync_preview.library_additions
            elif section_id == "library_removals":
                changes = self.sync_preview.library_removals

            # Check if all changes are selected
            all_selected = True
            for change in changes:
                if not self.selected_changes.get(change.change_id, False):
                    all_selected = False
                    break

            # Update checkbox state
            checkbox = self.section_checkboxes[section_id]
            # Temporarily disconnect to avoid recursion
            was_blocked = checkbox.blockSignals(True)
            checkbox.setChecked(all_selected)
            checkbox.blockSignals(was_blocked)

    def _count_all_changes(self) -> int:
        """Count the total number of changes across all categories.

        Returns:
            Total count of changes
        """
        return (
            len(self.sync_preview.platform_additions)
            + len(self.sync_preview.platform_removals)
            + len(self.sync_preview.library_additions)
            + len(self.sync_preview.library_removals)
        )

    def get_selected_changes(self) -> dict[str, bool]:
        """Get the user's change selections.

        Returns:
            Dictionary mapping change IDs to selection status
        """
        return self.selected_changes

    def show_progress(self, progress: int, max_value: int):
        """Show sync progress.

        Args:
            progress: Current progress value
            max_value: Maximum progress value
        """
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(progress)
        self.progress_bar.setVisible(True)

    def update_with_result(self, result: SyncResult):
        """Update the dialog with sync results.

        Args:
            result: Sync operation result
        """
        # Update progress bar
        self.progress_bar.setValue(self.progress_bar.maximum())

        # Update buttons
        self.apply_button.setEnabled(False)
        self.findChild(QPushButton, "Cancel").setText("Close")

        # TODO: Add result details
