"""Dialog for importing covers from audio metadata."""
import time

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.metadata_extractor import MetadataExtractor


class ImportCoversThread(QThread):
    """Background thread for importing covers from audio metadata."""

    progress_update = pyqtSignal(int, str)  # Value, message
    import_complete = pyqtSignal(int, int)  # Total imported, failed
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(self, parent=None):
        """Initialize the import thread.

        Args:
            parent: Parent object
        """
        super().__init__(parent)
        self.cancelled = False
        self.extractor = MetadataExtractor()
        self.track_repo = TrackRepository()

        # Statistics
        self.succeeded = 0
        self.failed = 0

    def cancel(self):
        """Cancel the import process."""
        self.cancelled = True

    def run(self):
        """Run the import process."""
        try:
            # Get all tracks with local paths
            tracks = self.track_repo.get_all_with_local_path()

            if not tracks:
                self.error_occurred.emit("No local tracks found")
                return

            # Calculate total
            total_tracks = len(tracks)
            self.progress_update.emit(0, f"Found {total_tracks} local tracks")

            # Process each track
            for i, track in enumerate(tracks):
                if self.cancelled:
                    break

                # Update progress (0-100)
                progress = int((i / total_tracks) * 100)
                self.progress_update.emit(
                    progress,
                    f"Processing track {i + 1} of {total_tracks}: {track.artist} - {track.title}",
                )

                # Process the track
                if self.extractor.extract_cover_from_track(track.id):
                    self.succeeded += 1
                else:
                    self.failed += 1

                # Small delay to prevent UI freezing
                time.sleep(0.01)

            # Final update
            self.progress_update.emit(100, "Import complete")
            self.import_complete.emit(self.succeeded, self.failed)

        except Exception as e:
            logger.exception(f"Error in import thread: {e}")
            self.error_occurred.emit(f"Import error: {str(e)}")


class ImportCoversDialog(QDialog):
    """Dialog for importing covers from audio metadata."""

    def __init__(self, parent=None):
        """Initialize the import dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Import Covers from Audio Files")
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)

        # Initialize repositories
        self.settings_repo = SettingsRepository()

        # Get local database folder
        self.local_folder = self.settings_repo.get_local_database_folder()
        if not self.local_folder:
            QMessageBox.critical(
                self, "No Local Database Folder", "Please select a local database folder first."
            )
            self.reject()
            return

        # Initialize UI
        self._setup_ui()

        # Import thread
        self.import_thread = None

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Information
        info_label = QLabel(
            "This will extract cover art from your local audio files "
            "and add them to the database.\n\n"
            "Only tracks without existing covers will be processed."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to import covers")
        layout.addWidget(self.status_label)

        # Buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        self.import_button = QPushButton("Start Import")
        self.import_button.setDefault(True)
        self.import_button.clicked.connect(self._start_import)
        layout.addWidget(self.import_button)

    def _start_import(self):
        """Start the import process."""
        # Disable the import button
        self.import_button.setEnabled(False)

        # Create and start the import thread
        self.import_thread = ImportCoversThread(self)

        # Connect signals
        self.import_thread.progress_update.connect(self._update_progress)
        self.import_thread.import_complete.connect(self._import_complete)
        self.import_thread.error_occurred.connect(self._handle_error)

        # Change cancel button to cancel import
        self.cancel_button.setText("Cancel Import")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self._cancel_import)

        # Start the thread
        self.import_thread.start()

    def _update_progress(self, value: int, message: str):
        """Update the progress bar and status message."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def _import_complete(self, succeeded: int, failed: int):
        """Handle import completion."""
        # Re-enable import button
        self.import_button.setEnabled(True)

        # Change cancel button back to close
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

        # Show a summary
        if failed == 0 and succeeded == 0:
            QMessageBox.information(self, "Import Complete", "No new covers were found to import.")
        elif failed == 0:
            QMessageBox.information(
                self, "Import Complete", f"Successfully imported {succeeded} covers."
            )
        else:
            QMessageBox.warning(
                self,
                "Import Complete with Issues",
                f"Imported {succeeded} covers, {failed} failed.\n\n"
                f"This is normal if some tracks don't have embedded artwork.",
            )

    def _handle_error(self, error_message: str):
        """Handle serious errors that stop the import process."""
        QMessageBox.critical(
            self, "Import Error", f"An error occurred during import:\n\n{error_message}"
        )

        # Re-enable import button
        self.import_button.setEnabled(True)

        # Change cancel button back to close
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.reject)

    def _cancel_import(self):
        """Cancel the import process."""
        if self.import_thread and self.import_thread.isRunning():
            # Ask for confirmation
            response = QMessageBox.question(
                self,
                "Cancel Import",
                "Are you sure you want to cancel the import?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response == QMessageBox.StandardButton.Yes:
                self.import_thread.cancel()
                self.status_label.setText("Cancelling...")
        else:
            self.reject()

    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.import_thread and self.import_thread.isRunning():
            # Prevent closing if import is in progress
            event.ignore()
            self._cancel_import()
        else:
            event.accept()