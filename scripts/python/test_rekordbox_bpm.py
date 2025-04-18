#!/usr/bin/env python
"""Test script to check BPM values from Rekordbox tracks."""

import sys
from pathlib import Path

from loguru import logger

# Add the project root to sys.path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from selecta.core.data.database import get_session
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.rekordbox.client import RekordboxClient


def main():
    """Retrieve and display BPM values from Rekordbox tracks."""
    logger.info("Initializing Rekordbox client...")

    # Initialize the database session
    db_session = get_session()

    # Create a settings repository
    settings_repo = SettingsRepository(db_session)

    try:
        # Create the Rekordbox client
        client = RekordboxClient(settings_repo=settings_repo)

        # Check authentication
        if not client.is_authenticated():
            logger.error("Failed to authenticate with Rekordbox")
            return

        logger.info("Successfully authenticated with Rekordbox")

        # Get all tracks
        logger.info("Retrieving tracks...")
        tracks = client.get_all_tracks()

        # Display BPM values for up to 10 tracks
        logger.info(f"Found {len(tracks)} tracks in total")
        logger.info("Displaying BPM values for up to 10 tracks:")

        for i, track in enumerate(tracks[:10]):
            logger.info(f"Track {i+1}: {track.title} by {track.artist_name}")
            logger.info(f"  - BPM: {track.bpm} (Python type: {type(track.bpm).__name__})")

            # Get raw BPM value directly from Rekordbox object if possible
            try:
                raw_tracks = client.db.get_content(ID=track.id)
                if raw_tracks:
                    raw_bpm = getattr(raw_tracks, "BPM", None)
                    type_name = type(raw_bpm).__name__
                    logger.info(f"  - Raw BPM from Rekordbox: {raw_bpm} (Python type: {type_name})")
                    if raw_bpm is not None:
                        logger.info(f"  - Corrected BPM: {raw_bpm/100.0}")
            except Exception as e:
                logger.error(f"Error retrieving raw BPM: {e}")

    except Exception as e:
        logger.exception(f"Error in Rekordbox BPM test: {e}")
    finally:
        # Clean up resources
        if "client" in locals():
            client.close()
        if "db_session" in locals():
            db_session.close()


if __name__ == "__main__":
    main()
