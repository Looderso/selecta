from typing import Any

from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.database import get_session
from selecta.core.data.models.db import ImageSize
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.ui.components.image_loader import DatabaseImageLoader
from selecta.ui.components.playlist.track_item import TrackItem


class PlatformInfoCard(QFrame):
    """Card displaying platform-specific information."""

    def __init__(self, platform: str, info: dict, parent=None):
        """Initialize the platform info card.

        Args:
            platform: Platform name
            info: Platform-specific information
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        
        # Log what platform data we're getting
        logger.info(f"Creating platform card for {platform} with data: {info}")

        # Set background color based on platform
        self.setStyleSheet(self._get_platform_style(platform))

        layout = QVBoxLayout(self)

        # Platform header
        header_layout = QHBoxLayout()
        
        # Create and set platform icon
        platform_icon = QLabel()
        
        # Define emoji icons for fallbacks 
        platform_emojis = {
            "spotify": "🎵",
            "youtube": "▶️",
            "discogs": "💿",
            "rekordbox": "🎧",
            "wantlist": "🛒",
            "collection": "📚"
        }
        
        # Load platform icon from resources
        try:
            from selecta.core.utils.path_helper import get_resource_path, get_resources_path
            import os
            
            # Get the resources path
            resources_dir = get_resources_path()
            logger.info(f"Resources directory: {resources_dir}")
            
            # Absolute paths for more reliable loading
            absolute_paths = [
                # Absolute paths 
                f"/Users/lorenzhausler/Documents/repos/selecta/resources/icons/1x/{platform}.png",
                f"/Users/lorenzhausler/Documents/repos/selecta/resources/icons/0.5x/{platform}@0.5x.png",
            ]
            
            # Try different icon paths with fallbacks
            icon_paths = [
                *absolute_paths,
                # Try direct path from resources 1x first
                resources_dir / "icons" / "1x" / f"{platform}.png",
                # Use resource path helper as backup
                get_resource_path(f"icons/1x/{platform}.png"),
                # Try other sizes if needed
                resources_dir / "icons" / "0.5x" / f"{platform}@0.5x.png",
                resources_dir / "icons" / "0.25x" / f"{platform}@0.25x.png",
            ]
            
            icon_loaded = False
            for icon_path in icon_paths:
                # Convert to string for QPixmap and exists check
                icon_path_str = str(icon_path)
                if os.path.exists(icon_path_str):
                    pixmap = QPixmap(icon_path_str)
                    if not pixmap.isNull():
                        # Scale to appropriate size for the card
                        platform_icon.setPixmap(pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        icon_loaded = True
                        logger.info(f"✅ Loaded platform icon from {icon_path_str}")
                        break
            
            if not icon_loaded:
                # Use appropriate emoji for platform
                emoji = platform_emojis.get(platform, "🔍")
                logger.warning(f"No icon found for platform {platform}, using emoji: {emoji}")
                platform_icon.setText(emoji)
        except Exception as e:
            # Use appropriate emoji for platform
            emoji = platform_emojis.get(platform, "🔍")
            logger.error(f"Error loading platform icon: {e}")
            platform_icon.setText(emoji)
        
        platform_name = QLabel(platform.capitalize())
        platform_name.setStyleSheet("font-weight: bold; font-size: 14px;")

        header_layout.addWidget(platform_icon)
        header_layout.addWidget(platform_name, 1)  # 1 = stretch factor
        layout.addLayout(header_layout)

        # Platform-specific info
        for key, value in info.items():
            if key == "platform":
                continue  # Skip the platform key itself

            # Skip internal keys that start with _
            if key.startswith("_"):
                continue
                
            # Format the key for display
            display_key = key.replace('_', ' ').capitalize()
            
            # Create layout for this info pair
            info_layout = QHBoxLayout()
            key_label = QLabel(f"{display_key}:")
            key_label.setStyleSheet("font-weight: bold;")
            
            # Format the value as a string with special handling
            if isinstance(value, bool):
                value_str = "Yes" if value else "No"
            elif value is None:
                value_str = "N/A"
            else:
                value_str = str(value)
                
            value_label = QLabel(value_str)
            value_label.setWordWrap(True)

            info_layout.addWidget(key_label)
            info_layout.addWidget(value_label, 1)  # 1 = stretch factor
            layout.addLayout(info_layout)

    def _get_platform_style(self, platform: str) -> str:
        """Get the style for a platform.

        Args:
            platform: Platform name

        Returns:
            CSS style string
        """
        match platform:
            case "spotify":
                return "background-color: #1DB954; color: white; border-radius: 5px;"
            case "rekordbox":
                return "background-color: #0082CD; color: white; border-radius: 5px;"
            case "discogs":
                return "background-color: #333333; color: white; border-radius: 5px;"
            case _:
                return "background-color: #888888; color: white; border-radius: 5px;"


class TrackDetailsPanel(QWidget):
    """Panel displaying detailed information about a track."""

    # Shared image loader
    _db_image_loader = None

    # Signal emitted when track quality is changed
    quality_changed = pyqtSignal(int, int)  # track_id, new_quality
    
    # Signal emitted when panel is refreshed
    panel_refreshed = pyqtSignal(int)  # track_id

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
        self.image_layout = QHBoxLayout(self.image_container)
        self.image_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Set placeholder
        placeholder = QPixmap(200, 200)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.image_label.setPixmap(placeholder)

        self.image_layout.addWidget(self.image_label)
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

        # Create scroll area for platform cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for cards
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)  # Push cards to the top

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)  # 1 = stretch factor
        
        # Connect to the global selection state
        from selecta.ui.components.selection_state import SelectionState
        self.selection_state = SelectionState()
        self.selection_state.track_updated.connect(self._on_track_updated)

    def set_track(self, track: TrackItem | None, platform_info: dict[str, Any] | None = None):
        """Set the track to display.

        Args:
            track: Track item to display details for, or None to clear
            platform_info: Optional dictionary of platform info objects keyed by platform name
        """
        # First check if this is an update to the current track
        is_same_track = track and self._current_track_id == track.track_id
        
        # Log track change or update for debugging - use higher log level to see what's happening
        if track:
            if is_same_track:
                logger.info(f"REFRESH: Updating existing track display for track_id={track.track_id}")
            else:
                logger.info(f"NEW: Setting track display for track_id={track.track_id}")
                
            # Log platform info if provided
            if platform_info:
                logger.info(f"Platform info provided: {list(platform_info.keys())}")
            else:
                logger.info(f"No platform info provided")
        
        # CRITICAL FIX: Before doing anything, record the current track ID so we can force refresh
        current_track_id = None
        if track:
            current_track_id = track.track_id
        
        # Clear existing cards - completely empty cards to start fresh
        self._clear_cards()

        # Reset image to placeholder before processing
        self._reset_image_to_placeholder()

        if not track:
            self.header_label.setText("No Track Selected")
            self._current_track_id = None
            self._current_album_id = None

            # Reset quality dropdown
            self.quality_combo.setCurrentIndex(0)  # Not rated
            self.quality_combo.setEnabled(False)
            self._current_quality = -1
            return

        # Update header with track info
        self.header_label.setText(f"{track.artist} - {track.title}")

        # ALWAYS FETCH PLATFORM INFO FROM DATABASE - this is a critical fix
        # This ensures we always get the latest platform info, even when it's also passed in
        from selecta.core.data.database import get_session
        from selecta.core.data.repositories.track_repository import TrackRepository
        
        try:
            # Create fresh session
            session = get_session()
            track_repo = TrackRepository(session)
            
            # Get ALL platform info directly from DB
            db_platform_info = {}
            
            # Log which track we're looking for
            logger.info(f"DIRECT DB FETCH: Getting platform info for track_id={track.track_id}")
            
            for platform in ["spotify", "discogs", "youtube", "rekordbox"]:
                info = track_repo.get_platform_info(track.track_id, platform)
                if info:
                    db_platform_info[platform] = info
                    logger.info(f"FOUND in DB: Platform info for {platform}: platform_id={info.platform_id}, has_uri={hasattr(info, 'uri')}")
            
            # Use database platform info if available, otherwise fall back to what was passed in
            if db_platform_info:
                logger.info(f"USING fresh DB platform info: {list(db_platform_info.keys())}")
                # Override the passed-in platform_info with what we got from DB
                platform_info = db_platform_info
            elif platform_info:
                # Use what was passed in if nothing in DB
                logger.info(f"Using PASSED-IN platform info: {list(platform_info.keys())}")
            else:
                logger.warning(f"⚠️ NO platform info found in DB for track {track.track_id}")
        except Exception as e:
            logger.error(f"Error fetching fresh platform info: {e}")

        # Get platform info from track or use provided platform_info
        if platform_info:
            # Process platform info from database
            for platform_name, info in platform_info.items():
                if info:
                    logger.info(f"Processing platform info for {platform_name}")
                    
                    # Create card for each platform
                    platform_data = {
                        "platform": platform_name,
                    }

                    # If platform_data is a JSON string, parse it
                    if hasattr(info, "platform_data") and info.platform_data:
                        import json

                        try:
                            platform_metadata = json.loads(info.platform_data)
                            # Add all metadata to platform_data dictionary
                            for key, value in platform_metadata.items():
                                platform_data[key] = value
                            logger.info(f"Added metadata for {platform_name}: {list(platform_metadata.keys())}")
                        except json.JSONDecodeError:
                            logger.warning(f"JSON decode error for {platform_name} platform_data")
                    else:
                        logger.warning(f"No platform_data attribute or it's empty for {platform_name}")

                    # Add platform ID - always required
                    if hasattr(info, "platform_id"):
                        platform_data["id"] = info.platform_id
                        logger.info(f"Added platform_id to {platform_name}: {info.platform_id}")
                    else:
                        logger.warning(f"No platform_id attribute for {platform_name}")
                    
                    # Add URI - attribute is named 'uri' in the TrackPlatformInfo model
                    if hasattr(info, "uri") and info.uri is not None:
                        platform_data["uri"] = info.uri
                        logger.info(f"Added URI to {platform_name}: {info.uri}")
                    else:
                        logger.info(f"No uri attribute or it's None for {platform_name}")

                    # Create and add the card - log all data going to the card for debugging
                    logger.info(f"Creating card for platform {platform_name} with data: {platform_data}")
                    card = PlatformInfoCard(platform_name, platform_data)
                    
                    # Force card to the top of the list
                    self.scroll_layout.insertWidget(0, card)
                    logger.info(f"✅ Added platform card for {platform_name}")
                else:
                    logger.warning(f"Platform info for {platform_name} is None")
        else:
            # Get platform info from track's display data - fallback mechanism
            display_data = track.to_display_data()
            track_platform_info = display_data.get("platform_info", [])
            
            logger.info(f"Fallback: Using display data platform info: {len(track_platform_info)} items")

            # Create cards for each platform
            for info in track_platform_info:
                # Handle both dict and TrackPlatformInfo objects
                if hasattr(info, "platform"):
                    # It's a TrackPlatformInfo object
                    platform_name = info.platform
                    logger.info(f"Processing platform info object for {platform_name}")

                    # Create platform data dict from TrackPlatformInfo object
                    platform_data = {
                        "platform": platform_name,
                        "id": info.platform_id,
                    }

                    # If the object has URI, add it
                    if hasattr(info, "uri") and info.uri:
                        platform_data["uri"] = info.uri
                        logger.info(f"Added URI from object: {info.uri}")

                    # If platform_data is available and is a JSON string, parse it
                    if hasattr(info, "platform_data") and info.platform_data:
                        import json

                        try:
                            platform_metadata = json.loads(info.platform_data)
                            # Add all metadata to platform_data dictionary
                            for key, value in platform_metadata.items():
                                platform_data[key] = value
                            logger.info(f"Added metadata from object: {list(platform_metadata.keys())}")
                        except json.JSONDecodeError:
                            logger.warning(f"JSON decode error for platform_data from object")

                    # Create and add the card with platform name and constructed data
                    logger.info(f"Creating card from object for {platform_name} with data: {platform_data}")
                    card = PlatformInfoCard(platform_name, platform_data)
                    logger.info(f"Added platform card for {platform_name} (object)")

                elif isinstance(info, dict) and "platform" in info:
                    # It's a dictionary
                    platform_name = info.get("platform", "unknown")
                    logger.info(f"Processing platform info dict for {platform_name}")
                    
                    # Use the dictionary directly
                    logger.info(f"Creating card from dict for {platform_name} with data: {info}")
                    card = PlatformInfoCard(platform_name, info)
                    logger.info(f"Added platform card for {platform_name} (dict)")

                else:
                    # Unknown format - skip
                    logger.warning(f"Unknown platform info format: {type(info)}")
                    continue

                # Insert the card at the top
                self.scroll_layout.insertWidget(0, card)

        # Try to load the track image
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

        # Check if this track actually has an image before trying to load it
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

        # Load track image from database if available
        if has_track_image and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_track_image(track.track_id, ImageSize.MEDIUM)

        # Also try to load the album image as a fallback
        if has_album_id and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_album_image(track.album_id, ImageSize.MEDIUM)

    def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap):
        """Handle loaded image from database for a track.

        Args:
            track_id: The track ID
            pixmap: The loaded image pixmap
        """
        # Check if this image belongs to the current track
        if track_id == self._current_track_id:
            self.image_label.setPixmap(pixmap)
            self.image_container.setVisible(True)
            # Reduce log spam
            # logger.debug(f"Displayed track image for track {track_id}")

    def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap):
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
                # Reduce log spam
                # logger.debug(f"Displayed album image for album {album_id}")

    @pyqtSlot(int)
    def _on_quality_changed(self, index: int):
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
            logger.info(
                f"Updating quality in database:"
                f" track_id={self._current_track_id}, quality={quality}"
            )

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
                from selecta.ui.components.selection_state import SelectionState

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

    def _clear_cards(self):
        """Clear all platform cards."""
        # Remove all widgets except the stretch at the end
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if widget:
                    widget.setParent(None)  # Detach from parent before deletion
                    widget.deleteLater()
        
        # Force layout update
        self.scroll_content.update()
        self.scroll_area.update()

    def _reset_image_to_placeholder(self):
        """Reset the image display to a placeholder."""
        # Create a gray placeholder
        placeholder = QPixmap(200, 200)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.image_label.setPixmap(placeholder)

        # Hide the image container by default
        # It will be shown only if a valid image is loaded
        self.image_container.setVisible(False)
        
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
            # Get the track from selection state
            selected_track = self.selection_state.get_selected_track()
            
            if not selected_track:
                logger.warning(f"Track {track_id} was updated but not found in selection state")
                return
                
            # Force fresh database query for platform info
            from selecta.core.data.database import get_session
            from selecta.core.data.repositories.track_repository import TrackRepository
            
            session = get_session()
            track_repo = TrackRepository(session)
            
            # Get platform info for all platforms
            platform_info = {}
            for platform_name in ["spotify", "rekordbox", "discogs", "youtube"]:
                info = track_repo.get_platform_info(track_id, platform_name)
                if info:
                    platform_info[platform_name] = info
                    
            # If we have platform info, refresh the panel
            if platform_info:
                logger.debug(f"Refreshing track details panel with fresh platform info: {list(platform_info.keys())}")
                self.set_track(selected_track, platform_info)
            else:
                # Just refresh with the track
                logger.debug("No platform info found, refreshing track details panel with just the track")
                self.set_track(selected_track)
                
            # Emit signal to notify that panel was refreshed
            self.panel_refreshed.emit(track_id)
                
        except Exception as e:
            logger.error(f"Error refreshing track details panel after track update: {e}")
        finally:
            self._refreshing = False
