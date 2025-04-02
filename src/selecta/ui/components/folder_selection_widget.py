# src/selecta/ui/components/folder_selection_widget.py
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.settings_repository import SettingsRepository


class FolderSelectionWidget(QWidget):
    """Widget for selecting and displaying the local database folder."""

    folder_changed = pyqtSignal(str)  # Signal emitted when folder is changed

    def __init__(self, parent=None):
        """Initialize the folder selection widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings_repo = SettingsRepository()
        self._setup_ui()
        self._load_current_folder()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        header = QLabel("Local Database Folder")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #DDDDDD;")
        layout.addWidget(header)

        # Description
        description = QLabel(
            "Select the root folder for your local music database. "
            "This folder will be scanned for audio files "
            "which will be added to your local database."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #AAAAAA; margin-bottom: 10px;")
        layout.addWidget(description)

        # Current folder display and select button
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.folder_label.setStyleSheet("""
            background-color: #333333;
            padding: 8px;
            border-radius: 4px;
            color: #CCCCCC;
        """)
        folder_layout.addWidget(self.folder_label)

        self.select_button = QPushButton("Browse...")
        self.select_button.setFixedWidth(100)
        self.select_button.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.select_button)

        layout.addLayout(folder_layout)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #999999; font-style: italic; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # Add spacer at the bottom
        layout.addStretch(1)

    def _load_current_folder(self):
        """Load and display the currently selected folder from settings."""
        folder_path = self.settings_repo.get_local_database_folder()

        if folder_path:
            self.folder_label.setText(folder_path)
            self._update_status(f"Contains {self._count_audio_files(folder_path)} audio files")
        else:
            self.folder_label.setText("No folder selected")
            self.status_label.setText("")

    def _select_folder(self):
        """Open a folder selection dialog and save the selected path."""
        # Get the current folder to use as starting point if it exists
        current_folder = self.settings_repo.get_local_database_folder()
        start_dir = current_folder if current_folder else str(Path.home())

        # Open folder selection dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Local Database Folder",
            start_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if folder_path:
            # Save the selected folder to settings
            try:
                self.settings_repo.set_local_database_folder(folder_path)
                self.folder_label.setText(folder_path)

                # Update status with audio file count
                audio_count = self._count_audio_files(folder_path)
                self._update_status(f"Contains {audio_count} audio files")

                # Emit signal that folder has changed
                self.folder_changed.emit(folder_path)

                logger.info(f"Local database folder set to: {folder_path}")
            except Exception as e:
                logger.exception(f"Error saving local database folder: {e}")
                self._update_status(f"Error saving folder: {str(e)}", error=True)

    def _update_status(self, message: str, error: bool = False):
        """Update the status label with a message.

        Args:
            message: Status message to display
            error: Whether this is an error message
        """
        color = "#FF5555" if error else "#999999"
        self.status_label.setStyleSheet(f"color: {color}; font-style: italic; margin-top: 5px;")
        self.status_label.setText(message)

    def _count_audio_files(self, folder_path: str) -> int:
        """Count the number of audio files in the folder and its subfolders.

        Args:
            folder_path: Path to the folder to scan

        Returns:
            Number of audio files found
        """
        try:
            audio_extensions = {".mp3", ".flac", ".wav", ".aac", ".m4a", ".ogg", ".aiff"}
            folder = Path(folder_path)

            # Use a generator expression to count matching files
            count = sum(
                1
                for f in folder.glob("**/*")
                if f.is_file() and f.suffix.lower() in audio_extensions
            )

            return count
        except Exception as e:
            logger.exception(f"Error counting audio files: {e}")
            return 0
