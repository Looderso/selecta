#!/usr/bin/env python3
"""
Test script for YouTube platform integration.
This script tests the YouTube client functionality:
1. Authentication and client creation
2. Listing playlists
3. Getting videos from a playlist
4. Creating a new playlist
5. Adding videos to a playlist
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from loguru import logger
from selecta.core.platform.youtube.client import YouTubeClient


def main():
    """Run the YouTube platform test."""
    logger.info("Starting YouTube platform test")
    
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
    
    # Get channel info
    try:
        channel_info = youtube_client.get_channel_info()
        logger.info(f"Channel Title: {channel_info.get('snippet', {}).get('title')}")
        logger.info(f"Channel ID: {channel_info.get('id')}")
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        return False
    
    # List playlists
    try:
        playlists = youtube_client.get_playlists()
        logger.info(f"Found {len(playlists)} playlists:")
        for i, playlist in enumerate(playlists[:5]):  # Show first 5 playlists
            logger.info(f"  {i+1}. {playlist.title} (ID: {playlist.id}, Videos: {playlist.video_count})")
        
        # If we have playlists, test getting videos from the first one
        if playlists:
            test_playlist = playlists[0]
            logger.info(f"Getting videos from playlist: {test_playlist.title}")
            
            videos = youtube_client.get_playlist_tracks(test_playlist.id)
            logger.info(f"Found {len(videos)} videos in playlist:")
            for i, video in enumerate(videos[:5]):  # Show first 5 videos
                logger.info(f"  {i+1}. {video.title} (ID: {video.id})")
            
            # Test creating a new playlist
            logger.info("Creating a test playlist...")
            new_playlist = youtube_client.create_playlist(
                name="Selecta Test Playlist",
                description="This is a test playlist created by Selecta",
                privacy_status="private"
            )
            logger.info(f"Created playlist: {new_playlist.title} (ID: {new_playlist.id})")
            
            # If we have videos, add the first one to the test playlist
            if videos:
                test_video = videos[0]
                logger.info(f"Adding video '{test_video.title}' to test playlist...")
                youtube_client.add_tracks_to_playlist(new_playlist.id, [test_video.id])
                logger.info("Video added successfully!")
            
            # Test search functionality
            logger.info("Testing search functionality...")
            search_results = youtube_client.search_tracks("test music", limit=3)
            logger.info(f"Found {len(search_results)} search results:")
            for i, result in enumerate(search_results):
                snippet = result.get("snippet", {})
                logger.info(f"  {i+1}. {snippet.get('title')} (ID: {result.get('id', {}).get('videoId')})")
    
    except Exception as e:
        logger.error(f"Error testing YouTube platform: {e}")
        return False
    
    logger.info("YouTube platform test completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)