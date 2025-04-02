# src/selecta/core/utils/folder_scanner.py
import contextlib
from pathlib import Path
from typing import Any

from loguru import logger
from tinytag import TinyTag

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.type_helpers import column_to_bool, column_to_int, column_to_str


class LocalFolderScanner:
    """Utility for scanning and reconciling the local database folder."""

    def __init__(self, folder_path: str):
        """Initialize the folder scanner.

        Args:
            folder_path: Path to the local database folder
        """
        self.folder_path = Path(folder_path)
        self.track_repo = TrackRepository()
        self.playlist_repo = PlaylistRepository()

        # Supported audio file extensions
        self.audio_extensions = {".mp3", ".flac", ".wav", ".aac", ".m4a", ".ogg", ".aiff"}

    def scan_folder(self) -> dict[str, list[Path]]:
        """Scan the folder for audio files and categorize them.

        Returns:
            Dictionary with categorized files: {
                'in_database': [files in DB],
                'not_in_database': [files not in DB],
                'missing_from_folder': [DB entries with missing files]
            }
        """
        result = {"in_database": [], "not_in_database": [], "missing_from_folder": []}

        # Get all physical files in the folder
        try:
            physical_files = self._get_audio_files()
            physical_paths = {str(path) for path in physical_files}

            # Get all tracks from the database
            all_tracks = self.track_repo.session.query(
                self.track_repo.session.query_model.local_path
            ).all()

            # Extract paths and convert to set for faster lookups
            db_paths = {track.local_path for track in all_tracks if track.local_path}

            # Categorize files
            for file_path in physical_files:
                str_path = str(file_path)
                if str_path in db_paths:
                    result["in_database"].append(file_path)
                else:
                    result["not_in_database"].append(file_path)

            # Find missing files
            for db_path in db_paths:
                if db_path and db_path not in physical_paths:
                    result["missing_from_folder"].append(Path(db_path))

            return result

        except Exception as e:
            logger.exception(f"Error scanning folder: {e}")
            raise

    def _get_audio_files(self) -> list[Path]:
        """Get all audio files in the folder.

        Returns:
            List of audio file paths
        """
        audio_files = []

        for ext in self.audio_extensions:
            audio_files.extend(self.folder_path.glob(f"**/*{ext}"))
            audio_files.extend(self.folder_path.glob(f"**/*{ext.upper()}"))

        return audio_files

    def _extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            Dictionary of metadata or None if extraction failed
        """
        try:
            tag = TinyTag.get(file_path)

            metadata = {
                "title": tag.title or file_path.stem,
                "artist": tag.artist or "Unknown Artist",
                "album": tag.album,
                "year": tag.year,
                "duration_ms": int(tag.duration * 1000) if tag.duration else 0,
                "genre": tag.genre,
                # Some tags might have BPM stored as "bpm" or as part of the comment
                "bpm": None,
            }

            # Try to extract BPM if available
            # TinyTag doesn't directly support BPM, but it could be in custom tags
            if hasattr(tag, "get") and callable(tag.get):
                bpm = tag.get("bpm")
                if bpm:
                    with contextlib.suppress(ValueError, TypeError):
                        metadata["bpm"] = float(bpm)

            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return None

    def import_untracked_files(self, collection_playlist_id: int = None) -> tuple[int, list[str]]:
        """Import untracked files found in the folder to the database.

        Args:
            collection_playlist_id: Optional ID of collection playlist to add tracks to

        Returns:
            Tuple of (number of imported files, list of errors)
        """
        errors = []
        imported_count = 0

        # Get untracked files
        scan_result = self.scan_folder()
        untracked_files = scan_result["not_in_database"]

        # Create collection playlist if needed
        if collection_playlist_id is None:
            collection_playlist_id = self._ensure_collection_playlist()

        # Process each file
        for file_path in untracked_files:
            try:
                # Extract metadata
                metadata = self._extract_metadata(file_path)

                if not metadata:
                    errors.append(f"Could not extract metadata from {file_path}")
                    continue

                # Create track in database
                track_data = {
                    "title": metadata.get("title", file_path.stem),
                    "artist": metadata.get("artist", "Unknown Artist"),
                    "duration_ms": metadata.get("duration_ms", 0),
                    "local_path": str(file_path),
                }

                # Add album if available
                if metadata.get("album"):
                    # This is simplified - in a full implementation you'd create
                    # or look up the album in a proper album table
                    track_data["album_id"] = None

                # Create track
                new_track = self.track_repo.create(track_data)

                # Add BPM if available
                if metadata.get("bpm") is not None:
                    self.track_repo.add_attribute(
                        new_track.id, "bpm", float(metadata["bpm"]), "file_metadata"
                    )

                # Add genre if available
                if metadata.get("genre"):
                    # Add genre to genres table
                    from selecta.core.data.models.db import Genre

                    genre_obj = (
                        self.track_repo.session.query(Genre)
                        .filter(Genre.name == metadata["genre"])
                        .first()
                    )
                    if not genre_obj:
                        genre_obj = Genre(name=metadata["genre"], source="file_metadata")
                        self.track_repo.session.add(genre_obj)
                        self.track_repo.session.commit()

                    # Associate track with genre
                    new_track.genres.append(genre_obj)
                    self.track_repo.session.commit()

                # Add to collection playlist
                if collection_playlist_id:
                    self.playlist_repo.add_track(collection_playlist_id, new_track.id)

                imported_count += 1

            except Exception as e:
                error_msg = f"Error importing {file_path}: {str(e)}"
                logger.exception(error_msg)
                errors.append(error_msg)

        return imported_count, errors

    def _ensure_collection_playlist(self) -> int:
        """Ensure the Collection playlist exists.

        Returns:
            ID of the collection playlist
        """
        # Check if collection playlist already exists
        playlists = self.playlist_repo.get_all()
        for playlist in playlists:
            if column_to_str(playlist.name) == "Collection" and not column_to_bool(
                playlist.is_folder
            ):
                return column_to_int(playlist.id)

        # Create the collection playlist
        playlist_data = {
            "name": "Collection",
            "description": "Local music collection",
            "is_local": True,
            "source_platform": None,  # This is our own playlist
        }

        new_playlist = self.playlist_repo.create(playlist_data)
        return column_to_int(new_playlist.id)
