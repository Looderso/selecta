"""Script to add test data to the database."""

import os
import sys
from datetime import UTC, datetime

# Add the src directory to the path to allow importing the modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from loguru import logger

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Playlist, PlaylistTrack, Track


def main():
    """Main function to add test data."""
    # Get a session
    session = get_session()

    # Check if we have any tracks
    tracks = session.query(Track).all()
    if tracks:
        logger.info(f"Found {len(tracks)} existing tracks")
    else:
        logger.info("No existing tracks, adding test tracks")

        # Add some test tracks
        test_tracks = [
            {"title": "Bohemian Rhapsody", "artist": "Queen", "duration_ms": 354000, "year": 1975},
            {
                "title": "Stairway to Heaven",
                "artist": "Led Zeppelin",
                "duration_ms": 482000,
                "year": 1971,
            },
            {
                "title": "Sweet Child O' Mine",
                "artist": "Guns N' Roses",
                "duration_ms": 356000,
                "year": 1987,
            },
            {"title": "Imagine", "artist": "John Lennon", "duration_ms": 183000, "year": 1971},
            {
                "title": "Smells Like Teen Spirit",
                "artist": "Nirvana",
                "duration_ms": 301000,
                "year": 1991,
            },
            {"title": "Hotel California", "artist": "Eagles", "duration_ms": 391000, "year": 1976},
            {"title": "Purple Haze", "artist": "Jimi Hendrix", "duration_ms": 171000, "year": 1967},
            {
                "title": "Billie Jean",
                "artist": "Michael Jackson",
                "duration_ms": 294000,
                "year": 1982,
            },
            {
                "title": "Like a Rolling Stone",
                "artist": "Bob Dylan",
                "duration_ms": 361000,
                "year": 1965,
            },
            {"title": "Respect", "artist": "Aretha Franklin", "duration_ms": 147000, "year": 1967},
        ]

        # Create and add tracks
        for track_data in test_tracks:
            track = Track(
                title=track_data["title"],
                artist=track_data["artist"],
                duration_ms=track_data["duration_ms"],
                year=track_data["year"],
                is_available_locally=False,
            )
            session.add(track)

        # Flush to get IDs
        session.flush()
        logger.info(f"Added {len(test_tracks)} test tracks")

    # Get all tracks (including newly added ones)
    all_tracks = session.query(Track).all()

    # Get all playlists
    playlists = session.query(Playlist).all()
    logger.info(f"Found {len(playlists)} playlists")

    # Add tracks to playlists
    for playlist in playlists:
        if playlist.is_folder:
            logger.info(f"Skipping folder: {playlist.name}")
            continue

        # Check if playlist already has tracks
        existing_tracks = (
            session.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist.id).count()
        )

        if existing_tracks > 0:
            logger.info(
                f"Playlist '{playlist.name}' already has {existing_tracks} tracks, skipping"
            )
            continue

        # Add random tracks to playlist
        num_tracks = min(5, len(all_tracks))  # Add up to 5 tracks per playlist
        start_idx = int(playlist.id) % len(all_tracks)  # Start at different positions for variety

        for i in range(num_tracks):
            track_idx = (start_idx + i) % len(all_tracks)
            track = all_tracks[track_idx]

            # Add track to playlist
            try:
                # Check if this track is already in this playlist to avoid duplicates
                existing = (
                    session.query(PlaylistTrack)
                    .filter(
                        PlaylistTrack.playlist_id == playlist.id, PlaylistTrack.track_id == track.id
                    )
                    .first()
                )

                if not existing:
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist.id,
                        track_id=track.id,
                        position=i,
                        added_at=datetime.now(UTC),
                    )
                    session.add(playlist_track)
                    logger.info(f"Added track '{track.title}' to playlist '{playlist.name}'")
            except Exception as e:
                logger.error(f"Error adding track {track.id} to playlist {playlist.id}: {e}")

    # Commit all changes
    session.commit()
    logger.info("All test data committed to database")

    # Verify the data
    for playlist in playlists:
        if playlist.is_folder:
            continue

        # Check PlaylistTrack records
        playlist_tracks = (
            session.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist.id).all()
        )
        track_count = len(playlist_tracks)
        logger.info(f"Playlist '{playlist.name}' has {track_count} PlaylistTrack records")

        # Print the tracks in the playlist
        if track_count > 0:
            logger.info(f"Tracks in '{playlist.name}':")
            for i, pt in enumerate(playlist_tracks):
                track = session.query(Track).filter(Track.id == pt.track_id).first()
                if track:
                    logger.info(f"  {i + 1}. {track.title} by {track.artist}")


if __name__ == "__main__":
    main()
