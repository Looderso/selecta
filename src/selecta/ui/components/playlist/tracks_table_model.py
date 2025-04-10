from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from selecta.ui.components.playlist.track_item import TrackItem


class TracksTableModel(QAbstractTableModel):
    """Model for displaying tracks in a table view."""

    def __init__(self, parent=None):
        """Initialize the tracks table model.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.tracks: list[TrackItem] = []

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
        display_data = track.to_display_data()

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
                # The default empty list makes sure we always return a list
                return track_data.get("platforms", [])
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

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
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

    def set_tracks(self, tracks: list[TrackItem]) -> None:
        """Set the tracks in the model.

        Args:
            tracks: List of track items
        """
        self.beginResetModel()
        self.tracks = tracks
        self.endResetModel()

    def get_track(self, row: int) -> TrackItem | None:
        """Get the track at the given row.

        Args:
            row: Row index

        Returns:
            TrackItem at the row or None if out of bounds
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
        for row, track in enumerate(self.tracks):
            if track.track_id == track_id:
                # If quality is None, fetch from database
                if quality is None:
                    from selecta.core.data.database import get_session
                    from selecta.core.data.repositories.track_repository import TrackRepository

                    session = get_session()
                    track_repo = TrackRepository(session)

                    # Get the track from the database
                    db_track = track_repo.get_by_id(track_id)
                    if db_track:
                        quality = db_track.quality
                    else:
                        # If track not found in DB, don't update
                        return False

                # Update the track's quality
                track.quality = quality

                # Notify the view that this row has changed
                # Create indexes for all cells in the row
                first_index = self.index(row, 0)
                last_index = self.index(row, self.columnCount() - 1)

                # Emit the dataChanged signal to update the view
                self.dataChanged.emit(first_index, last_index)

                # Also specifically update the quality cell
                if "quality" in self.column_keys:
                    quality_col = self.column_keys.index("quality")
                    quality_index = self.index(row, quality_col)
                    self.dataChanged.emit(quality_index, quality_index)

                return True

        return False
