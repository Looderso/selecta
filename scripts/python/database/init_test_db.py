#!/usr/bin/env python3
"""Initialize and populate a test database."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger

from selecta.data.database import get_engine, get_session, init_database
from selecta.data.repositories.playlist_repository import PlaylistRepository
from selecta.data.repositories.settings_repository import SettingsRepository
from selecta.data.repositories.tag_repository import TagRepository
from selecta.data.repositories.track_repository import TrackRepository
from selecta.data.repositories.vinyl_repository import VinylRepository
from selecta.utils.type_helpers import column_to_int


def create_test_data(db_path: Path) -> None:
    """Create test data in the database.

    Args:
        db_path: Path to the database file
    """
    # Create engine and session with the specific database path
    engine = get_engine(db_path)
    session = get_session(engine)

    # Initialize repositories
    track_repo = TrackRepository(session)
    playlist_repo = PlaylistRepository(session)
    vinyl_repo = VinylRepository(session)
    tag_repo = TagRepository(session)
    settings_repo = SettingsRepository(session)

    # Create tags
    logger.info("Creating tags...")
    sunset_tag = tag_repo.create_tag("sunset", "Tracks for sunset sessions", "#FF9900")
    club_tag = tag_repo.create_tag("club", "Tracks for club sets", "#990099")
    afternoon_tag = tag_repo.create_tag("afternoon", "Tracks for afternoon sessions", "#66CC99")

    # Keep track of IDs as Python integers
    sunset_tag_id = column_to_int(sunset_tag.id)
    club_tag_id = column_to_int(club_tag.id)
    afternoon_tag_id = column_to_int(afternoon_tag.id)

    # Create tracks
    logger.info("Creating tracks...")
    track1 = track_repo.create(
        {
            "title": "Magic Hour",
            "artist": "DJ Horizon",
            "duration_ms": 360000,  # 6 minutes
        }
    )

    track2 = track_repo.create(
        {
            "title": "Midnight Groove",
            "artist": "Deep Collective",
            "duration_ms": 420000,  # 7 minutes
        }
    )

    track3 = track_repo.create(
        {
            "title": "Solar Energy",
            "artist": "Sunshine Project",
            "duration_ms": 300000,  # 5 minutes
        }
    )

    # Store track IDs as Python integers
    track1_id = column_to_int(track1.id)
    track2_id = column_to_int(track2.id)
    track3_id = column_to_int(track3.id)

    # Add platform information to tracks
    track_repo.add_platform_info(
        track1_id,
        "spotify",
        "spotify123",
        "spotify:track:123",
        '{"bpm": 125, "key": "Gm"}',
    )

    track_repo.add_platform_info(track2_id, "rekordbox", "rb456", None, '{"bpm": 128, "key": "Am"}')

    # Add track attributes
    track_repo.add_attribute(track1_id, "energy", 0.85, "spotify")
    track_repo.add_attribute(track1_id, "danceability", 0.92, "spotify")
    track_repo.add_attribute(track2_id, "energy", 0.75, "spotify")
    track_repo.add_attribute(track3_id, "danceability", 0.68, "user")

    # Add tags to tracks
    tag_repo.add_tag_to_track(track1_id, sunset_tag_id)
    tag_repo.add_tag_to_track(track1_id, club_tag_id)
    tag_repo.add_tag_to_track(track2_id, club_tag_id)
    tag_repo.add_tag_to_track(track3_id, afternoon_tag_id)
    tag_repo.add_tag_to_track(track3_id, sunset_tag_id)

    # Create playlists
    logger.info("Creating playlists...")
    sunset_playlist = playlist_repo.create(
        {
            "name": "Sunset Vibes",
            "description": "Perfect tracks for sunset DJ sets",
            "is_local": True,
        }
    )

    club_playlist = playlist_repo.create(
        {
            "name": "Club Bangers",
            "description": "High energy tracks for peak time",
            "is_local": False,
            "source_platform": "spotify",
            "platform_id": "spotify_playlist_789",
        }
    )

    # Store playlist IDs as Python integers
    sunset_playlist_id = column_to_int(sunset_playlist.id)
    club_playlist_id = column_to_int(club_playlist.id)

    # Add tracks to playlists
    playlist_repo.add_track(sunset_playlist_id, track1_id, 0)
    playlist_repo.add_track(sunset_playlist_id, track3_id, 1)
    playlist_repo.add_track(club_playlist_id, track2_id, 0)
    playlist_repo.add_track(club_playlist_id, track1_id, 1)

    # Add tags to playlists
    tag_repo.add_tag_to_playlist(sunset_playlist_id, sunset_tag_id)
    tag_repo.add_tag_to_playlist(club_playlist_id, club_tag_id)

    # Create vinyl records
    logger.info("Creating vinyl records...")
    _ = vinyl_repo.create(
        {
            "discogs_id": 12345,
            "discogs_release_id": 67890,
            "is_owned": True,
            "media_condition": "Very Good Plus (VG+)",
            "sleeve_condition": "Very Good (VG)",
        },
        {
            "title": "Magic Hour EP",
            "artist": "DJ Horizon",
            "release_year": 2022,
            "label": "Sunset Records",
            "catalog_number": "SUN-123",
        },
    )

    # Store platform credentials
    logger.info("Storing credentials...")
    settings_repo.set_credentials(
        "spotify",
        {
            "client_id": "dummy_spotify_client_id",
            "client_secret": "dummy_spotify_client_secret",
            "access_token": "dummy_access_token",
            "refresh_token": "dummy_refresh_token",
            "token_expiry": datetime.utcnow() + timedelta(hours=1),
        },
    )

    settings_repo.set_credentials(
        "discogs",
        {
            "client_id": "dummy_discogs_consumer_key",
            "client_secret": "dummy_discogs_consumer_secret",
            "access_token": "dummy_discogs_access_token",
        },
    )

    # Store user settings
    logger.info("Storing settings...")
    settings_repo.set_setting("dark_mode", True)
    settings_repo.set_setting("sync_interval_minutes", 60)
    settings_repo.set_setting("default_playlist_view", "list")

    logger.success("Test data created successfully!")


def main() -> None:
    """Initialize the database and create test data."""
    # Define a test database path in the current directory
    db_path = Path("./test_selecta.db")

    logger.info(f"Initializing test database at {db_path.absolute()}")

    # Remove existing database if it exists
    if db_path.exists():
        logger.warning(f"Removing existing database at {db_path}")
        db_path.unlink()

    # Initialize the database with the specific path
    init_database(db_path)

    # Create test data with the same path
    create_test_data(db_path)

    logger.success(f"Database initialized and populated at {db_path.absolute()}")


if __name__ == "__main__":
    main()
