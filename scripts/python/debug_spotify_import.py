#!/usr/bin/env python
"""Debug script for testing Spotify track imports.

This script attempts to import a track from Spotify and logs detailed information about
the process to help diagnose import issues.
"""

import json
import sys
import traceback
from datetime import datetime

from loguru import logger

# Configure detailed logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="TRACE", format="<level>{level}</level> {message}")
logger.add("spotify_import_debug.log", level="TRACE", rotation="10 MB")

# Import required modules
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.link_manager import PlatformLinkManager
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.auth import SpotifyAuthManager


def debug_spotify_import(track_id=None):
    """Debug the Spotify track import process.

    Args:
        track_id: Optional Spotify track ID to import, if None, will use a test track
    """
    # Use a default track ID if none provided (Daft Punk - Get Lucky)
    if not track_id:
        track_id = "2Foc5Q5nqNiosCNqttzHof"

    logger.info(f"Starting debug for Spotify track import with ID: {track_id}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Create a settings repository
        settings_repo = SettingsRepository()
        logger.info("Created settings repository")

        # Check Spotify auth token status
        auth_manager = SpotifyAuthManager(settings_repo=settings_repo)
        token_info = auth_manager.get_token_info()

        if token_info:
            masked_token = {k: "***" if k in ("access_token", "refresh_token") else v for k, v in token_info.items()}
            logger.info(f"Found Spotify token info: {json.dumps(masked_token)}")

            # Check token expiration
            if "expires_at" in token_info:
                expiry_time = datetime.fromtimestamp(token_info["expires_at"])
                now = datetime.now()
                if expiry_time < now:
                    logger.warning(f"Spotify token is EXPIRED (expired at {expiry_time}, current time: {now})")
                else:
                    logger.info(f"Spotify token is valid until {expiry_time}")
        else:
            logger.warning("No Spotify token info found!")

        # Create the Spotify client
        spotify_client = PlatformFactory.create("spotify", settings_repo)
        if not spotify_client:
            logger.error("Failed to create Spotify client")
            return
        logger.info("Created Spotify client")

        # Check authentication
        logger.info("Testing Spotify authentication...")
        is_auth = spotify_client.is_authenticated()
        logger.info(f"is_authenticated() returned: {is_auth}")

        if not is_auth:
            logger.warning("Spotify client is not authenticated, attempting authentication...")
            auth_result = spotify_client.authenticate()
            logger.info(f"Authentication attempt result: {auth_result}")

            if not auth_result:
                logger.error("Failed to authenticate with Spotify")
                return
            logger.info("Successfully authenticated with Spotify")
        else:
            logger.info("Spotify client is already authenticated")

        # Check that the underlying spotipy client is initialized correctly
        if hasattr(spotify_client, "_spotify") and spotify_client._spotify:
            logger.info("Spotipy client is initialized")
        else:
            logger.error("Spotipy client is NOT initialized!")

        # Create a link manager for track import
        link_manager = PlatformLinkManager(spotify_client)
        logger.info("Created link manager")

        # Fetch the track from Spotify
        logger.info(f"Fetching track {track_id} from Spotify...")
        try:
            track = spotify_client.get_track(track_id)
            if not track:
                logger.error(f"Failed to fetch track {track_id} from Spotify (returned None)")
                return

            # Log the track data
            logger.info("Successfully fetched track from Spotify")

            # Log track type
            logger.info(f"Track type: {type(track).__name__}")

            # Get all attributes and values
            if hasattr(track, "__dict__"):
                logger.info(f"Track data: {track.__dict__}")

            # Extract and log key track attributes
            key_attrs = [
                "id",
                "name",
                "artist_names",
                "album_name",
                "duration_ms",
                "popularity",
                "explicit",
                "preview_url",
                "uri",
                "album_release_date",
            ]

            attr_values = {}
            for attr in key_attrs:
                if hasattr(track, attr):
                    attr_values[attr] = getattr(track, attr)

            logger.info(f"Track key attributes: {json.dumps(attr_values, default=str)}")

            # Check for key attributes required by link_manager.import_track
            missing_attrs = []
            critical_attrs = ["name", "artist_names"]
            for attr in critical_attrs:
                if not hasattr(track, attr) or not getattr(track, attr):
                    missing_attrs.append(attr)

            if missing_attrs:
                logger.warning(f"Track is missing critical attributes: {missing_attrs}")

            # Try to import the track
            logger.info("Attempting to import track...")
            try:
                # First, test the track data extraction logic ourselves
                logger.info("Testing track data extraction manually first...")

                # Title extraction
                if hasattr(track, "name"):
                    title = track.name
                    logger.info(f"Extracted title: {title}")
                else:
                    logger.error("Failed to extract title - 'name' attribute missing")

                # Artist extraction
                if hasattr(track, "artist_names"):
                    artist_names = track.artist_names
                    artist_str = ", ".join(artist_names) if artist_names else "Unknown Artist"
                    logger.info(f"Extracted artist: {artist_str}")
                else:
                    logger.error("Failed to extract artist - 'artist_names' attribute missing")

                # Now try the actual import
                local_track = link_manager.import_track(track)
                logger.info(
                    f"Successfully imported track: {local_track.id} - {local_track.title} by {local_track.artist}"
                )

                # Check platform info
                platform_info = getattr(local_track, "platform_info", [])
                logger.info(f"Track has {len(platform_info)} platform info entries")

                for info in platform_info:
                    logger.info(f"Platform info: {info.platform} - {info.platform_id}")
                    if hasattr(info, "metadata") and info.metadata:
                        try:
                            metadata = json.loads(info.metadata)
                            logger.info(f"Metadata: {json.dumps(metadata)}")
                        except:
                            logger.info(f"Raw metadata: {info.metadata}")

            except ValueError as e:
                logger.error(f"Validation error during import: {str(e)}")
                logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Unexpected error during import: {str(e)}")
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(f"Error fetching track {track_id} from Spotify: {str(e)}")
            logger.error(traceback.format_exc())

            # Try to get some basic information
            try:
                logger.info("Attempting to get current user profile as API test...")
                user = spotify_client._spotify.current_user()
                logger.info(f"Successfully fetched user profile: {user.get('display_name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to get user profile: {str(e)}")
                logger.error(traceback.format_exc())

    except Exception as e:
        logger.error(f"Error in debug_spotify_import: {str(e)}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Use command-line argument as track ID if provided
    track_id = sys.argv[1] if len(sys.argv) > 1 else None
    debug_spotify_import(track_id)

    logger.info("Debug script completed")
