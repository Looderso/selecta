"""Widget for selecting and managing the local database folder."""

from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QCoreApplication, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.utils.folder_scanner import LocalFolderScanner


class FolderSelectionWidget(QWidget):
    """Widget for selecting and displaying the local database folder."""

    folder_changed = pyqtSignal(str)  # Signal emitted when folder is changed
    import_rekordbox_clicked = pyqtSignal()  # Signal emitted when import button is clicked
    import_covers_clicked = pyqtSignal()  # Signal emitted when import covers button is clicked

    def __init__(self, parent=None):
        """Initialize the folder selection widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings_repo = SettingsRepository()
        self._setup_ui()
        self._load_current_folder()
        self._update_button_states()

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
            "This folder will be used to store your music collection."
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

        # Import section
        import_section_layout = QVBoxLayout()
        import_section_layout.setSpacing(10)
        import_section_layout.setContentsMargins(0, 15, 0, 0)

        # Import header
        import_header = QLabel("Import Options")
        import_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #DDDDDD;")
        import_section_layout.addWidget(import_header)

        # Import description
        import_description = QLabel("Import tracks from external sources to your local collection.")
        import_description.setWordWrap(True)
        import_description.setStyleSheet("color: #AAAAAA; margin-bottom: 10px;")
        import_section_layout.addWidget(import_description)

        # Import buttons
        import_buttons_layout = QHBoxLayout()
        import_buttons_layout.setSpacing(10)

        self.import_rekordbox_button = QPushButton("Import from Rekordbox")
        self.import_rekordbox_button.clicked.connect(self._on_import_rekordbox)
        # Initially disabled until we have a folder selected and Rekordbox is authenticated
        self.import_rekordbox_button.setEnabled(False)
        import_buttons_layout.addWidget(self.import_rekordbox_button)

        self.import_covers_button = QPushButton("Import Covers from Audio Files")
        self.import_covers_button.clicked.connect(self._on_import_covers)
        # Initially disabled until we have a folder selected
        self.import_covers_button.setEnabled(False)
        import_buttons_layout.addWidget(self.import_covers_button)

        import_buttons_layout.addStretch(1)  # Push buttons to the left
        import_section_layout.addLayout(import_buttons_layout)

        # Import status
        self.import_status_label = QLabel("")
        self.import_status_label.setStyleSheet(
            "color: #999999; font-style: italic; margin-top: 5px;"
        )
        import_section_layout.addWidget(self.import_status_label)

        layout.addLayout(import_section_layout)

        # Folder management
        folder_management_layout = QVBoxLayout()
        folder_management_layout.setSpacing(10)
        folder_management_layout.setContentsMargins(0, 15, 0, 0)

        # Folder management header
        folder_management_header = QLabel("Folder Management")
        folder_management_header.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #DDDDDD;"
        )
        folder_management_layout.addWidget(folder_management_header)

        # Folder management description
        folder_management_description = QLabel("Manage files in your local database folder.")
        folder_management_description.setWordWrap(True)
        folder_management_description.setStyleSheet("color: #AAAAAA; margin-bottom: 10px;")
        folder_management_layout.addWidget(folder_management_description)

        # Management buttons
        management_buttons_layout = QHBoxLayout()
        management_buttons_layout.setSpacing(10)

        self.scan_folder_button = QPushButton("Scan Folder")
        self.scan_folder_button.clicked.connect(self._on_scan_folder)
        # Initially disabled until we have a folder selected
        self.scan_folder_button.setEnabled(False)
        management_buttons_layout.addWidget(self.scan_folder_button)

        management_buttons_layout.addStretch(1)  # Push buttons to the left
        folder_management_layout.addLayout(management_buttons_layout)

        # Management status
        self.management_status_label = QLabel("")
        self.management_status_label.setStyleSheet(
            "color: #999999; font-style: italic; margin-top: 5px;"
        )
        folder_management_layout.addWidget(self.management_status_label)

        layout.addLayout(folder_management_layout)

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

        # Update button states after loading folder
        self._update_button_states()

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

                # Update button states
                self._update_button_states()

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

    def _update_import_status(self, message: str, error: bool = False):
        """Update the import status label with a message.

        Args:
            message: Status message to display
            error: Whether this is an error message
        """
        color = "#FF5555" if error else "#999999"
        self.import_status_label.setStyleSheet(
            f"color: {color}; font-style: italic; margin-top: 5px;"
        )
        self.import_status_label.setText(message)

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

    def _on_import_rekordbox(self):
        """Handle Rekordbox import button click."""
        # Emit the signal to trigger import process
        self.import_rekordbox_clicked.emit()

    def _on_import_covers(self):
        """Handle Import Covers button click."""
        # Emit the signal to trigger import covers process
        self.import_covers_clicked.emit()

    def _update_button_states(self):
        """Update the state of buttons based on current conditions."""
        # Check if a folder is selected
        folder_path = self.settings_repo.get_local_database_folder()
        has_folder = bool(folder_path)

        # Check Rekordbox authentication
        rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)
        rekordbox_authenticated = False
        if rekordbox_client:
            # Use contextlib.suppress to handle exceptions cleanly
            import contextlib

            with contextlib.suppress(Exception):
                rekordbox_authenticated = bool(rekordbox_client.is_authenticated())

        # Enable/disable buttons
        self.import_rekordbox_button.setEnabled(has_folder and rekordbox_authenticated)
        self.import_covers_button.setEnabled(has_folder)
        self.scan_folder_button.setEnabled(has_folder)

        # Update status messages
        if not has_folder:
            self._update_import_status("Select a folder to enable import options")
            self._update_management_status("Select a folder to enable management options")
        else:
            if not rekordbox_authenticated:
                self._update_import_status("Authenticate Rekordbox to enable import")
            else:
                self._update_import_status("Ready to import from Rekordbox")

            self._update_management_status("Ready to manage local files")

    def _update_management_status(self, message: str, error: bool = False):
        """Update the management status label with a message.

        Args:
            message: Status message to display
            error: Whether this is an error message
        """
        color = "#FF5555" if error else "#999999"
        self.management_status_label.setStyleSheet(
            f"color: {color}; font-style: italic; margin-top: 5px;"
        )
        self.management_status_label.setText(message)

    def _on_scan_folder(self):
        """Handle scan folder button click."""
        folder_path = self.settings_repo.get_local_database_folder()
        if not folder_path:
            self._update_management_status("No folder selected", error=True)
            return

        # Create a dialog to show scan options
        scan_dialog = QDialog(self)
        scan_dialog.setWindowTitle("Scan Folder")
        scan_dialog.setMinimumWidth(400)

        dialog_layout = QVBoxLayout(scan_dialog)

        # Information
        info_label = QLabel(
            f"Scan the folder: {folder_path}\n\n"
            "This will check for any audio files not yet in your database."
        )
        info_label.setWordWrap(True)
        dialog_layout.addWidget(info_label)

        # Options
        self.scan_only_radio = QRadioButton("Scan only (report files not in database)")
        self.scan_only_radio.setChecked(True)
        dialog_layout.addWidget(self.scan_only_radio)

        self.import_radio = QRadioButton("Import untracked files to database")
        dialog_layout.addWidget(self.import_radio)

        # Buttons
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(scan_dialog.reject)
        button_layout.addWidget(cancel_button)

        button_layout.addStretch(1)

        start_button = QPushButton("Start Scan")
        start_button.setDefault(True)
        start_button.clicked.connect(scan_dialog.accept)
        button_layout.addWidget(start_button)

        dialog_layout.addLayout(button_layout)

        # Show dialog and get result
        if scan_dialog.exec() == 1:  # QDialog.Accepted
            if self.scan_only_radio.isChecked():
                self._scan_folder_only(folder_path)
            else:
                self._scan_and_import(folder_path)

    def _scan_folder_only(self, folder_path: str):
        """Scan the folder and report results without importing.

        Args:
            folder_path: Path to scan
        """
        try:
            # Create a progress dialog
            progress = QProgressDialog("Scanning folder...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setWindowTitle("Scanning Folder")
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(10)

            # Create scanner
            scanner = LocalFolderScanner(folder_path)

            # Update progress
            progress.setValue(30)
            progress.setLabelText("Analyzing files...")

            # Process events to keep UI responsive
            QCoreApplication.processEvents()

            # Scan folder
            scan_result = scanner.scan_folder()

            # Update progress
            progress.setValue(100)
            progress.close()

            # Show results
            in_db_count = len(scan_result["in_database"])
            untracked_count = len(scan_result["not_in_database"])
            missing_count = len(scan_result["missing_from_folder"])

            total_physical = in_db_count + untracked_count

            message = (
                f"Scan complete. Found {total_physical} audio files in folder.\n\n"
                f"• {in_db_count} files are in the database\n"
                f"• {untracked_count} files are not in the database\n"
                f"• {missing_count} database entries have missing files\n\n"
            )

            if untracked_count > 0:
                message += "Would you like to import the untracked files now?"

                response = QMessageBox.question(
                    self,
                    "Scan Results",
                    message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

                if response == QMessageBox.StandardButton.Yes:
                    self._scan_and_import(folder_path)
                else:
                    QMessageBox.information(
                        self, "Scan Complete", "Scan completed without importing files."
                    )
            else:
                QMessageBox.information(self, "Scan Complete", message)

        except Exception as e:
            logger.exception(f"Error scanning folder: {e}")
            QMessageBox.critical(
                self, "Scan Error", f"An error occurred during scanning:\n\n{str(e)}"
            )

    def _scan_and_import(self, folder_path: str):
        """Scan the folder and import untracked files.

        Args:
            folder_path: Path to scan
        """
        try:
            # Create a progress dialog
            progress = QProgressDialog("Scanning and importing files...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setWindowTitle("Importing Files")
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(10)

            # Create scanner
            scanner = LocalFolderScanner(folder_path)

            # Update progress
            progress.setValue(30)
            progress.setLabelText("Analyzing files...")

            # Process events to keep UI responsive
            QCoreApplication.processEvents()

            # Scan folder
            scan_result = scanner.scan_folder()
            untracked_count = len(scan_result["not_in_database"])

            if untracked_count == 0:
                progress.close()
                QMessageBox.information(
                    self, "Nothing to Import", "No untracked files found in the folder."
                )
                return

            # Update progress
            progress.setValue(50)
            progress.setLabelText(f"Importing {untracked_count} files...")
            QCoreApplication.processEvents()

            # Import untracked files
            imported_count, errors = scanner.import_untracked_files()

            # Update progress
            progress.setValue(100)
            progress.close()

            # Show results
            if not errors:
                QMessageBox.information(
                    self,
                    "Import Complete",
                    f"Successfully imported {imported_count} files to your database.",
                )
            else:
                error_details = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_details += f"\n...and {len(errors) - 5} more errors."

                QMessageBox.warning(
                    self,
                    "Import Complete with Errors",
                    f"Imported {imported_count} files, {len(errors)} failed.\n\n"
                    f"First few errors:\n{error_details}",
                )

            # Update our file count in the display
            self._load_current_folder()

            # Emit folder changed signal to refresh UI
            self.folder_changed.emit(folder_path)

        except Exception as e:
            logger.exception(f"Error importing files: {e}")
            QMessageBox.critical(
                self, "Import Error", f"An error occurred during import:\n\n{str(e)}"
            )