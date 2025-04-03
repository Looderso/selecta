"""Dialog for importing/exporting playlists from/to platforms."""

from typing import cast

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ImportExportPlaylistDialog(QDialog):
    """Dialog for importing/exporting playlists to/from platforms."""

    def __init__(
        self,
        parent=None,
        *,
        mode="import",
        platform="spotify",
        default_name="",
        enable_folder_selection=False,
        available_folders=None,
    ):
        """Initialize the import/export playlist dialog.

        Args:
            parent: Parent widget
            mode: Either "import" or "export"
            platform: The platform name ("spotify" or "rekordbox")
            default_name: Default name for the playlist
            enable_folder_selection: Whether to show folder selection (for rekordbox)
            available_folders: List of available folders [(id, name), ...] for rekordbox
        """
        super().__init__(parent)
        self.mode = mode
        self.platform = platform
        self.default_name = default_name
        self.enable_folder_selection = enable_folder_selection
        self.available_folders = available_folders or []

        self._setup_ui()
        self._initialize_values()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Set window properties
        title = "Import Playlist" if self.mode == "import" else "Export Playlist"
        self.setWindowTitle(f"{title} - {self.platform.capitalize()}")
        self.setMinimumWidth(400)

        # Main layout
        layout = QVBoxLayout(self)

        # Description label
        if self.mode == "import":
            description = f"Import a {self.platform.capitalize()} playlist to your local library"
        else:
            description = f"Export this playlist to {self.platform.capitalize()}"

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Playlist name section
        name_form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(self.default_name)
        name_form.addRow("Playlist Name:", self.name_input)
        layout.addLayout(name_form)

        # Rekordbox-specific folder selection
        if self.platform == "rekordbox" and self.enable_folder_selection:
            # Folder selection group
            folder_group = QGroupBox("Folder Options")
            folder_layout = QVBoxLayout(folder_group)

            # Checkbox for using a folder
            self.use_folder_checkbox = QCheckBox("Add to a folder")
            folder_layout.addWidget(self.use_folder_checkbox)

            # Folder selection combo
            folder_form = QFormLayout()
            self.folder_combo = QComboBox()
            # Add a "Root" option
            self.folder_combo.addItem("Root (No folder)", "")

            # Add available folders
            for folder_id, folder_name in self.available_folders:
                self.folder_combo.addItem(folder_name, folder_id)

            self.folder_combo.setEnabled(False)
            folder_form.addRow("Select Folder:", self.folder_combo)
            folder_layout.addLayout(folder_form)

            # Connect checkbox to enable/disable the combo
            self.use_folder_checkbox.toggled.connect(self.folder_combo.setEnabled)

            layout.addWidget(folder_group)

        # Warning message for platform-specific limitations
        if self.mode == "export":
            warning_text = ""
            if self.platform == "spotify":
                warning_text = (
                    "Note: Only tracks with Spotify metadata will be exported. "
                    "Tracks without Spotify data will be skipped."
                )
            elif self.platform == "rekordbox":
                warning_text = (
                    "Note: Only tracks with Rekordbox metadata or tracks in your "
                    "local database folder will be exported. Other tracks will be skipped."
                )

            if warning_text:
                warning_label = QLabel(warning_text)
                warning_label.setWordWrap(True)
                warning_label.setStyleSheet("color: orange;")
                layout.addWidget(warning_label)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

    def _initialize_values(self):
        """Initialize form values with defaults."""
        # Already setup in _setup_ui

    def get_values(self):
        """Get the user-entered values.

        Returns:
            Dictionary with the form values
        """
        result = {
            "name": self.name_input.text().strip(),
        }

        # Add rekordbox folder info if applicable
        if self.platform == "rekordbox" and self.enable_folder_selection:
            if self.use_folder_checkbox.isChecked():
                result["parent_folder_id"] = cast(str, self.folder_combo.currentData())
            else:
                result["parent_folder_id"] = None

        return result
