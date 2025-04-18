"""Dialog for importing tracks from Rekordbox."""

import os
import shutil
import time
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from selecta.core.data.models.db import TrackAttribute
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.rekordbox.models import RekordboxTrack


class ImportThread(QThread):
    """Background thread for importing tracks from Rekordbox."""

    progress_update = pyqtSignal(int, str)  # Value, message
    import_complete = pyqtSignal(int, int, list)  # Total imported, failed, errors
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(
        self,
        rekordbox_client: RekordboxClient,
        destination_folder: str,
        create_collection_playlist: bool = True,
        parent=None,
    ):
        """Initialize the import thread.

        Args:
            rekordbox_client: Rekordbox client instance
            destination_folder: Folder to copy files to
            create_collection_playlist: Whether to create a collection playlist
            parent: Parent object
        """
        super().__init__(parent)
        self.rekordbox_client = rekordbox_client
        self.destination_folder = destination_folder
        self.create_collection_playlist = create_collection_playlist
        self.cancelled = False

        # Repositories
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()

        # Statistics
        self.imported_count = 0
        self.failed_count = 0
        self.error_messages = []

    def cancel(self):
        """Cancel the import process."""
        self.cancelled = True

    def run(self):
        """Run the import process."""
        try:
            # Get all tracks from Rekordbox
            self.progress_update.emit(0, "Getting tracks from Rekordbox...")
            tracks = self.rekordbox_client.get_all_tracks()

            if not tracks:
                self.error_occurred.emit("No tracks found in Rekordbox")
                return

            # Calculate total
            total_tracks = len(tracks)
            self.progress_update.emit(0, f"Found {total_tracks} tracks in Rekordbox")
            time.sleep(0.5)  # Short pause to show message

            # Make sure the destination folder exists
            os.makedirs(self.destination_folder, exist_ok=True)

            # Create collection playlist if requested
            collection_playlist_id = None
            if self.create_collection_playlist:
                collection_playlist_id = self.playlist_repo.create_playlist(
                    "Rekordbox Collection", is_folder=False, parent_id=None
                )

            # Process each track
            for i, track in enumerate(tracks):
                if self.cancelled:
                    break

                # Update progress (0-100)
                progress = int((i / total_tracks) * 100)
                self.progress_update.emit(
                    progress, f"Processing track {i + 1} of {total_tracks}: {track.title}"
                )

                try:
                    # Import the track
                    if self._import_track(track):
                        # Add to collection playlist if created
                        if collection_playlist_id:
                            self.playlist_repo.add_track_to_playlist(
                                track.id, collection_playlist_id
                            )
                        self.imported_count += 1
                    else:
                        self.failed_count += 1
                except Exception as e:
                    self.failed_count += 1
                    error_msg = f"Error importing {track.title}: {str(e)}"
                    self.error_messages.append(error_msg)
                    logger.error(error_msg)

                # Small delay to prevent UI freezing
                time.sleep(0.01)

            # Final update
            self.progress_update.emit(100, "Import complete")
            self.import_complete.emit(self.imported_count, self.failed_count, self.error_messages)

        except Exception as e:
            logger.exception(f"Error in import thread: {e}")
            self.error_occurred.emit(f"Import error: {str(e)}")

    def _import_track(self, track: RekordboxTrack) -> bool:
        """Import a single track from Rekordbox.

        Args:
            track: The Rekordbox track to import

        Returns:
            True if successful, False otherwise
        """
        # Skip tracks without a location
        if not track.location:
            self.error_messages.append(f"Track {track.title} has no file location")
            return False

        # Check if the source file exists
        source_path = Path(track.location)
        if not source_path.exists():
            self.error_messages.append(f"Source file not found: {track.location}")
            return False

        # Determine destination path
        rel_path = source_path.name  # Just the filename
        dest_path = Path(self.destination_folder) / rel_path

        # Copy file if it doesn't exist
        if not dest_path.exists():
            try:
                shutil.copy2(source_path, dest_path)
            except Exception as e:
                self.error_messages.append(f"Error copying file {track.location}: {str(e)}")
                return False

        # Record the local path
        local_path = str(dest_path)

        # Check if track already exists with this Rekordbox ID
        existing_track = self.track_repo.get_by_platform_id("rekordbox", track.id)

        if existing_track:
            # Update existing track
            self.track_repo.update_track(
                existing_track.id,
                {
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "genre": track.genre,
                    "duration": track.duration,
                    "local_path": local_path,
                },
            )
            # Update Rekordbox metadata
            self.track_repo.set_track_attribute(
                existing_track.id, TrackAttribute.REKORDBOX_ID, track.id
            )
            track_id = existing_track.id
        else:
            # Create new track
            track_id = self.track_repo.create_track(
                title=track.title,
                artist=track.artist,
                album=track.album,
                genre=track.genre,
                duration=track.duration,
                local_path=local_path,
            )

            # Add Rekordbox metadata
            self.track_repo.set_track_attribute(track_id, TrackAttribute.REKORDBOX_ID, track.id)

        return True


class ImportRekordboxDialog(QDialog):
    """Dialog for importing tracks from Rekordbox."""

    def __init__(self, parent=None):
        """Initialize the import dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Import from Rekordbox")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        # Initialize repositories
        self.settings_repo = SettingsRepository()

        # Get RekordboxClient
        self.rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)

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
            "This will import tracks from your Rekordbox database into Selecta. "
            "Audio files will be copied to your local database folder.\n\n"
            "This may take a while depending on the number of tracks."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Options
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        self.create_collection_checkbox = QCheckBox("Create Rekordbox Collection playlist")
        self.create_collection_checkbox.setChecked(True)
        options_layout.addWidget(self.create_collection_checkbox)

        layout.addWidget(options_group)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to import")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.import_button = QPushButton("Start Import")
        self.import_button.setDefault(True)
        self.import_button.clicked.connect(self._start_import)
        button_layout.addWidget(self.import_button)

        layout.addLayout(button_layout)

    def _start_import(self):
        """Start the import process."""
        # Disable the import button
        self.import_button.setEnabled(False)

        # Get options
        create_collection = self.create_collection_checkbox.isChecked()

        # Create and start the import thread
        self.import_thread = ImportThread(
            self.rekordbox_client, self.local_folder, create_collection, self
        )

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

    def _import_complete(self, imported: int, failed: int, errors: list):
        """Handle import completion."""
        # Re-enable import button
        self.import_button.setEnabled(True)

        # Change cancel button back to close
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

        # Show a summary
        if failed == 0 and imported == 0:
            QMessageBox.information(self, "Import Complete", "No tracks were imported.")
        elif failed == 0:
            QMessageBox.information(
                self, "Import Complete", f"Successfully imported {imported} tracks."
            )
        else:
            error_text = "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n...and {len(errors) - 10} more errors"

            QMessageBox.warning(
                self,
                "Import Complete with Issues",
                f"Imported {imported} tracks, {failed} failed.\n\n"
                f"Some common issues include missing files or permission problems.\n\n"
                f"First few errors:\n{error_text}",
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
