"""Script to add tracks to playlists for testing."""

import os
import sys

# Add the src directory to the path to allow importing the modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from loguru import logger

from selecta.core.data.database import get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository


def main():
    """Main function to add tracks to playlists."""
    # Get a session
    session = get_session()

    # Create repositories
    playlist_repo = PlaylistRepository(session)
    track_repo = TrackRepository(session)

    # Get all tracks
    tracks = track_repo.get_all()
    logger.info(f"Found {len(tracks)} tracks")

    if not tracks:
        logger.error("No tracks found in the database. Cannot add to playlists.")
        return

    # Get some playlists
    playlists = playlist_repo.get_all()
    logger.info(f"Found {len(playlists)} playlists")

    if not playlists:
        logger.error("No playlists found in the database.")
        return

    # Distribute tracks to playlists
    for i, playlist in enumerate(playlists):
        if playlist.is_folder:
            logger.info(f"Skipping folder: {playlist.name}")
            continue

        # Add some tracks to this playlist
        start_idx = i * 10
        end_idx = min(start_idx + 10, len(tracks))

        if start_idx >= len(tracks):
            start_idx = 0
            end_idx = min(10, len(tracks))

        playlist_tracks = tracks[start_idx:end_idx]

        logger.info(f"Adding {len(playlist_tracks)} tracks to playlist: {playlist.name}")

        # Add each track to the playlist
        for j, track in enumerate(playlist_tracks):
            try:
                playlist_repo.add_track(playlist.id, track.id, position=j)
                logger.info(f"  - Added track: {track.title} by {track.artist}")
            except Exception as e:
                logger.error(f"Error adding track {track.id} to playlist {playlist.id}: {e}")

    # Commit the transaction
    session.commit()
    logger.info("All tracks added to playlists and committed to database")

    # Verify the tracks were added
    for playlist in playlists:
        if playlist.is_folder:
            continue

        tracks = playlist_repo.get_playlist_tracks(playlist.id)
        logger.info(f"Playlist {playlist.name} now has {len(tracks)} tracks")


if __name__ == "__main__":
    main()
