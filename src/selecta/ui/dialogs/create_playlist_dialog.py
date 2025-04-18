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

    def __init__(self, parent=None, *, available_folders=None):
        """Initialize the create playlist dialog.

        Args:
            parent: Parent widget
            available_folders: List of available folders [(id, name), ...] for parent selection
        """
        super().__init__(parent)
        self.available_folders = available_folders or []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Set window properties
        self.setWindowTitle("Create Playlist")
        self.setMinimumWidth(400)

        # Main layout
        layout = QVBoxLayout(self)

        # Description label
        description = "Create a new playlist or folder in your local library"
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Type selection
        type_form = QFormLayout()
        self.is_folder_checkbox = QCheckBox("Create as folder")
        type_form.addRow("Type:", self.is_folder_checkbox)
        layout.addLayout(type_form)

        # Name input
        name_form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter playlist name")
        name_form.addRow("Name:", self.name_input)
        layout.addLayout(name_form)

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
        return {
            "name": self.name_input.text().strip(),
            "is_folder": self.is_folder_checkbox.isChecked(),
            "parent_id": self.parent_combo.currentData(),
        }
