# src/selecta/ui/components/import_rekordbox_dialog.py
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
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()

        # Keep track of our collection playlist ID
        self.collection_playlist_id = None

        # Statistics
        self.succeeded = 0
        self.failed = 0
        self.errors = []

    def cancel(self):
        """Cancel the import process."""
        self.cancelled = True

    def run(self):
        """Run the import process."""
        try:
            # Get all tracks from Rekordbox
            self.progress_update.emit(0, "Fetching tracks from Rekordbox...")
            all_tracks = self.rekordbox_client.get_all_tracks()

            if not all_tracks:
                self.error_occurred.emit("No tracks found in Rekordbox")
                return

            # Create collection playlist if needed
            if self.create_collection_playlist:
                self._ensure_collection_playlist()

            # Calculate total
            total_tracks = len(all_tracks)
            self.progress_update.emit(0, f"Found {total_tracks} tracks in Rekordbox")

            # Create destination folder if it doesn't exist
            os.makedirs(self.destination_folder, exist_ok=True)

            # Process each track
            for i, track in enumerate(all_tracks):
                if self.cancelled:
                    break

                # Update progress (0-100)
                progress = int((i / total_tracks) * 100)
                self.progress_update.emit(
                    progress, f"Importing track {i + 1} of {total_tracks}: {track.title}"
                )

                # Process the track
                success = self._import_track(track)
                if success:
                    self.succeeded += 1
                else:
                    self.failed += 1

                # Small delay to prevent UI freezing
                time.sleep(0.01)

            # Final update
            self.progress_update.emit(100, "Import complete")
            self.import_complete.emit(self.succeeded, self.failed, self.errors)

        except Exception as e:
            logger.exception(f"Error in import thread: {e}")
            self.error_occurred.emit(f"Import error: {str(e)}")

    def _ensure_collection_playlist(self):
        """Create or get the collection playlist."""
        try:
            # Check if collection playlist already exists
            playlists = self.playlist_repo.get_all()
            for playlist in playlists:
                if playlist.name == "Collection" and not playlist.is_folder:
                    self.collection_playlist_id = playlist.id
                    self.progress_update.emit(0, "Using existing Collection playlist")
                    return

            # Create the collection playlist
            playlist_data = {
                "name": "Collection",
                "description": "Tracks imported from Rekordbox",
                "is_local": True,
                "source_platform": None,  # This is our own playlist
            }

            new_playlist = self.playlist_repo.create(playlist_data)
            self.collection_playlist_id = new_playlist.id
            self.progress_update.emit(0, "Created new Collection playlist")

        except Exception as e:
            logger.exception(f"Error ensuring collection playlist: {e}")
            self.error_occurred.emit(f"Error creating collection playlist: {str(e)}")

    def _import_track(self, track: RekordboxTrack) -> bool:
        """Import a single track from Rekordbox.

        Args:
            track: Rekordbox track to import

        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip tracks without a path
            if not track.folder_path:
                self.errors.append(f"No file path for track: {track.artist_name} - {track.title}")
                return False

            # Check if file exists
            source_path = Path(track.folder_path)
            if not source_path.exists():
                self.errors.append(f"File not found: {track.folder_path}")
                return False

            # Check if we already have this track in the database with rekordbox info
            existing_track = self.track_repo.get_by_platform_id("rekordbox", str(track.id))

            if existing_track:
                # Track exists - update with any new metadata
                self._update_existing_track(existing_track, track)

                # Add to collection playlist if needed
                if self.collection_playlist_id:
                    # Check if already in collection
                    playlist_tracks = self.playlist_repo.get_playlist_tracks(
                        self.collection_playlist_id
                    )
                    if existing_track.id not in [t.id for t in playlist_tracks]:
                        # Add to collection
                        self.playlist_repo.add_track(self.collection_playlist_id, existing_track.id)
                return True

            # This is a new track, create a clean filename
            # Replace any characters that might cause issues in filenames
            clean_artist = "".join(c for c in track.artist_name if c.isalnum() or c in " -_.")
            clean_title = "".join(c for c in track.title if c.isalnum() or c in " -_.")

            # Get file extension
            file_extension = source_path.suffix.lower()

            # Create destination filename
            dest_filename = f"{clean_artist} - {clean_title}{file_extension}"
            dest_path = Path(self.destination_folder) / dest_filename

            # Make sure we don't overwrite existing files with the same name
            counter = 1
            original_dest_path = dest_path
            while dest_path.exists():
                dest_path = original_dest_path.with_stem(f"{original_dest_path.stem}_{counter}")
                counter += 1

            # Copy the file
            shutil.copy2(source_path, dest_path)

            # Create track in the database
            track_data = {
                "title": track.title,
                "artist": track.artist_name,
                "duration_ms": track.duration_ms,
                "local_path": str(dest_path),
            }

            # Add album info if available
            if track.album_name:
                # This should be improved to use a proper album model
                # but for simplicity, we're just storing the name for now
                track_data["album_id"] = None

            # Create the track
            new_track = self.track_repo.create(track_data)

            # Add the metadata to the new track
            self._add_track_metadata(new_track.id, track)

            # Add to collection playlist if needed
            if self.collection_playlist_id:
                self.playlist_repo.add_track(self.collection_playlist_id, new_track.id)

            return True

        except Exception as e:
            error_msg = f"Error importing {track.artist_name} - {track.title}: {str(e)}"
            logger.exception(error_msg)
            self.errors.append(error_msg)
            return False

    def _update_existing_track(self, existing_track, rekordbox_track: RekordboxTrack):
        """Update an existing track with any new metadata from Rekordbox.

        Args:
            existing_track: The existing track in our database
            rekordbox_track: The track data from Rekordbox
        """
        try:
            # Update basic track info if needed
            updated = False
            track_data = {}

            # Only update if different
            if existing_track.title != rekordbox_track.title:
                track_data["title"] = rekordbox_track.title
                updated = True

            if existing_track.artist != rekordbox_track.artist_name:
                track_data["artist"] = rekordbox_track.artist_name
                updated = True

            if (
                existing_track.duration_ms != rekordbox_track.duration_ms
                and rekordbox_track.duration_ms
            ):
                track_data["duration_ms"] = rekordbox_track.duration_ms
                updated = True

            if updated:
                self.track_repo.update(existing_track.id, track_data, preserve_existing=True)

            # Update attributes and metadata
            self._add_track_metadata(existing_track.id, rekordbox_track)

        except Exception as e:
            logger.exception(f"Error updating track metadata: {e}")
            self.errors.append(
                f"Error updating metadata for {rekordbox_track.artist_name}"
                f" - {rekordbox_track.title}: {str(e)}"
            )

    def _add_track_metadata(self, track_id: int, rekordbox_track: RekordboxTrack):
        """Add or update metadata for a track.

        Args:
            track_id: ID of the track in our database
            rekordbox_track: The track data from Rekordbox
        """
        # Make sure we have a fresh session after any potential errors
        self.track_repo.session.rollback()

        try:
            # Add BPM as a track attribute if available
            if rekordbox_track.bpm is not None:
                # Check if attribute already exists
                existing_attr = (
                    self.track_repo.session.query(TrackAttribute)
                    .filter(TrackAttribute.track_id == track_id, TrackAttribute.name == "bpm")
                    .first()
                )

                if existing_attr:
                    # Update if different
                    if existing_attr.value != float(rekordbox_track.bpm):
                        existing_attr.value = float(rekordbox_track.bpm)
                        existing_attr.source = "rekordbox"
                        self.track_repo.session.commit()
                else:
                    # Add new attribute
                    self.track_repo.add_attribute(
                        track_id, "bpm", float(rekordbox_track.bpm), "rekordbox"
                    )

            # Add key as a track attribute if available - treated as a STRING
            if rekordbox_track.key:
                # For key, we need a different approach since it's a string, not a float
                # First, we'll create an attribute with a different name to avoid type conflict
                key_attr_name = "musical_key"  # Use a different name for the key attribute

                existing_attr = (
                    self.track_repo.session.query(TrackAttribute)
                    .filter(
                        TrackAttribute.track_id == track_id, TrackAttribute.name == key_attr_name
                    )
                    .first()
                )

                if existing_attr:
                    # Convert to numeric representation for storage
                    key_numeric = self._key_to_numeric(rekordbox_track.key)

                    if existing_attr.value != key_numeric:
                        existing_attr.value = key_numeric
                        existing_attr.source = "rekordbox"
                        self.track_repo.session.commit()
                else:
                    # Convert key to numeric value for storage
                    key_numeric = self._key_to_numeric(rekordbox_track.key)

                    # Add key as numeric value
                    self.track_repo.add_attribute(track_id, key_attr_name, key_numeric, "rekordbox")

                # Also store the original string value in a separate field
                # This is optional - you can choose how to best represent this data
                existing_attr = (
                    self.track_repo.session.query(TrackAttribute)
                    .filter(
                        TrackAttribute.track_id == track_id, TrackAttribute.name == "key_notation"
                    )
                    .first()
                )

                if existing_attr:
                    if str(existing_attr.value) != rekordbox_track.key:
                        existing_attr.value = 0.0  # Placeholder value
                        existing_attr.source = "rekordbox"
                        self.track_repo.session.commit()

                        # Update the metadata to include the key string
                        key_info = self.track_repo.get_platform_info(track_id, "rekordbox")
                        if key_info and key_info.platform_data:
                            try:
                                import json

                                metadata = json.loads(key_info.platform_data)
                                metadata["key_notation"] = rekordbox_track.key
                                key_info.platform_data = json.dumps(metadata)
                                self.track_repo.session.commit()
                            except Exception as e:
                                logger.warning(f"Error updating key notation in metadata: {e}")
                else:
                    # Don't store as attribute, just in the metadata
                    pass

            # Add genre if available
            if rekordbox_track.genre:
                from selecta.core.data.models.db import Genre, Track

                # Get the track
                track = self.track_repo.session.query(Track).get(track_id)

                # Check if genre already exists in the database
                genre_obj = (
                    self.track_repo.session.query(Genre)
                    .filter(Genre.name == rekordbox_track.genre)
                    .first()
                )

                if not genre_obj:
                    # Create new genre
                    genre_obj = Genre(name=rekordbox_track.genre, source="rekordbox")
                    self.track_repo.session.add(genre_obj)
                    self.track_repo.session.commit()

                # Check if track already has this genre
                if genre_obj not in track.genres:
                    # Associate track with genre
                    track.genres.append(genre_obj)
                    self.track_repo.session.commit()

            # Update rekordbox platform info with metadata
            import json

            platform_metadata = {
                "bpm": rekordbox_track.bpm,
                "key": rekordbox_track.key,  # Store original key string in metadata
                "rating": rekordbox_track.rating,
                "genre": rekordbox_track.genre,
                "created_at": rekordbox_track.created_at.isoformat()
                if rekordbox_track.created_at
                else None,
            }

            # Get existing platform info
            existing_info = self.track_repo.get_platform_info(track_id, "rekordbox")

            if existing_info:
                # Update existing info
                self.track_repo.add_platform_info(
                    track_id,
                    "rekordbox",
                    str(rekordbox_track.id),
                    None,  # No URI for rekordbox
                    json.dumps(platform_metadata),  # Updated metadata
                )
            else:
                # Add new platform info
                self.track_repo.add_platform_info(
                    track_id,
                    "rekordbox",
                    str(rekordbox_track.id),
                    None,  # No URI for rekordbox
                    json.dumps(platform_metadata),  # Store additional metadata
                )
        except Exception as e:
            logger.exception(f"Error adding track metadata: {e}")
            # Make sure to rollback the session
            self.track_repo.session.rollback()
            raise

    def _key_to_numeric(self, key_str: str) -> float:
        """Convert a musical key string to a numeric value.

        This allows storing key information in the float-based attribute table.

        Args:
            key_str: Key string (e.g., '8m', '1d', etc.)

        Returns:
            Numeric representation of the key
        """
        # First map the key to Camelot notation
        # This creates a number from 1-12 with either A (major) or B (minor) suffix
        camelot_map = {
            # Major keys (Camelot "B" keys)
            "1d": 1.1,  # C major - 1B
            "8d": 2.1,  # G major - 2B
            "3d": 3.1,  # D major - 3B
            "10d": 4.1,  # A major - 4B
            "5d": 5.1,  # E major - 5B
            "12d": 6.1,  # B major - 6B
            "7d": 7.1,  # F# major - 7B
            "2d": 8.1,  # Db major - 8B
            "9d": 9.1,  # Ab major - 9B
            "4d": 10.1,  # Eb major - 10B
            "11d": 11.1,  # Bb major - 11B
            "6d": 12.1,  # F major - 12B
            # Minor keys (Camelot "A" keys)
            "10m": 1.0,  # A minor - 1A
            "5m": 2.0,  # E minor - 2A
            "12m": 3.0,  # B minor - 3A
            "7m": 4.0,  # F# minor - 4A
            "2m": 5.0,  # C# minor - 5A
            "9m": 6.0,  # G# minor - 6A
            "4m": 7.0,  # D# minor - 7A
            "11m": 8.0,  # A# minor - 8A
            "6m": 9.0,  # F minor - 9A
            "1m": 10.0,  # C minor - 10A
            "8m": 11.0,  # G minor - 11A
            "3m": 12.0,  # D minor - 12A
        }

        # Handle potential case issues and standardize format
        normalized_key = key_str.lower().strip()

        # Return mapped value or default to 0.0 if key not recognized
        return camelot_map.get(normalized_key, 0.0)


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

        # Initialize repositories and clients
        self.settings_repo = SettingsRepository()
        self.rekordbox_client = PlatformFactory.create("rekordbox", self.settings_repo)

        if not self.rekordbox_client or not self.rekordbox_client.is_authenticated():
            QMessageBox.critical(
                self, "Rekordbox Not Authenticated", "Please authenticate with Rekordbox first."
            )
            self.reject()
            return

        # Get destination folder
        self.destination_folder = self.settings_repo.get_local_database_folder()
        if not self.destination_folder:
            QMessageBox.critical(
                self, "No Destination Folder", "Please select a local database folder first."
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
            "This will import tracks from your Rekordbox collection to your local database.\n\n"
            "Tracks will be copied to your local database folder "
            "and added to a 'Collection' playlist."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Options group
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        self.create_collection_checkbox = QCheckBox("Add tracks to Collection playlist")
        self.create_collection_checkbox.setChecked(True)
        options_layout.addWidget(self.create_collection_checkbox)

        layout.addWidget(options_group)

        # Destination folder
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)

        folder_label = QLabel("Destination folder:")
        folder_layout.addWidget(folder_label)

        self.folder_path_label = QLabel(self.destination_folder)
        self.folder_path_label.setStyleSheet("font-weight: bold;")
        folder_layout.addWidget(self.folder_path_label, 1)  # 1 = stretch

        layout.addLayout(folder_layout)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to import")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch(1)

        self.import_button = QPushButton("Start Import")
        self.import_button.setDefault(True)
        self.import_button.clicked.connect(self._start_import)
        button_layout.addWidget(self.import_button)

        layout.addLayout(button_layout)

    def _start_import(self):
        """Start the import process."""
        # Disable the import button
        self.import_button.setEnabled(False)

        # Create and start the import thread
        self.import_thread = ImportThread(
            self.rekordbox_client,
            self.destination_folder,
            self.create_collection_checkbox.isChecked(),
            self,
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

    def _import_complete(self, succeeded: int, failed: int, errors: list):
        """Handle import completion."""
        # Re-enable import button
        self.import_button.setEnabled(True)

        # Change cancel button back to close
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

        # Show a summary
        if failed == 0:
            QMessageBox.information(
                self, "Import Complete", f"Successfully imported {succeeded} tracks."
            )
        else:
            details = "\n".join(errors[:10])
            if len(errors) > 10:
                details += f"\n...and {len(errors) - 10} more errors."

            QMessageBox.warning(
                self,
                "Import Complete with Errors",
                f"Imported {succeeded} tracks, {failed} failed.\n\nFirst few errors:\n{details}",
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
                "Are you sure you want to cancel the import?\n\n"
                "Tracks that have already been imported will remain in your database.",
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
