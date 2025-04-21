"""Dialog for creating a new playlist or folder."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class CreatePlaylistDialog(QDialog):
    """Dialog for creating a new playlist or folder."""

    def __init__(self, parent=None, *, available_folders=None, platform_name=None):
        """Initialize the create playlist dialog.

        Args:
            parent: Parent widget
            available_folders: List of available folders [(id, name), ...] for parent selection
            platform_name: Optional platform name to customize fields
        """
        super().__init__(parent)
        self.available_folders = available_folders or []
        self.platform_name = platform_name

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Set window properties
        self.setWindowTitle("Create Playlist")
        self.setMinimumWidth(400)

        # Main layout
        layout = QVBoxLayout(self)

        # Description label
        description = "Create a new playlist"
        if self.platform_name:
            description += f" on {self.platform_name}"
        else:
            description += " or folder in your local library"
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Type selection - only show for local playlists
        if not self.platform_name:
            type_form = QFormLayout()
            self.is_folder_checkbox = QCheckBox("Create as folder")
            type_form.addRow("Type:", self.is_folder_checkbox)
            layout.addLayout(type_form)
        else:
            # Create a hidden checkbox for type compatibility
            self.is_folder_checkbox = QCheckBox()
            self.is_folder_checkbox.setVisible(False)

        # Name input
        name_form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter playlist name")
        name_form.addRow("Name:", self.name_input)
        layout.addLayout(name_form)

        # Description input for platform playlists
        if self.platform_name in ["YouTube", "Spotify"]:
            description_form = QFormLayout()
            self.description_input = QLineEdit()
            self.description_input.setPlaceholderText("Enter playlist description")
            description_form.addRow("Description:", self.description_input)
            layout.addLayout(description_form)

            # Privacy setting for platforms that support it
            privacy_form = QFormLayout()
            self.is_public_checkbox = QCheckBox("Make playlist public")
            privacy_form.addRow("Privacy:", self.is_public_checkbox)
            layout.addLayout(privacy_form)

        # Parent folder selection
        folder_form = QFormLayout()
        self.parent_combo = QComboBox()

        # Add a "Root" option
        self.parent_combo.addItem("Root (No parent)", None)

        # Add available folders
        for folder_id, folder_name in self.available_folders:
            self.parent_combo.addItem(folder_name, folder_id)

        folder_form.addRow("Parent Folder:", self.parent_combo)
        layout.addLayout(folder_form)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("Create")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

    def get_values(self):
        """Get the user-entered values.

        Returns:
            Dictionary with the form values
        """
        values = {
            "name": self.name_input.text().strip(),
            "is_folder": self.is_folder_checkbox.isChecked(),
            "parent_id": self.parent_combo.currentData(),
        }

        # Add platform-specific fields when present
        if hasattr(self, "description_input"):
            values["description"] = self.description_input.text().strip()

        if hasattr(self, "is_public_checkbox"):
            values["is_public"] = self.is_public_checkbox.isChecked()

        return values

    def get_playlist_name(self):
        """Get the entered playlist name.

        Returns:
            The playlist name as a string
        """
        return self.name_input.text().strip()

    def get_playlist_description(self):
        """Get the entered playlist description.

        Returns:
            The playlist description as a string, or empty string if not available
        """
        if hasattr(self, "description_input"):
            return self.description_input.text().strip()
        return ""

    def is_public(self):
        """Check if the playlist should be public.

        Returns:
            True if the playlist should be public, False otherwise
        """
        if hasattr(self, "is_public_checkbox"):
            return self.is_public_checkbox.isChecked()
        return False
