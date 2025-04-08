#!/usr/bin/env python3
"""
Test script for YouTube synchronization.
This script tests importing a YouTube playlist into the local database.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from loguru import logger
from selecta.core.data.database import get_session as get_db_session
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.platform.youtube.sync import import_youtube_playlist, export_playlist_to_youtube, sync_youtube_playlist


def main():
    """Run the YouTube sync test."""
    logger.info("Starting YouTube sync test")
    
    # Create YouTube client
    youtube_client = YouTubeClient()
    
    # Check if authenticated
    if not youtube_client.is_authenticated():
        logger.info("YouTube client not authenticated. Starting authentication flow...")
        success = youtube_client.authenticate()
        if not success:
            logger.error("YouTube authentication failed.")
            return False
        logger.info("YouTube authentication successful!")
    else:
        logger.info("YouTube client already authenticated.")
    
    # Get user's playlists
    playlists = youtube_client.get_playlists()
    if not playlists:
        logger.error("No YouTube playlists found.")
        return False
    
    # Display playlists
    logger.info(f"Found {len(playlists)} playlists:")
    for i, playlist in enumerate(playlists[:5]):  # Show first 5 playlists
        logger.info(f"  {i+1}. {playlist.title} (ID: {playlist.id}, Videos: {playlist.video_count})")
    
    # Ask user to select a playlist to import
    selection = input("\nEnter the number of the playlist to import (or press Enter to skip import test): ")
    if selection and selection.isdigit() and 1 <= int(selection) <= len(playlists):
        selected_playlist = playlists[int(selection) - 1]
        logger.info(f"Selected playlist: {selected_playlist.title}")
        
        # Import the playlist
        logger.info(f"Importing playlist {selected_playlist.title} to local database...")
        try:
            with get_db_session() as session:
                playlist, tracks = import_youtube_playlist(
                    youtube_client, selected_playlist.id, session
                )
                logger.info(f"Successfully imported playlist '{playlist.name}' with {len(tracks)} tracks")
                
                # Try exporting the playlist back to YouTube
                export_test = input("\nDo you want to test exporting this playlist back to YouTube? (y/n): ")
                if export_test.lower() == 'y':
                    logger.info(f"Exporting playlist '{playlist.name}' to YouTube...")
                    youtube_playlist_id = export_playlist_to_youtube(
                        youtube_client, playlist.id, session=session
                    )
                    logger.info(f"Successfully exported playlist to YouTube (ID: {youtube_playlist_id})")
                    
                    # Try syncing the playlist
                    sync_test = input("\nDo you want to test syncing this playlist? (y/n): ")
                    if sync_test.lower() == 'y':
                        logger.info(f"Syncing playlist '{playlist.name}' with YouTube...")
                        added, removed = sync_youtube_playlist(
                            youtube_client, playlist.id, session=session
                        )
                        logger.info(f"Sync complete: Added {added} tracks, removed {removed} tracks")
        
        except Exception as e:
            logger.error(f"Error during YouTube sync test: {e}")
            return False
    
    logger.info("YouTube sync test completed!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)