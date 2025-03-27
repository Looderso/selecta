#!/usr/bin/env python3
"""Query the test database to verify data."""

import sys
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger

from selecta.core.data.database import get_engine, get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.tag_repository import TagRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.data.repositories.vinyl_repository import VinylRepository


def query_database():
    """Query and display data from the database."""
    # Specify the test database path
    db_path = Path("./test_selecta.db")
    if not db_path.exists():
        logger.error(f"Database not found at {db_path.absolute()}")
        return

    # Create engine and session specifically for the test database
    engine = get_engine(db_path)
    session = get_session(engine)

    # Initialize repositories
    track_repo = TrackRepository(session)
    playlist_repo = PlaylistRepository(session)
    vinyl_repo = VinylRepository(session)
    tag_repo = TagRepository(session)
    settings_repo = SettingsRepository(session)

    # Query and display tracks
    logger.info("=== TRACKS ===")
    tracks, count = track_repo.search("", limit=100)
    logger.info(f"Found {count} tracks")

    for track in tracks:
        logger.info(f"Track: {track.artist} - {track.title}")
        track_id = int(track.id)

        # Display platform info
        platform_infos = track_repo.get_all_platform_info(track_id)
        for platform_info in platform_infos:
            logger.info(f"  Platform: {platform_info.platform}, ID: {platform_info.platform_id}")

        # Display attributes
        attributes = track_repo.get_all_attributes(track_id)
        for attr in attributes:
            logger.info(f"  Attribute: {attr.name} = {attr.value} ({attr.source})")

        # Display tags
        tags = tag_repo.get_track_tags(track_id)
        for tag in tags:
            logger.info(f"  Tag: {tag.name} ({tag.color})")

    # Query and display playlists
    logger.info("\n=== PLAYLISTS ===")
    playlists = playlist_repo.get_all(include_tracks=True)

    for playlist in playlists:
        logger.info(f"Playlist: {playlist.name} - {playlist.description}")
        playlist_id = int(playlist.id)

        if not playlist.is_local:
            logger.info(f"  Source: {playlist.source_platform}, ID: {playlist.platform_id}")

        # Display tracks in playlist
        track_list = playlist_repo.get_playlist_tracks(playlist_id)
        logger.info(f"  Tracks ({len(track_list)}):")
        for i, track in enumerate(track_list):
            logger.info(f"    {i + 1}. {track.artist} - {track.title}")

        # Display tags
        tags = tag_repo.get_playlist_tags(playlist_id)
        logger.info(f"  Tags ({len(tags)}):")
        for tag in tags:
            logger.info(f"    - {tag.name}")

    # Query and display vinyl records
    logger.info("\n=== VINYL RECORDS ===")
    vinyl_records = vinyl_repo.get_all()

    for vinyl in vinyl_records:
        if vinyl.album:
            logger.info(
                f"Vinyl: {vinyl.album.artist} - {vinyl.album.title} ({vinyl.album.release_year})"
            )
            logger.info(f"  Label: {vinyl.album.label}, Cat#: {vinyl.album.catalog_number}")
        else:
            logger.info(f"Vinyl: ID={vinyl.id} (No album info)")

        logger.info(f"  Discogs ID: {vinyl.discogs_id}")
        logger.info(f"  Condition: Media={vinyl.media_condition}, Sleeve={vinyl.sleeve_condition}")
        logger.info(
            f"  Status: Owned={vinyl.is_owned}, Wanted={vinyl.is_wanted}, For Sale={vinyl.for_sale}"
        )

    # Query and display settings
    logger.info("\n=== SETTINGS ===")
    settings = settings_repo.get_settings_dict()
    for key, value in settings.items():
        logger.info(f"Setting: {key} = {value}")

    # Query and display platform credentials
    logger.info("\n=== PLATFORM CREDENTIALS ===")
    credentials = settings_repo.get_all_credentials()
    for cred in credentials:
        logger.info(f"Platform: {cred.platform}")
        logger.info(f"  Client ID: {cred.client_id}")
        logger.info(
            f"  Access Token: {cred.access_token[:10]}..."
            if cred.access_token
            else "  Access Token: None"
        )
        logger.info(f"  Token Expiry: {cred.token_expiry}")


if __name__ == "__main__":
    query_database()
