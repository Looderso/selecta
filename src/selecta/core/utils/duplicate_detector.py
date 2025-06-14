"""Utilities for detecting potential duplicate tracks in the collection."""

import difflib
from typing import Any

from loguru import logger

from selecta.core.data.database import get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.type_helpers import column_to_bool, column_to_int, column_to_str


class DuplicateDetector:
    """Utility for detecting potential duplicate tracks in the collection."""

    def __init__(self):
        """Initialize the duplicate detector."""
        self.session = get_session()
        self.track_repo = TrackRepository(self.session)
        self.playlist_repo = PlaylistRepository(self.session)

    def get_collection_playlist_id(self) -> int | None:
        """Get the ID of the Collection playlist.

        Returns:
            ID of the Collection playlist or None if not found
        """
        # Check if Collection playlist exists
        playlists = self.playlist_repo.get_all()
        for playlist in playlists:
            if column_to_str(playlist.name) == "Collection" and not column_to_bool(playlist.is_folder):
                return column_to_int(playlist.id)

        return None

    def find_potential_duplicates(self, threshold: float = 0.85) -> list[dict[str, Any]]:
        """Find potential duplicate tracks in the Collection.

        Args:
            threshold: Similarity threshold for considering tracks as potential duplicates (0.0-1.0)

        Returns:
            List of potential duplicate groups with track information
        """
        # Get Collection playlist ID
        collection_id = self.get_collection_playlist_id()
        if not collection_id:
            return []

        # Get all tracks in Collection
        try:
            tracks = self.playlist_repo.get_playlist_tracks(collection_id)

            # Group potential duplicates
            potential_duplicates = []
            processed_track_ids = set()

            for i, track1 in enumerate(tracks):
                # Skip if this track is already in a duplicate group
                if track1.id in processed_track_ids:
                    continue

                duplicates = []

                for _, track2 in enumerate(tracks[i + 1 :], i + 1):
                    # Skip if this track is already in a duplicate group
                    if track2.id in processed_track_ids:
                        continue

                    # Calculate similarity based on artist and title
                    similarity = self._calculate_similarity(track1, track2)

                    # If similar, add to duplicates
                    if similarity >= threshold:
                        # Add the first track if this is the first duplicate found
                        if not duplicates:
                            duplicates.append(
                                {
                                    "id": track1.id,
                                    "title": track1.title,
                                    "artist": track1.artist,
                                    "album": track1.album or "",
                                    "duration_ms": track1.duration_ms,
                                    "platforms": self._get_track_platforms(track1),
                                    "local_path": track1.local_path or "",
                                }
                            )
                            processed_track_ids.add(track1.id)

                        # Add the duplicate track
                        duplicates.append(
                            {
                                "id": track2.id,
                                "title": track2.title,
                                "artist": track2.artist,
                                "album": track2.album or "",
                                "duration_ms": track2.duration_ms,
                                "platforms": self._get_track_platforms(track2),
                                "local_path": track2.local_path or "",
                                "similarity": similarity,
                            }
                        )
                        processed_track_ids.add(track2.id)

                # If duplicates found, add the group
                if duplicates:
                    potential_duplicates.append(duplicates)

            return potential_duplicates

        except Exception as e:
            logger.exception(f"Error finding potential duplicates: {e}")
            return []

    def _calculate_similarity(self, track1: Any, track2: Any) -> float:
        """Calculate similarity between two tracks.

        Args:
            track1: First track
            track2: Second track

        Returns:
            Similarity score (0.0-1.0)
        """
        # Compare titles
        title_similarity = difflib.SequenceMatcher(None, track1.title.lower(), track2.title.lower()).ratio()

        # Compare artists
        artist_similarity = difflib.SequenceMatcher(None, track1.artist.lower(), track2.artist.lower()).ratio()

        # Compare duration if available
        duration_similarity = 1.0
        if track1.duration_ms and track2.duration_ms:
            # If duration differs by less than 3 seconds, consider them similar
            duration_diff_seconds = abs(track1.duration_ms - track2.duration_ms) / 1000
            duration_similarity = 1.0 if duration_diff_seconds < 3 else max(0, 1.0 - duration_diff_seconds / 30)

        # Weight the factors
        weighted_similarity = (
            (title_similarity * 0.5)  # Title is very important
            + (artist_similarity * 0.4)  # Artist is important
            + (duration_similarity * 0.1)  # Duration is a secondary factor
        )

        return weighted_similarity

    def _get_track_platforms(self, track: Any) -> list[str]:
        """Get the list of platforms where the track is available.

        Args:
            track: Track to check

        Returns:
            List of platform names
        """
        platforms = []
        for platform_info in track.platform_info:
            platforms.append(platform_info.platform)

        return platforms

    def find_orphaned_tracks(self) -> list[dict[str, Any]]:
        """Find tracks in Collection that aren't in any other playlists.

        Returns:
            List of orphaned tracks with track information
        """
        # Get Collection playlist ID
        collection_id = self.get_collection_playlist_id()
        if not collection_id:
            return []

        try:
            # Get all playlists
            playlists = self.playlist_repo.get_all()

            # Get all tracks in Collection
            collection_tracks = self.playlist_repo.get_playlist_tracks(collection_id)
            collection_track_ids = {track.id for track in collection_tracks}

            # Track which tracks appear in other playlists
            tracks_in_playlists = set()

            # For each playlist except Collection
            for playlist in playlists:
                # Skip Collection and folders
                if playlist.id == collection_id or playlist.is_folder:
                    continue

                # Get tracks in this playlist
                playlist_tracks = self.playlist_repo.get_playlist_tracks(playlist.id)

                # Add to the set of tracks in playlists
                for track in playlist_tracks:
                    tracks_in_playlists.add(track.id)

            # Find orphaned tracks (in Collection but not in any other playlist)
            orphaned_track_ids = collection_track_ids - tracks_in_playlists

            # Get full track information for orphaned tracks
            orphaned_tracks = []
            for track in collection_tracks:
                if track.id in orphaned_track_ids:
                    orphaned_tracks.append(
                        {
                            "id": track.id,
                            "title": track.title,
                            "artist": track.artist,
                            "album": track.album or "",
                            "duration_ms": track.duration_ms,
                            "platforms": self._get_track_platforms(track),
                            "local_path": track.local_path or "",
                        }
                    )

            return orphaned_tracks

        except Exception as e:
            logger.exception(f"Error finding orphaned tracks: {e}")
            return []
