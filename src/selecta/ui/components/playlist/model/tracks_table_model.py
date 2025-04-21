from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from selecta.ui.components.playlist.base_items import BaseTrackItem


class TracksTableModel(QAbstractTableModel):
    """Model for displaying tracks in a table view."""

    def __init__(self, parent=None):
        """Initialize the tracks table model.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.tracks: list[BaseTrackItem] = []

        # Flag to disable display data caching
        # This is used to resolve the issue with platform icons not updating
        self.force_refresh_data = True

        # Default column configurations
        self._platform_columns = {
            # Default/Local platform columns
            "default": {
                "columns": ["Title", "Artist", "Tags", "Genre", "BPM", "Quality", "Platforms"],
                "column_keys": ["title", "artist", "tags", "genre", "bpm", "quality", "platforms"],
            },
            # Spotify platform columns
            "spotify": {
                "columns": ["Title", "Artist", "Album", "Duration", "Platforms"],
                "column_keys": ["title", "artist", "album", "duration", "platforms"],
            },
            # YouTube platform columns
            "youtube": {
                "columns": ["Title", "Channel", "Duration", "Platforms"],
                "column_keys": ["title", "artist", "duration", "platforms"],
            },
            # Discogs platform columns
            "discogs": {
                "columns": ["Title", "Artist", "Album", "Year", "Platforms"],
                "column_keys": ["title", "artist", "album", "added_at", "platforms"],
            },
            # Rekordbox platform columns
            "rekordbox": {
                "columns": ["Title", "Artist", "BPM", "Genre", "Tags", "Quality", "Platforms"],
                "column_keys": ["title", "artist", "bpm", "genre", "tags", "quality", "platforms"],
            },
        }

        # Start with default columns
        self.current_platform = "default"
        self.columns = self._platform_columns["default"]["columns"]
        self.column_keys = self._platform_columns["default"]["column_keys"]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        """Get the number of rows.

        Args:
            parent: Parent index

        Returns:
            Number of rows
        """
        return len(self.tracks)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        """Get the number of columns.

        Args:
            parent: Parent index

        Returns:
            Number of columns
        """
        return len(self.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get data for the given index and role.

        Args:
            index: Index of the item
            role: Data role

        Returns:
            Data for the index and role
        """
        if not index.isValid():
            return None

        if index.row() >= len(self.tracks) or index.row() < 0:
            return None

        track = self.tracks[index.row()]
        column_key = self.column_keys[index.column()]

        # Get display data from the track - BaseTrackItem implementation
        try:
            # Call the method to retrieve display data (this uses the cache if available)
            display_data = track.to_display_data()
        except Exception as e:
            from loguru import logger

            logger.error(f"Error getting display data for track: {e}")
            # Return empty dict if to_display_data fails
            display_data = {}

        from loguru import logger

        from selecta.core.utils.type_helpers import dict_str

        # Use display_data directly with our typed helper functions
        track_data = display_data

        if role == Qt.ItemDataRole.DisplayRole:
            # For platforms and quality columns, we'll handle this differently - we return
            # empty string here and use custom delegates for visualization
            if column_key == "platforms" or column_key == "quality":
                return ""
            return dict_str(track_data, column_key)
        elif role == Qt.ItemDataRole.UserRole:
            # Return the list of platforms for the PlatformIconDelegate
            if column_key == "platforms":
                # Get platforms directly from the BaseTrackItem
                platforms = track.platforms if hasattr(track, "platforms") else []

                # Fallback to display data if needed
                if not platforms and track_data and "platforms" in track_data:
                    platforms = track_data.get("platforms", [])

                # Only log platform data when it changes to reduce spam
                if hasattr(track, "track_id"):
                    track_id = track.track_id

                    # Use a class attribute to track platform changes
                    if not hasattr(self, "_last_platform_data"):
                        self._last_platform_data = {}

                    # Only log if platforms changed or it's been a while
                    last_data = self._last_platform_data.get(track_id, {})
                    last_platforms = last_data.get("platforms", [])
                    last_time = last_data.get("time", 0)

                    import time

                    current_time = time.time()

                    if set(platforms) != set(last_platforms) or current_time - last_time > 60:
                        # Only log when platforms actually change or once a minute
                        logger.debug(f"Returning platforms for track {track_id}: {platforms}")
                        self._last_platform_data[track_id] = {"platforms": platforms, "time": current_time}

                return platforms
            # Return the quality value for the TrackQualityDelegate
            if column_key == "quality":
                return track_data.get("quality", -1)
            # Return the raw track data for any UserRole requests
            if column_key == "title":
                return {
                    "track_id": track.track_id,
                    "album_id": track.album_id,
                    "has_image": track.has_image,
                    "db_id": track.track_id if hasattr(track, "db_id") else None,
                }
        elif role == Qt.ItemDataRole.ToolTipRole:
            if column_key == "title":
                title = dict_str(track_data, "title")
                artist = dict_str(track_data, "artist")
                return f"{title} by {artist}"
            if column_key == "platforms":
                return dict_str(track_data, "platforms_tooltip")
            if column_key == "quality":
                return dict_str(track_data, "quality_str")
            return dict_str(track_data, column_key)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get header data for the given section.

        Args:
            section: Header section
            orientation: Header orientation
            role: Data role

        Returns:
            Header data
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and section < len(self.columns)
        ):
            return self.columns[section]

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Get flags for the given index.

        Args:
            index: Index of the item

        Returns:
            Item flags
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def clear(self) -> None:
        """Clear all tracks from the model."""
        self.beginResetModel()
        self.tracks.clear()
        self.endResetModel()

    def set_tracks(self, tracks: list[BaseTrackItem]) -> None:
        """Set the tracks in the model.

        Args:
            tracks: List of track items
        """
        self.beginResetModel()
        self.tracks = tracks
        self.endResetModel()

    def get_track(self, row: int) -> BaseTrackItem | None:
        """Get the track at the given row.

        Args:
            row: Row index

        Returns:
            BaseTrackItem at the row or None if out of bounds
        """
        if 0 <= row < len(self.tracks):
            return self.tracks[row]
        return None

    def get_image_metadata(self, row: int) -> dict[str, Any]:
        """Get image metadata for the track at the given row.

        Args:
            row: Row index

        Returns:
            Dictionary with image metadata (track_id, album_id, has_image)
        """
        if 0 <= row < len(self.tracks):
            track = self.tracks[row]
            return {
                "track_id": track.track_id,
                "album_id": track.album_id,
                "has_image": track.has_image,
            }
        return {}

    def set_platform(self, platform: str) -> None:
        """Set the current platform and update the columns accordingly.

        Args:
            platform: Platform name (default, spotify, youtube, discogs, rekordbox)
        """
        if platform in self._platform_columns:
            self.beginResetModel()
            self.current_platform = platform
            self.columns = self._platform_columns[platform]["columns"]
            self.column_keys = self._platform_columns[platform]["column_keys"]
            self.endResetModel()
        else:
            # Fallback to default if platform not found
            self.beginResetModel()
            self.current_platform = "default"
            self.columns = self._platform_columns["default"]["columns"]
            self.column_keys = self._platform_columns["default"]["column_keys"]
            self.endResetModel()

    def update_track_quality(self, track_id: Any, quality: int | None = None) -> bool:
        """Update a specific track's quality rating.

        Args:
            track_id: The track ID to update
            quality: The new quality rating, or None to fetch from database

        Returns:
            True if track was found and updated, False otherwise
        """
        from loguru import logger

        # If quality is explicitly provided, we need to update it directly
        if quality is not None:
            for row, track in enumerate(self.tracks):
                if track.track_id == track_id:
                    # Update the track's quality
                    track.quality = quality

                    # Clear display cache to ensure it's regenerated with the new quality
                    track.clear_display_cache()

                    # Notify the view that this row has changed
                    first_index = self.index(row, 0)
                    last_index = self.index(row, self.columnCount() - 1)
                    self.dataChanged.emit(first_index, last_index)

                    # Also specifically update the quality cell
                    if "quality" in self.column_keys:
                        quality_col = self.column_keys.index("quality")
                        quality_index = self.index(row, quality_col)
                        self.dataChanged.emit(quality_index, quality_index)

                    logger.debug(f"Directly updated quality for track {track_id} to {quality}")
                    return True

            logger.warning(f"Track {track_id} not found for direct quality update")
            return False
        else:
            # If no quality provided, use the comprehensive update method
            # that fetches all track data from the database
            logger.debug(f"Fetching updated track data from database for track {track_id}")
            return self.update_track_from_database(track_id)

    def update_track_field(self, track_id: Any, field_name: str, value: Any) -> bool:
        """Update a specific field of a track without a full database reload.

        This method efficiently updates a single field in a track item
        and notifies the view to refresh only that specific cell.

        Args:
            track_id: The ID of the track to update
            field_name: The name of the field to update
            value: The new value for the field

        Returns:
            True if the update was successful, False otherwise
        """
        from loguru import logger

        # Find the track in our current model
        track_row = -1
        for row, track in enumerate(self.tracks):
            if hasattr(track, "track_id") and track.track_id == track_id:
                track_row = row
                break

        if track_row == -1:
            logger.warning(f"Track {track_id} not found in current view for field update")
            return False

        # Get the track from our model
        track = self.tracks[track_row]

        # Update the specified field
        if hasattr(track, field_name):
            # Log the update
            logger.debug(f"Updating track {track_id} field {field_name}: {getattr(track, field_name)} -> {value}")
            setattr(track, field_name, value)

            # Clear cached display data just for this track
            track.clear_display_cache()

            # Find which column corresponds to this field
            col_idx = -1
            if field_name in self.column_keys:
                col_idx = self.column_keys.index(field_name)

            # Notify the view that this cell has changed
            if col_idx >= 0:
                cell_index = self.index(track_row, col_idx)
                self.dataChanged.emit(cell_index, cell_index)
            else:
                # If we can't match the field to a column, update the whole row
                first_index = self.index(track_row, 0)
                last_index = self.index(track_row, self.columnCount() - 1)
                self.dataChanged.emit(first_index, last_index)

            return True
        else:
            logger.warning(f"Field {field_name} not found in track {track_id}")
            return False

    def update_track_platform_info(self, track_id: Any) -> bool:
        """Update just the platform information for a track.

        Updates platform-related fields for a track by fetching the latest data from the database.

        Args:
            track_id: The ID of the track to update

        Returns:
            True if the update was successful, False otherwise
        """
        # For simplicity and reliability, use the more comprehensive database update method
        # This avoids duplication and ensures all platform data is properly updated
        return self.update_track_from_database(track_id)

    def update_track_from_database(self, track_id: Any) -> bool:
        """Update all track information from the database.

        This comprehensive update method refreshes all track properties from the database,
        including platform links, metadata, and any other fields. It's designed to handle
        any type of track update in a consistent way.

        Args:
            track_id: The track ID to update

        Returns:
            True if track was found and updated, False otherwise
        """
        from loguru import logger

        # Find the track row in our model
        track_row = -1
        for row, track in enumerate(self.tracks):
            if hasattr(track, "track_id") and track.track_id == track_id:
                track_row = row
                break

        if track_row == -1:
            logger.warning(f"Track {track_id} not found in current view for update")
            return False

        # Get the track from our model
        track = self.tracks[track_row]

        # Fetch the track from database - this is the only database call we'll make
        from selecta.core.data.database import get_session
        from selecta.core.data.repositories.track_repository import TrackRepository

        session = get_session()
        track_repo = TrackRepository(session)
        db_track = track_repo.get_by_id(track_id)

        if not db_track:
            logger.warning(f"Track {track_id} not found in database for update")
            return False

        # --- Extract and update platform information ---
        platforms = []
        platform_info = []

        # Process platform info if available
        if hasattr(db_track, "platform_info") and db_track.platform_info:
            for info in db_track.platform_info:
                platform_name = getattr(info, "platform", None)
                if platform_name:
                    # Add to platforms list
                    platforms.append(platform_name)

                    # Convert TrackPlatformInfo to dictionary for display
                    platform_data = {
                        "platform": platform_name,
                        "platform_id": getattr(info, "platform_id", ""),
                        "uri": getattr(info, "uri", ""),
                    }

                    # Add metadata if available
                    if hasattr(info, "platform_data") and info.platform_data:
                        import json

                        try:
                            metadata = json.loads(info.platform_data)
                            platform_data.update(metadata)
                        except Exception:
                            pass

                    platform_info.append(platform_data)

        # --- Extract other track fields ---
        # This approach minimizes code duplication
        field_updates = {
            "title": getattr(db_track, "title", None),
            "artist": getattr(db_track, "artist", None),
            "album": getattr(db_track, "album", None),
            "quality": getattr(db_track, "quality", None),
            "has_image": bool(getattr(db_track, "images", [])),
        }

        # Handle BPM - preserve existing value if needed
        if hasattr(db_track, "bpm") and db_track.bpm is not None:
            field_updates["bpm"] = db_track.bpm
        elif hasattr(db_track, "attributes") and db_track.attributes:
            for attr in db_track.attributes:
                if attr.name.lower() == "bpm":
                    field_updates["bpm"] = attr.value
                    break

        # Handle genre - convert from list of genre objects to string
        if hasattr(db_track, "genres") and db_track.genres:
            genre_str = ", ".join([g.name for g in db_track.genres])
            field_updates["genre"] = genre_str
        elif hasattr(db_track, "genre") and db_track.genre:
            field_updates["genre"] = db_track.genre

        # Handle tags - convert from list of tag objects to list of strings
        if hasattr(db_track, "tags") and db_track.tags:
            field_updates["tags"] = [tag.name for tag in db_track.tags]

        # --- Apply updates to the track ---
        # Clear any display cache
        track.clear_display_cache()

        # Update platform info using the standard method
        track.set_platforms(platforms.copy() if platforms else [])

        # Update all other fields
        for field, value in field_updates.items():
            if hasattr(track, field) and value is not None:
                # Skip setting value if it's None
                current_value = getattr(track, field)
                if current_value != value:
                    setattr(track, field, value)

        # Log the update
        logger.debug(f"Updated track {track_id} from database")

        # Notify just once for the whole row
        first_index = self.index(track_row, 0)
        last_index = self.index(track_row, self.columnCount() - 1)
        self.dataChanged.emit(first_index, last_index)

        return True

    def update_track_platforms(self, track_id: Any) -> bool:
        """Update a track's platform information after linking.

        This method is a specialized version of update_track_from_database
        that focuses only on platform information.

        Args:
            track_id: The track ID to update

        Returns:
            True if track was found and updated, False otherwise
        """
        # Delegate to the more comprehensive update method
        return self.update_track_from_database(track_id)
