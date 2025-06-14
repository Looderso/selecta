#!/usr/bin/env python
"""Debug script for testing YouTube playlist loading.

This script attempts to fetch playlists and their tracks from YouTube and logs detailed
information to help diagnose issues with playlist loading.
"""

import json
import sys
import traceback
from datetime import datetime

from loguru import logger

# Configure detailed logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="TRACE", format="<level>{level}</level> {message}")
logger.add("youtube_playlists_debug.log", level="TRACE", rotation="10 MB")

# Import required modules
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.youtube.auth import YouTubeAuthManager
from selecta.ui.components.playlist.interfaces import PlatformCapability
from selecta.ui.components.playlist.platform.youtube.youtube_data_provider import YouTubeDataProvider


def debug_youtube_playlists(playlist_id=None):
    """Debug the YouTube playlist loading process.

    Args:
        playlist_id: Optional YouTube playlist ID to test, if None, will fetch all playlists
    """
    logger.info(f"Starting debug for YouTube playlists (playlist_id={playlist_id})")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Create a settings repository
        settings_repo = SettingsRepository()
        logger.info("Created settings repository")

        # Check YouTube auth token status
        auth_manager = YouTubeAuthManager(settings_repo=settings_repo)
        token_info = auth_manager.get_token_info()

        if token_info:
            masked_token = {k: "***" if k in ("access_token", "refresh_token") else v for k, v in token_info.items()}
            logger.info(f"Found YouTube token info: {json.dumps(masked_token)}")

            # Check token expiration
            if "expires_at" in token_info:
                expiry_time = datetime.fromtimestamp(token_info["expires_at"])
                now = datetime.now()
                if expiry_time < now:
                    logger.warning(f"YouTube token is EXPIRED (expired at {expiry_time}, current time: {now})")
                else:
                    logger.info(f"YouTube token is valid until {expiry_time}")
        else:
            logger.warning("No YouTube token info found!")

        # Create the YouTube client
        youtube_client = PlatformFactory.create("youtube", settings_repo)
        if not youtube_client:
            logger.error("Failed to create YouTube client")
            return
        logger.info("Created YouTube client")

        # Check authentication
        logger.info("Testing YouTube authentication...")
        is_auth = youtube_client.is_authenticated()
        logger.info(f"is_authenticated() returned: {is_auth}")

        if not is_auth:
            logger.warning("YouTube client is not authenticated, attempting authentication...")
            auth_result = youtube_client.authenticate()
            logger.info(f"Authentication attempt result: {auth_result}")

            if not auth_result:
                logger.error("Failed to authenticate with YouTube")
                return
            logger.info("Successfully authenticated with YouTube")
        else:
            logger.info("YouTube client is already authenticated")

        # Try to get channel info as a basic API test
        try:
            logger.info("Fetching YouTube channel info to test API access...")
            channel_info = youtube_client.get_channel_info()
            channel_name = channel_info.get("snippet", {}).get("title", "Unknown")
            channel_id = channel_info.get("id", "Unknown")
            logger.info(f"Successfully fetched channel info: {channel_name} (ID: {channel_id})")
        except Exception as e:
            logger.error(f"Failed to fetch channel info: {str(e)}")
            logger.error(traceback.format_exc())

        # Create a data provider
        youtube_provider = YouTubeDataProvider(youtube_client)
        logger.info("Created YouTube data provider")

        # Check provider capabilities
        capabilities = youtube_provider.get_capabilities()
        logger.info(f"Provider capabilities: {[c.name for c in capabilities]}")

        # Check if import capability is present
        has_import = PlatformCapability.IMPORT_PLAYLISTS in capabilities
        logger.info(f"Provider has IMPORT_PLAYLISTS capability: {has_import}")

        # Try direct client first, to isolate UI-related issues
        logger.info("Trying direct client access first...")
        try:
            client_playlists = youtube_client.get_all_playlists()
            logger.info(f"Direct client returned {len(client_playlists)} playlists")

            if client_playlists:
                # Log first 5 playlists from client
                for i, pl in enumerate(client_playlists[:5]):
                    logger.info(f"Client Playlist {i+1}: {pl.title} (ID: {pl.id})")

                    # Try to fetch tracks for this playlist directly
                    if i == 0 and not playlist_id:  # Test first playlist if no specific ID provided
                        try:
                            logger.info(f"Fetching tracks directly for playlist '{pl.title}' (ID: {pl.id})...")
                            direct_tracks = youtube_client.get_playlist_tracks(pl.id)
                            logger.info(f"Direct client found {len(direct_tracks)} tracks in playlist")

                            # Log first few tracks
                            for j, track in enumerate(direct_tracks[:3]):
                                logger.info(f"Direct Track {j+1}: {track.title} by {track.channel_title}")
                        except Exception as e:
                            logger.error(f"Error fetching tracks directly: {str(e)}")
                            logger.error(traceback.format_exc())
            else:
                logger.warning("Direct client returned no playlists!")
        except Exception as e:
            logger.error(f"Error getting playlists directly from client: {str(e)}")
            logger.error(traceback.format_exc())

        # Now test through provider (UI layer)
        logger.info("Now testing through provider (UI layer)...")

        # Test if we can get playlists through provider
        logger.info("Fetching YouTube playlists through provider...")
        playlists = youtube_provider.get_all_playlists()

        if not playlists:
            logger.error("Provider returned no YouTube playlists!")
            return

        logger.info(f"Provider found {len(playlists)} YouTube playlists")

        # Log details of the first few playlists
        for i, playlist in enumerate(playlists[:5]):
            logger.info(f"Provider Playlist {i+1}: {playlist.name} (ID: {playlist.item_id})")

            # Check if is_imported flag is set correctly
            if hasattr(playlist, "is_imported"):
                logger.info(f"Playlist is_imported flag: {playlist.is_imported}")
            else:
                logger.warning("Playlist does not have is_imported attribute!")

            # Log playlist attributes
            if hasattr(playlist, "__dict__"):
                logger.info(f"Playlist data: {playlist.__dict__}")

            # Try to fetch content for this playlist through provider
            if i == 0 and not playlist_id:  # Test first playlist if no specific ID provided
                provider_playlist_id = playlist.item_id
                logger.info(f"Testing provider with first playlist: {playlist.name} (ID: {provider_playlist_id})")

                try:
                    tracks = youtube_provider.get_playlist_tracks(provider_playlist_id)
                    logger.info(f"Provider found {len(tracks)} tracks in first playlist")

                    if tracks:
                        # Log details of the first few tracks
                        for j, track in enumerate(tracks[:3]):
                            logger.info(f"Provider Track {j+1}: {track.title} by {track.artist}")
                    else:
                        logger.warning("Provider returned empty track list for playlist!")
                except Exception as e:
                    logger.error(f"Error fetching tracks through provider: {str(e)}")
                    logger.error(traceback.format_exc())

        # If a specific playlist ID was provided, test fetching its tracks
        if playlist_id:
            logger.info(f"Fetching tracks for specific playlist {playlist_id}...")
            try:
                # Try direct client first
                logger.info("Fetching tracks directly from client...")
                direct_tracks = youtube_client.get_playlist_tracks(playlist_id)
                logger.info(f"Direct client found {len(direct_tracks)} tracks in playlist {playlist_id}")

                # Now try through provider
                logger.info("Fetching tracks through provider...")
                provider_tracks = youtube_provider.get_playlist_tracks(playlist_id)
                logger.info(f"Provider found {len(provider_tracks)} tracks in playlist {playlist_id}")

                # Log details of tracks and compare
                for i in range(min(5, len(direct_tracks))):
                    logger.info(f"Direct Track {i+1}: {direct_tracks[i].title} by {direct_tracks[i].channel_title}")

                for i in range(min(5, len(provider_tracks))):
                    logger.info(f"Provider Track {i+1}: {provider_tracks[i].title} by {provider_tracks[i].artist}")
            except Exception as e:
                logger.error(f"Error fetching tracks for playlist {playlist_id}: {str(e)}")
                logger.error(traceback.format_exc())

    except Exception as e:
        logger.error(f"Error in debug_youtube_playlists: {str(e)}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Use command-line argument as playlist ID if provided
    playlist_id = sys.argv[1] if len(sys.argv) > 1 else None
    debug_youtube_playlists(playlist_id)

    logger.info("Debug script completed")
