from typing import Any

from loguru import logger
from PyQt6.QtCore import QBuffer, QByteArray, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.database import get_session
from selecta.core.data.models.db import ImageSize, Track
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.path_helper import get_resource_path
from selecta.ui.components.common.image_loader import DatabaseImageLoader
from selecta.ui.components.common.selection_state import SelectionState
from selecta.ui.components.playlist.base_items import BaseTrackItem


class PlatformButton(QPushButton):
    """Button that represents a platform with an icon."""

    def __init__(self, platform: str, parent=None):
        """Initialize the platform button.

        Args:
            platform: Platform name
            parent: Parent widget
        """
        super().__init__(parent)
        self.platform = platform
        self.setToolTip(f"Use data from {platform.capitalize()}")
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Load platform icon
        self._load_icon()

    def _load_icon(self) -> None:
        """Load the platform icon."""
        try:
            # Try different icon paths
            icon_paths = [
                # Try full size first
                f"icons/1x/{self.platform}.png",
                # Then smaller sizes as fallback
                f"icons/0.5x/{self.platform}@0.5x.png",
                f"icons/0.25x/{self.platform}@0.25x.png",
            ]

            for icon_path in icon_paths:
                resource_path = get_resource_path(icon_path)
                icon = QIcon(str(resource_path))
                if not icon.isNull():
                    self.setIcon(icon)
                    return

            # Fallback to text if no icon found
            self.setText(self.platform[0].upper())
        except Exception as e:
            logger.error(f"Error loading platform icon for {self.platform}: {e}")
            self.setText(self.platform[0].upper())


class MetadataField(QWidget):
    """Widget for a single metadata field with platform suggestions."""

    # Signal when the field value is changed
    value_changed = pyqtSignal(str, str)  # field_name, new_value

    def __init__(self, name: str, display_name: str, value: str, parent=None):
        """Initialize the metadata field.

        Args:
            name: Field name (e.g., "title")
            display_name: Display name (e.g., "Title")
            value: Current value
            parent: Parent widget
        """
        super().__init__(parent)
        self.name = name
        self.display_name = display_name
        self.original_value = value
        self.current_value = value
        self.platform_values: dict[str, str] = {}  # Values from different platforms

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Field label
        label_layout = QHBoxLayout()
        label = QLabel(f"{display_name}:")
        label.setStyleSheet("font-weight: bold;")

        label_layout.addWidget(label)
        label_layout.addStretch(1)

        # Platform buttons container (initially empty)
        self.platform_container = QWidget()
        self.platform_layout = QHBoxLayout(self.platform_container)
        self.platform_layout.setContentsMargins(0, 0, 0, 0)
        self.platform_layout.setSpacing(4)

        label_layout.addWidget(self.platform_container)
        layout.addLayout(label_layout)

        # Field value with editing
        edit_layout = QHBoxLayout()

        self.value_edit = QLineEdit(value)
        self.value_edit.textChanged.connect(self._on_text_changed)

        # Reset button (initially hidden)
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset to original value")
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.reset_button.setVisible(False)
        self.reset_button.setFixedWidth(60)

        edit_layout.addWidget(self.value_edit)
        edit_layout.addWidget(self.reset_button)
        layout.addLayout(edit_layout)

    def add_platform_suggestion(self, platform: str, value: str) -> None:
        """Add a platform suggestion button.

        Args:
            platform: Platform name (e.g., "spotify")
            value: Value from this platform
        """
        if not value or value == self.current_value:
            return

        self.platform_values[platform] = value

        # Create button for this platform
        platform_button = PlatformButton(platform)
        platform_button.setToolTip(f"Use '{value}' from {platform.capitalize()}")
        platform_button.clicked.connect(lambda: self._on_platform_clicked(platform))

        # Add to container
        self.platform_layout.addWidget(platform_button)
        self.platform_container.setVisible(True)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes in the edit field.

        Args:
            text: New text value
        """
        self.current_value = text
        self.reset_button.setVisible(text != self.original_value)
        self.value_changed.emit(self.name, text)

    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        self.value_edit.setText(self.original_value)
        self.current_value = self.original_value
        self.reset_button.setVisible(False)

    def _on_platform_clicked(self, platform: str) -> None:
        """Handle platform button click.

        Args:
            platform: Platform that was clicked
        """
        platform_value = self.platform_values.get(platform)
        if platform_value:
            self.value_edit.setText(platform_value)

            # Hide this platform button since we've used its value
            for i in range(self.platform_layout.count()):
                item = self.platform_layout.itemAt(i)
                if item is not None:
                    button = item.widget()
                    if isinstance(button, PlatformButton) and button.platform == platform:
                        button.setVisible(False)


class TrackDetailsPanel(QWidget):
    """Panel displaying detailed information about a track with metadata editing capabilities."""

    # Shared image loader
    _db_image_loader = None

    # Signal emitted when track quality is changed
    quality_changed = pyqtSignal(int, int)  # track_id, new_quality

    # Signal emitted when panel is refreshed
    panel_refreshed = pyqtSignal(int)  # track_id

    # Signal emitted when track is updated
    track_updated = pyqtSignal(int)  # track_id

    def __init__(self, parent=None):
        """Initialize the track details panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setObjectName("trackDetailsPanel")  # Set object name for finding in hierarchy

        # Track we're currently displaying
        self._current_track_id = None
        self._current_album_id = None
        self._current_quality = -1  # NOT_RATED by default
        self._refreshing = False  # Flag to prevent recursive refresh
        self._editing_mode = False  # Whether we're in editing mode
        self._changed_fields: set[str] = set()  # Fields that have been changed
        self._metadata_fields: dict[str, MetadataField] = {}  # Field widgets
        self._platform_info: dict[str, Any] = {}  # Platform info for the current track
        self._image_just_saved = False  # Flag to prevent image refresh after saving
        self._saved_image_track_id = None  # Track ID that we just saved an image for

        # Initialize the database image loader if needed
        if TrackDetailsPanel._db_image_loader is None:
            TrackDetailsPanel._db_image_loader = DatabaseImageLoader()

        # Connect to image loader signals
        TrackDetailsPanel._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
        TrackDetailsPanel._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

        # Set up the UI
        layout = QVBoxLayout(self)

        # Header
        self.header_label = QLabel("Track Details")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.header_label)

        # Album artwork
        self.image_container = QWidget()
        self.image_layout = QVBoxLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Image display
        image_display = QWidget()
        image_display_layout = QHBoxLayout(image_display)
        image_display_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        image_display_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Set placeholder
        placeholder = QPixmap(200, 200)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.image_label.setPixmap(placeholder)

        image_display_layout.addWidget(self.image_label)
        self.image_layout.addWidget(image_display)

        # Platform covers container
        self.platform_covers_container = QWidget()
        self.platform_covers_layout = QHBoxLayout(self.platform_covers_container)
        self.platform_covers_layout.setContentsMargins(0, 0, 0, 0)
        self.platform_covers_layout.setSpacing(8)
        self.platform_covers_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.platform_covers_container.setVisible(False)
        self.image_layout.addWidget(self.platform_covers_container)

        # Label for platform covers
        self.covers_label = QLabel("Select cover image from:")
        self.covers_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.platform_covers_layout.addWidget(self.covers_label)

        # Reset button for cover
        self.reset_cover_button = QPushButton("Reset")
        self.reset_cover_button.setToolTip("Reset to original cover")
        self.reset_cover_button.clicked.connect(self._on_reset_cover)
        self.reset_cover_button.setVisible(False)
        self.image_layout.addWidget(self.reset_cover_button, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(self.image_container)

        # Quality rating section
        quality_container = QWidget()
        quality_layout = QVBoxLayout(quality_container)

        # Label for the quality section
        quality_label = QLabel("Quality Rating:")
        quality_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        quality_layout.addWidget(quality_label)

        # Quality selector dropdown
        quality_selection = QHBoxLayout()

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Not Rated", -1)
        self.quality_combo.addItem("★ Very Poor", 1)
        self.quality_combo.addItem("★★ Poor", 2)
        self.quality_combo.addItem("★★★ OK", 3)
        self.quality_combo.addItem("★★★★ Good", 4)
        self.quality_combo.addItem("★★★★★ Great", 5)

        # Connect the quality change signal
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)

        quality_selection.addWidget(self.quality_combo)
        quality_layout.addLayout(quality_selection)

        layout.addWidget(quality_container)

        # Create scroll area for metadata fields
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for metadata fields
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)  # Push fields to the top

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor

        # Action buttons at the bottom
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.update_from_platforms_button = QPushButton("Update From Platforms")
        self.update_from_platforms_button.clicked.connect(self._on_update_from_platforms)

        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self._on_apply_changes)
        self.apply_button.setVisible(False)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_changes)
        self.cancel_button.setVisible(False)

        button_layout.addWidget(self.update_from_platforms_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)

        layout.addWidget(button_container)

        # Connect to the global selection state
        self.selection_state = SelectionState()
        self.selection_state.track_updated.connect(self._on_track_updated)

    def set_track(self, track: BaseTrackItem | None, platform_info: dict[str, Any] | None = None):
        """Set the track to display.

        Args:
            track: Track item to display details for, or None to clear
            platform_info: Optional dictionary of platform info objects keyed by platform name
        """
        # Exit editing mode if we're switching tracks
        if track and (not self._current_track_id or self._current_track_id != track.track_id):
            self._exit_editing_mode()

        # If we're displaying the same track and just saved a new image,
        # we want to skip clearing the image and keep our saved version
        same_track_with_saved_image = (
            track
            and self._current_track_id == track.track_id
            and self._image_just_saved
            and self._saved_image_track_id == track.track_id
        )

        # Clear existing fields
        self._clear_metadata_fields()

        # Only reset the image if we're not keeping a just-saved image
        if not same_track_with_saved_image:
            self._reset_image_to_placeholder()
        else:
            logger.debug("Keeping current image for track that just had image saved")
            # Reset the flag since we've handled it
            self._image_just_saved = False

        if not track:
            self.header_label.setText("No Track Selected")
            self._current_track_id = None
            self._current_album_id = None
            self._platform_info = {}

            # Reset quality dropdown
            self.quality_combo.setCurrentIndex(0)  # Not rated
            self.quality_combo.setEnabled(False)
            self._current_quality = -1

            # Hide buttons
            self.update_from_platforms_button.setVisible(False)
            self.apply_button.setVisible(False)
            self.cancel_button.setVisible(False)
            return

        # Update header with track info
        self.header_label.setText(f"{track.artist} - {track.title}")

        # Show platform update button
        self.update_from_platforms_button.setVisible(True)

        # Fetch platform info from database
        self._fetch_platform_info(track)

        # Store the platform info for later use
        if platform_info:
            self._platform_info = platform_info

        # Create metadata fields from track data
        self._create_metadata_fields(track)

        # Set track ID and album ID
        self._current_track_id = track.track_id
        self._current_album_id = track.album_id

        # Set quality rating if available
        display_data = track.to_display_data()
        quality = display_data.get("quality", -1)
        self._current_quality = quality

        # Set the quality dropdown to the track's quality
        self.quality_combo.blockSignals(True)  # Prevent triggering the signal during setup

        # Find the index for the current quality value
        index = self.quality_combo.findData(quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
        else:
            logger.warning(f"Quality {quality} not found in combo box, defaulting to NOT_RATED")
            self.quality_combo.setCurrentIndex(0)  # Default to "Not Rated"

        self.quality_combo.blockSignals(False)
        self.quality_combo.setEnabled(True)

        # Load images
        self._load_track_images(track)

    def _fetch_platform_info(self, track: BaseTrackItem) -> None:
        """Fetch platform info for a track from the database.

        Args:
            track: Track item to get platform info for
        """
        try:
            # Create fresh session
            session = get_session()
            track_repo = TrackRepository(session)

            # Get platform info for all platforms
            platform_info = {}
            for platform in ["spotify", "discogs", "youtube", "rekordbox"]:
                info = track_repo.get_platform_info(track.track_id, platform)
                if info:
                    platform_info[platform] = info
                    logger.info(f"Found platform info for {platform}: platform_id={info.platform_id}")

            # Store platform info
            self._platform_info = platform_info
        except Exception as e:
            logger.error(f"Error fetching platform info: {e}")
            self._platform_info = {}

    def _create_metadata_fields(self, track: BaseTrackItem) -> None:
        """Create metadata fields from track data.

        Args:
            track: Track item to create fields for
        """
        # Get track data
        display_data = track.to_display_data()

        # Get genres and tags for this track
        genres = []
        tags = []
        session = get_session()
        track_repo = TrackRepository(session)
        db_track = track_repo.get_by_id(track.track_id)
        if db_track:
            # Get genres as comma-separated string
            genres = [genre.name for genre in db_track.genres] if db_track.genres else []
            # Get tags as comma-separated string
            tags = [tag.name for tag in db_track.tags] if db_track.tags else []

        # Get country from platform metadata
        country = ""
        # Try to get from platform metadata
        for _, platform_info in self._platform_info.items():
            platform_metadata = self._get_platform_metadata(platform_info)
            if platform_metadata and "country" in platform_metadata:
                country = platform_metadata["country"]
                break

        # Create fields with current values
        fields_config = [
            ("title", "Title", display_data.get("title", "")),
            ("artist", "Artist", display_data.get("artist", "")),
            ("album", "Album", display_data.get("album_name", "")),
            ("year", "Year", str(display_data.get("year", "")) if display_data.get("year") else ""),
            ("bpm", "BPM", str(display_data.get("bpm", "")) if display_data.get("bpm") else ""),
            ("country", "Country", country),
            ("genres", "Genres", ", ".join(genres)),
            ("tags", "Tags", ", ".join(tags)),
        ]

        for field_name, display_name, value in fields_config:
            # Create field widget
            field = MetadataField(field_name, display_name, value)
            field.value_changed.connect(self._on_field_value_changed)

            # Add to layout
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, field)

            # Save reference
            self._metadata_fields[field_name] = field

    def _on_field_value_changed(self, field_name: str, new_value: str) -> None:
        """Handle field value changes.

        Args:
            field_name: Name of the changed field
            new_value: New value for the field
        """
        # Add to changed fields set
        self._changed_fields.add(field_name)

        # Show apply/cancel buttons if we have changes
        if self._changed_fields:
            self._enter_editing_mode()
        else:
            self._exit_editing_mode()

    def _on_update_from_platforms(self) -> None:
        """Handle update from platforms button click."""
        if not self._current_track_id or not self._platform_info:
            return

        logger.info("Updating metadata from platforms")

        # Process platform data to find alternative values
        for platform_name, platform_info in self._platform_info.items():
            if not platform_info:
                continue

            # Extract metadata from platform_data
            platform_metadata = self._get_platform_metadata(platform_info)
            if not platform_metadata:
                continue

            # Add platform values to each field
            self._add_platform_values_to_fields(platform_name, platform_metadata)

        # Add platform covers
        self._add_platform_covers()

        # Enter editing mode
        self._enter_editing_mode()

    def _get_platform_metadata(self, platform_info: Any) -> dict[str, Any]:
        """Extract metadata from platform info.

        Args:
            platform_info: Platform info object

        Returns:
            Dictionary of metadata
        """
        if not platform_info:
            return {}

        # Try to get platform_data JSON
        if hasattr(platform_info, "platform_data") and platform_info.platform_data:
            import json

            try:
                return json.loads(platform_info.platform_data)
            except json.JSONDecodeError:
                pass

        return {}

    def _add_platform_values_to_fields(self, platform_name: str, platform_metadata: dict[str, Any]) -> None:
        """Add platform values to metadata fields.

        Args:
            platform_name: Name of the platform
            platform_metadata: Metadata from the platform
        """
        # Field mapping from platform metadata to our fields
        field_mappings = {
            "title": ["title", "name", "track_name"],
            "artist": ["artist", "artist_name", "artists"],
            "album": ["album", "album_name"],
            "year": ["year", "release_year", "release_date"],
            "bpm": ["bpm", "tempo"],
            "country": ["country", "release_country", "country_of_origin"],
            "genres": ["genres", "genre", "styles", "tags"],
        }

        # For each field, check if we have a value in platform metadata
        for field_name, platform_keys in field_mappings.items():
            if field_name not in self._metadata_fields:
                continue

            field = self._metadata_fields[field_name]

            # Try each possible key
            for key in platform_keys:
                if key in platform_metadata and platform_metadata[key]:
                    # Convert to string if needed
                    value = str(platform_metadata[key])

                    # Special handling for arrays (like artists in Spotify)
                    if isinstance(platform_metadata[key], list):
                        if field_name == "artist":
                            # Join artist names with comma
                            value = ", ".join(platform_metadata[key])
                        elif field_name == "genres":
                            # Join genre names with comma
                            value = ", ".join(str(g) for g in platform_metadata[key])
                        else:
                            # Use first value for other fields
                            value = str(platform_metadata[key][0]) if platform_metadata[key] else ""

                    # Add suggestion if it's different from current value
                    if value and value != field.current_value:
                        field.add_platform_suggestion(platform_name, value)

                    break

    def _on_apply_changes(self) -> None:
        """Handle apply changes button click."""
        if not self._current_track_id or not self._changed_fields:
            return

        changes = ", ".join(self._changed_fields)
        logger.info(f"Applying metadata changes for track {self._current_track_id}: {changes}")

        try:
            # Store if we have image changes
            has_image_changes = "cover_image" in self._changed_fields and hasattr(self, "_selected_cover_data")

            # Get changed field values
            field_values = {}
            for field_name in self._changed_fields:
                if field_name in self._metadata_fields:
                    field = self._metadata_fields[field_name]
                    field_values[field_name] = field.current_value

            # Update track in database
            session = get_session()
            track_repo = TrackRepository(session)

            # Get track from database
            track = track_repo.get_by_id(self._current_track_id)
            if not track:
                logger.error(f"Track {self._current_track_id} not found in database")
                return

            # Update track fields first (text fields)
            self._update_track_fields(track, field_values)

            # Handle cover image update if selected - after text fields to avoid refresh issues
            if has_image_changes:
                cover_data = self._selected_cover_data
                if cover_data and "pixmap" in cover_data and "metadata" in cover_data:
                    # Process image in a way that avoids refresh issues
                    success = self._save_cover_image(track, cover_data["pixmap"], cover_data["metadata"])
                    if not success:
                        logger.warning("Failed to save cover image during apply changes")

            # Save only field changes, image changes are committed in _save_cover_image
            if not has_image_changes:
                session.commit()

            # Exit editing mode
            self._exit_editing_mode()

            # Notify that track was updated
            self.track_updated.emit(self._current_track_id)

            # Refresh the track data
            self._refresh_current_track()

        except Exception as e:
            logger.error(f"Error applying metadata changes: {e}")

    def _update_track_fields(self, track: Track, field_values: dict[str, str]) -> None:
        """Update track fields with new values.

        Args:
            track: Track to update
            field_values: New field values
        """
        # Update basic fields
        if "title" in field_values:
            track.title = field_values["title"]

        if "artist" in field_values:
            track.artist = field_values["artist"]

        if "year" in field_values:
            # Convert to int if possible
            try:
                if field_values["year"]:
                    track.year = int(field_values["year"])
                else:
                    track.year = None
            except ValueError:
                logger.warning(f"Invalid year value: {field_values['year']}")

        if "bpm" in field_values:
            # Convert to float if possible
            try:
                if field_values["bpm"]:
                    track.bpm = float(field_values["bpm"])
                else:
                    track.bpm = None
            except ValueError:
                logger.warning(f"Invalid BPM value: {field_values['bpm']}")

        # Country field - stored in platform_data for now
        if "country" in field_values:
            # Since we don't have a dedicated field for country in the Track model,
            # we'll update it in the platform_data for Discogs first, if available
            discogs_info = None
            for platform_info in track.platform_info:
                if platform_info.platform == "discogs":
                    discogs_info = platform_info
                    break

            if discogs_info and discogs_info.platform_data:
                try:
                    import json

                    data = json.loads(discogs_info.platform_data)
                    data["country"] = field_values["country"]
                    discogs_info.platform_data = json.dumps(data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Error updating country in platform data: {e}")

        # Genres field - parse the comma-separated list and update track's genres
        if "genres" in field_values and field_values["genres"]:
            # Create TrackRepository to handle genre operations
            from selecta.core.data.repositories.track_repository import TrackRepository

            track_repo = TrackRepository(session=None)  # We're already in a session

            # Split the comma-separated list
            genre_names = [g.strip() for g in field_values["genres"].split(",") if g.strip()]

            # Set the genres (this handles creating new genres if needed)
            if genre_names:
                # The source is 'user' since this is a manual edit
                track_repo.set_track_genres(track.id, genre_names, source="user")

        # Tags field - parse the comma-separated list and update track's tags
        if "tags" in field_values and field_values["tags"]:
            # Create TrackRepository to handle tag operations
            from selecta.core.data.repositories.track_repository import TrackRepository

            track_repo = TrackRepository(session=None)  # We're already in a session

            # Split the comma-separated list
            tag_names = [t.strip() for t in field_values["tags"].split(",") if t.strip()]

            # Remove all existing tags first
            for tag in list(track.tags):
                track.tags.remove(tag)

            # Add each tag
            for tag_name in tag_names:
                if tag_name:
                    tag = track_repo.get_or_create_tag(tag_name)
                    if tag not in track.tags:
                        track.tags.append(tag)

        # Album requires additional handling - update if we have an album
        if "album" in field_values and track.album:
            track.album.title = field_values["album"]

    def _on_cancel_changes(self) -> None:
        """Handle cancel changes button click."""
        logger.info("Canceling metadata changes")

        # Reset all fields to original values
        for _, field in self._metadata_fields.items():
            field.value_edit.setText(field.original_value)

        # Exit editing mode
        self._exit_editing_mode()

    def _enter_editing_mode(self) -> None:
        """Enter metadata editing mode."""
        self._editing_mode = True
        self.apply_button.setVisible(True)
        self.cancel_button.setVisible(True)
        self.update_from_platforms_button.setVisible(False)
        self.platform_covers_container.setVisible(True)

    def _exit_editing_mode(self) -> None:
        """Exit metadata editing mode."""
        self._editing_mode = False
        self._changed_fields.clear()
        self.apply_button.setVisible(False)
        self.cancel_button.setVisible(False)
        self.update_from_platforms_button.setVisible(self._current_track_id is not None)
        self.platform_covers_container.setVisible(False)
        self.reset_cover_button.setVisible(False)

        # Clear any platform buttons
        self._clear_platform_cover_buttons()

    def _refresh_current_track(self) -> None:
        """Refresh the current track display."""
        if not self._current_track_id:
            return

        # If we just saved an image and this is the same track, we don't want to refresh
        # the image because it would overwrite our selection with the old database version
        if self._image_just_saved and self._saved_image_track_id == self._current_track_id:
            logger.debug("Skipping image refresh after save to keep selected image")
            self._image_just_saved = False  # Reset flag
            return

        try:
            # Get the track from selection state
            selected_track = self.selection_state.get_selected_track()

            if not selected_track:
                logger.warning(f"Track {self._current_track_id} not found in selection state")
                return

            # Refresh the display
            self.set_track(selected_track)

        except Exception as e:
            logger.error(f"Error refreshing track: {e}")

    def _clear_metadata_fields(self) -> None:
        """Clear all metadata fields."""
        # Remove all widgets except the stretch at the end
        for _, field in self._metadata_fields.items():
            self.scroll_layout.removeWidget(field)
            field.setParent(None)
            field.deleteLater()

        self._metadata_fields.clear()
        self._changed_fields.clear()

        # Force layout update
        self.scroll_content.update()
        self.scroll_area.update()

    def _load_track_images(self, track: BaseTrackItem) -> None:
        """Load images for the track.

        Args:
            track: Track to load images for
        """
        # Check if this track actually has an image
        has_track_image = hasattr(track, "has_image") and track.has_image
        has_album_id = hasattr(track, "album_id") and track.album_id is not None

        # Only make the image container visible if the track has an image or album ID
        if not (has_track_image or has_album_id):
            # No image available, keep placeholder
            logger.debug(f"Track {track.track_id} has no image and no album ID")
            self.image_container.setVisible(False)
            return

        # Make the image container visible
        self.image_container.setVisible(True)

        # Check if we just saved an image for this track
        same_track_with_saved_image = self._image_just_saved and self._saved_image_track_id == track.track_id

        # Skip loading images if we have a newly saved image we want to keep
        if same_track_with_saved_image:
            logger.debug(f"Keeping newly saved image for track {track.track_id}")
            # We need the image container to be visible but don't load new images
            return

        # Load track image from database if available
        if has_track_image and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_track_image(track.track_id, ImageSize.MEDIUM)

        # Also try to load the album image as a fallback
        if has_album_id and TrackDetailsPanel._db_image_loader and track.album_id is not None:
            TrackDetailsPanel._db_image_loader.load_album_image(track.album_id, ImageSize.MEDIUM)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap) -> None:
        """Handle loaded image from database for a track.

        Args:
            track_id: The track ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to the current track
        if track_id == self._current_track_id:
            self.image_label.setPixmap(pixmap)
            self.image_container.setVisible(True)

    def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap) -> None:
        """Handle loaded image from database for an album.

        Args:
            album_id: The album ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to the current album and we don't already have a track image
        if album_id == self._current_album_id and self._current_track_id is not None:
            # Only use album image if we don't already have a track image
            # Check if the current pixmap is just our placeholder
            current_pixmap = self.image_label.pixmap()
            is_placeholder = current_pixmap.width() <= 200 and current_pixmap.height() <= 200

            if is_placeholder:
                self.image_label.setPixmap(pixmap)
                self.image_container.setVisible(True)

    @pyqtSlot(int)
    def _on_quality_changed(self, index: int) -> None:
        """Handle quality rating changes.

        Args:
            index: The index of the selected quality in the combo box
        """
        logger.debug(f"Quality dropdown changed to index {index}")

        if self._current_track_id is None:
            logger.warning("No track ID available, ignoring quality change")
            return

        # Get the quality value from the combo box
        quality_data = self.quality_combo.itemData(index)

        # Ensure we have an integer
        try:
            quality = quality_data if isinstance(quality_data, int) else int(quality_data)
        except (ValueError, TypeError):
            logger.error(f"Error converting quality data to int: {quality_data}")
            quality = -1  # Default to NOT_RATED

        logger.debug(f"Quality data value: {quality}")

        # Only update if the quality has actually changed
        if quality != self._current_quality:
            self._current_quality = quality
            logger.info(f"Updating quality in database: track_id={self._current_track_id}, quality={quality}")

            # Update the database directly
            session = get_session()
            track_repo = TrackRepository(session)

            # Update the quality
            success = track_repo.set_track_quality(self._current_track_id, quality)

            if success:
                logger.info(f"Quality updated successfully for track {self._current_track_id}")

                # Still emit the signal for any listeners that want to know about the change
                self.quality_changed.emit(self._current_track_id, quality)

                # Notify the global selection state that this track was updated
                SelectionState().notify_track_updated(self._current_track_id)
            else:
                logger.error(f"Failed to update quality for track {self._current_track_id}")
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Quality Update Failed",
                    f"Failed to update quality rating for track {self._current_track_id}.",
                )
        else:
            logger.debug(f"Quality unchanged from {self._current_quality}, not updating")

    def _reset_image_to_placeholder(self) -> None:
        """Reset the image display to a placeholder."""
        # Create a gray placeholder
        placeholder = QPixmap(200, 200)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.image_label.setPixmap(placeholder)

        # Hide the image container by default
        # It will be shown only if a valid image is loaded
        self.image_container.setVisible(False)
        self.platform_covers_container.setVisible(False)
        self.reset_cover_button.setVisible(False)

        # Clear selected cover data
        if hasattr(self, "_selected_cover_data"):
            self._selected_cover_data = None

    def _on_track_updated(self, track_id: int) -> None:
        """Handle track update notification from SelectionState.

        This method is called when track_updated signal is emitted.
        It refreshes the track details panel if the updated track is currently displayed.

        Args:
            track_id: ID of the track that was updated
        """
        # Skip if we're not displaying this track or already refreshing
        if self._current_track_id != track_id or self._refreshing:
            return

        logger.debug(f"Track details panel handling track update for track_id={track_id}")
        self._refreshing = True

        try:
            # Refresh the current track
            self._refresh_current_track()

            # Emit signal to notify that panel was refreshed
            self.panel_refreshed.emit(track_id)

        except Exception as e:
            logger.error(f"Error refreshing track details panel after track update: {e}")
        finally:
            self._refreshing = False

    def _add_platform_covers(self) -> None:
        """Add platform cover buttons for available cover images."""
        # Clear existing buttons first
        self._clear_platform_cover_buttons()

        # Get cover images from platforms
        platform_images = self._get_platform_images()
        if not platform_images:
            logger.warning("No platform images available for this track")
            return

        # Store original cover for potential reset
        self._original_cover = self.image_label.pixmap()

        # Create a button for each platform with cover images
        for platform_name, images in platform_images.items():
            if not images:
                continue

            # Create a button for this platform
            platform_button = PlatformButton(platform_name)
            platform_button.setToolTip(f"Use cover image from {platform_name.capitalize()}")

            # Connect click handler with platform and image data
            # Use first image for each platform
            image_data = images[0]
            platform_button.clicked.connect(
                lambda checked=False, p=platform_name, img=image_data: self._on_platform_cover_clicked(p, img)
            )

            # Add to container
            self.platform_covers_layout.addWidget(platform_button)

        # Make reset button visible if we have original cover
        if not self._original_cover.isNull():
            self.reset_cover_button.setVisible(True)

    def _clear_platform_cover_buttons(self) -> None:
        """Clear all platform cover buttons."""
        # Remove all widgets except the label
        for i in reversed(range(self.platform_covers_layout.count())):
            layout_item = self.platform_covers_layout.itemAt(i)
            if layout_item is not None:
                item = layout_item.widget()
                if item is not None and item != self.covers_label:  # Keep the label
                    item.setParent(None)
                    item.deleteLater()

    def _on_platform_cover_clicked(self, platform: str, image_data: dict) -> None:
        """Handle platform cover button click.

        Args:
            platform: Platform name
            image_data: Image metadata from platform
        """
        logger.info(f"Selected cover image from {platform}")

        try:
            # Download the image
            url = image_data.get("url")
            if not url:
                logger.error("No URL in image data")
                return

            # Create request with headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            from urllib.request import Request, urlopen

            req = Request(url, headers=headers)

            # Download the image
            with urlopen(req, timeout=10) as response:
                image_data_bytes = response.read()

            # Create pixmap from image data
            pixmap = QPixmap()
            pixmap.loadFromData(image_data_bytes)

            if pixmap.isNull():
                logger.error("Failed to load image from URL")
                return

            # Update the displayed image
            self.image_label.setPixmap(pixmap)

            # Store the image data for later saving
            self._selected_cover_data = {
                "pixmap": pixmap,
                "metadata": {"url": url, "source": platform},
            }

            # Add to changed fields to trigger save
            self._changed_fields.add("cover_image")

        except Exception as e:
            logger.error(f"Error downloading cover image: {e}")

    def _on_reset_cover(self) -> None:
        """Reset cover image to original."""
        if hasattr(self, "_original_cover") and not self._original_cover.isNull():
            self.image_label.setPixmap(self._original_cover)

            # Remove from changed fields if it was added
            if "cover_image" in self._changed_fields:
                self._changed_fields.remove("cover_image")

            # Clear selected cover data
            self._selected_cover_data = None

    def _get_platform_images(self) -> dict:
        """Get image URLs from available platforms.

        Returns:
            Dictionary of platform image data
        """
        platform_images = {}
        logger.debug(f"Getting platform images from: {list(self._platform_info.keys())}")

        for platform_name, platform_info in self._platform_info.items():
            if not platform_info:
                continue

            # Get platform metadata
            platform_metadata = self._get_platform_metadata(platform_info)
            logger.debug(f"Platform metadata for {platform_name}: {platform_metadata}")
            if not platform_metadata:
                continue

            # Extract images based on platform
            if platform_name == "spotify":
                # Spotify has album images
                album_images = []
                # Check if we have album images in metadata
                if "album_images" in platform_metadata:
                    album_images = platform_metadata["album_images"]
                    logger.debug(f"Found album_images: {album_images}")
                elif "album" in platform_metadata and "images" in platform_metadata["album"]:
                    album_images = platform_metadata["album"]["images"]
                    logger.debug(f"Found album.images: {album_images}")
                # Check structure from SpotifySearchPanel
                elif "artwork_url" in platform_metadata:
                    # Format a single image as would be expected
                    artwork_url = platform_metadata["artwork_url"]
                    if artwork_url:
                        album_images = [{"url": artwork_url, "width": 640, "height": 640}]
                        logger.debug(f"Created image from artwork_url: {album_images}")

                if album_images:
                    platform_images["spotify"] = album_images

            elif platform_name == "discogs":
                # Discogs has release images
                release_images = []
                # Check for images in metadata
                if "images" in platform_metadata:
                    release_images = platform_metadata["images"]
                    logger.debug(f"Found images: {release_images}")
                # Check structure from DiscogsSearchPanel
                elif "artwork_url" in platform_metadata:
                    # Format a single image as would be expected
                    artwork_url = platform_metadata["artwork_url"]
                    if artwork_url:
                        release_images = [{"url": artwork_url, "width": 600, "height": 600}]
                        logger.debug(f"Created image from artwork_url: {release_images}")

                if release_images:
                    platform_images["discogs"] = release_images

            elif platform_name == "youtube":
                # YouTube has video thumbnails
                youtube_images = []
                # Look for thumbnail URLs
                if "thumbnail_url" in platform_metadata:
                    thumbnail_url = platform_metadata["thumbnail_url"]
                    if thumbnail_url:
                        # Get the highest resolution version by removing
                        # trailing resolution specifier if present
                        # YouTube thumbnails look like: https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg
                        # or https://i.ytimg.com/vi/VIDEO_ID/maxresdefault.jpg
                        youtube_images = [{"url": thumbnail_url, "width": 480, "height": 360}]
                        logger.debug(f"Found YouTube thumbnail: {youtube_images}")
                # Also check video_id and construct thumbnail URL manually
                elif "video_id" in platform_metadata:
                    video_id = platform_metadata["video_id"]
                    if video_id:
                        # Use maxresdefault.jpg for highest quality
                        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
                        youtube_images = [{"url": thumbnail_url, "width": 1280, "height": 720}]
                        logger.debug(f"Created YouTube thumbnail from video_id: {youtube_images}")

                if youtube_images:
                    platform_images["youtube"] = youtube_images

        logger.debug(f"Final platform_images: {platform_images}")
        return platform_images

    def _save_cover_image(self, track: Track, pixmap: QPixmap, metadata: dict) -> bool:
        """Save a cover image to the database.

        Args:
            track: Track to update
            pixmap: Image pixmap
            metadata: Image metadata

        Returns:
            True if the image was saved successfully, False otherwise
        """
        try:
            # Convert pixmap to bytes
            image_bytes = QByteArray()
            buffer = QBuffer(image_bytes)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "PNG")  # Save as PNG format
            buffer.close()

            # Get image dimensions
            width = pixmap.width()
            height = pixmap.height()
            size_bytes = len(image_bytes.data())

            # Create image object
            session = get_session()

            # Create new Image record
            from selecta.core.data.models.db import Image, ImageSize

            logger.info(f"Saving new cover image for track {track.id}")

            # Delete existing images for this track first to avoid conflicts
            existing_images = session.query(Image).filter(Image.track_id == track.id).all()
            for img in existing_images:
                logger.info(f"Deleting existing image: {img.id}")
                session.delete(img)

            # Commit the deletion before adding the new image
            session.commit()

            # Clear image loader cache to ensure fresh images are loaded
            if TrackDetailsPanel._db_image_loader:
                TrackDetailsPanel._db_image_loader.clear_track_image_cache(track.id)

            # Create new image
            new_image = Image(
                data=image_bytes.data(),
                mime_type="image/png",
                size=ImageSize.MEDIUM,
                width=width,
                height=height,
                file_size=size_bytes,
                track_id=track.id,
                source=metadata.get("source", "unknown"),
                source_url=metadata.get("url", ""),
            )

            # Save to database - use add() and commit() since there's no save_image method
            session.add(new_image)
            session.commit()
            image_id = new_image.id

            logger.info(f"New image saved with ID: {image_id}")

            if image_id:
                logger.info(f"Saved new cover image (id={image_id}) for track {track.id}")

                # Update track relationships if needed
                from selecta.core.data.repositories.track_repository import TrackRepository

                track_repo = TrackRepository(session)

                # Reload the track to ensure it has the new image
                track_repo.refresh_track(track.id)

                # Instead of relying on refresh, directly update the displayed image
                # This ensures the image change is immediately visible
                if TrackDetailsPanel._db_image_loader:
                    # Force reload from database
                    logger.info(f"Forcing image reload for track {track.id}")

                    # Clear any existing image from the cache
                    TrackDetailsPanel._db_image_loader.clear_track_image_cache(track.id)

                # Keep the current image displayed (it's already showing the user selection)
                # and avoid refreshing the panel which might revert to database image
                self._image_just_saved = True
                self._saved_image_track_id = track.id

                # Notify UI of update WITHOUT triggering a full refresh
                SelectionState().notify_track_updated(track.id)

                return True
            else:
                logger.error(f"Failed to save cover image for track {track.id}")
                return False

        except Exception as e:
            logger.error(f"Error saving cover image: {e}")
            return False
