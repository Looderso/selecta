"""Utility for extracting metadata from audio files."""

from pathlib import Path

from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import APIC, ID3

from selecta.core.data.repositories.image_repository import ImageRepository
from selecta.core.data.repositories.track_repository import TrackRepository


class MetadataExtractor:
    """Extracts metadata from audio files."""

    def __init__(self):
        """Initialize the metadata extractor."""
        self.track_repo = TrackRepository()
        self.image_repo = ImageRepository()

    def extract_cover_from_track(self, track_id: int) -> bool:
        """Extract cover art from a track's audio file and add it to the database.

        Args:
            track_id: The track ID

        Returns:
            True if cover was extracted and added, False otherwise
        """
        try:
            # Get the track from the database
            track = self.track_repo.get_by_id(track_id)
            if not track or not track.local_path:
                logger.warning(f"Track {track_id} not found or has no local path")
                return False

            # Check if the track already has an image
            existing_image = self.image_repo.get_track_image(track_id)
            if existing_image:
                logger.debug(f"Track {track_id} already has an image, skipping")
                return False

            # Check if the file exists
            file_path = Path(track.local_path)
            if not file_path.exists():
                logger.warning(f"Audio file not found: {file_path}")
                return False

            # Extract cover art
            cover_data = self._extract_cover_from_file(file_path)
            if not cover_data:
                logger.debug(f"No cover art found in {file_path}")
                return False

            # Add the image to the database
            self.image_repo.resize_and_store_image(
                original_data=cover_data, track_id=track_id, source="audio_metadata"
            )

            logger.info(f"Successfully extracted and added cover for track {track_id}")
            return True

        except Exception as e:
            logger.exception(f"Error extracting cover for track {track_id}: {e}")
            return False

    def _extract_cover_from_file(self, file_path: Path) -> bytes:
        """Extract cover art from an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            Cover art data as bytes or None if not found
        """
        try:
            # Try with Mutagen's generic File
            audio = MutagenFile(file_path)
            if audio is None:
                return None

            # Different audio formats store artwork differently
            # MP3 (ID3)
            if hasattr(audio, "tags") and isinstance(audio.tags, ID3):
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        return tag.data

            # FLAC and others often use the 'pictures' attribute
            if hasattr(audio, "pictures"):
                for pic in audio.pictures:
                    return pic.data

            # MP4/AAC files use 'covr' atom
            if "covr" in audio:
                return audio["covr"][0]

            # Try a more general approach for other formats
            for key in audio:
                if key.startswith("APIC:") or key == "APIC" or key == "covr":
                    return audio[key][0]

            # No cover found
            return None

        except Exception as e:
            logger.exception(f"Error extracting cover from {file_path}: {e}")
            return None

    def batch_extract_covers(self, limit: int = None) -> tuple[int, int]:
        """Extract covers for all tracks without images.

        Args:
            limit: Maximum number of tracks to process (None for all)

        Returns:
            Tuple of (successful extractions, failed extractions)
        """
        # Get all tracks with local paths but no images
        tracks_with_local_paths = self.track_repo.get_all_with_local_path()

        success_count = 0
        failed_count = 0

        # Process tracks
        for i, track in enumerate(tracks_with_local_paths):
            if limit and i >= limit:
                break

            # Skip tracks that already have images
            if self.image_repo.get_track_image(track.id):
                continue

            # Extract and add cover
            if self.extract_cover_from_track(track.id):
                success_count += 1
            else:
                failed_count += 1

        return success_count, failed_count
