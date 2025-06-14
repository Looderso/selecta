#!/usr/bin/env python
"""Debug script for testing Rekordbox track imports.

This script attempts to import a track from Rekordbox and logs detailed information about
the process to help diagnose import issues.
"""

import json
import os
import sys
import traceback
from datetime import datetime

from loguru import logger

# Configure detailed logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="TRACE", format="<level>{level}</level> {message}")
logger.add("rekordbox_import_debug.log", level="TRACE", rotation="10 MB")

# Import required modules
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.link_manager import PlatformLinkManager
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.ui.components.playlist.interfaces import PlatformCapability
from selecta.ui.components.playlist.platform.rekordbox.rekordbox_data_provider import RekordboxDataProvider


def debug_rekordbox_import(playlist_id=None, track_index=0):
    """Debug the Rekordbox track import process.

    Args:
        playlist_id: Optional Rekordbox playlist ID to use, if None, will use the first playlist
        track_index: Index of the track in the playlist to import (default: 0, the first track)
    """
    logger.info(f"Starting debug for Rekordbox track import (playlist_id={playlist_id}, track_index={track_index})")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Create a settings repository
        settings_repo = SettingsRepository()
        logger.info("Created settings repository")

        # Check Rekordbox database path setting
        db_path_key = "rekordbox_database_path"
        rb_db_path = settings_repo.get_setting(db_path_key, "")

        if rb_db_path:
            logger.info(f"Rekordbox database path: {rb_db_path}")

            # Check if file exists
            if os.path.exists(rb_db_path):
                logger.info("Rekordbox database file exists")

                # Check file size
                file_size = os.path.getsize(rb_db_path) / (1024 * 1024)  # Size in MB
                logger.info(f"Database file size: {file_size:.2f} MB")
            else:
                logger.error(f"Rekordbox database file does NOT exist at path: {rb_db_path}")
        else:
            logger.warning("Rekordbox database path not set in settings")

        # Create the Rekordbox client
        rekordbox_client = PlatformFactory.create("rekordbox", settings_repo)
        if not rekordbox_client:
            logger.error("Failed to create Rekordbox client")
            return
        logger.info("Created Rekordbox client")

        # Check authentication
        logger.info("Testing Rekordbox authentication...")
        is_auth = rekordbox_client.is_authenticated()
        logger.info(f"is_authenticated() returned: {is_auth}")

        if not is_auth:
            logger.warning("Rekordbox client is not authenticated, attempting authentication...")
            auth_result = rekordbox_client.authenticate()
            logger.info(f"Authentication attempt result: {auth_result}")

            if not auth_result:
                logger.error("Failed to authenticate with Rekordbox")
                return
            logger.info("Successfully authenticated with Rekordbox")
        else:
            logger.info("Rekordbox client is already authenticated")

        # Check database connection
        if hasattr(rekordbox_client, "db") and rekordbox_client.db:
            logger.info("Rekordbox database connection is established")

            # Check if we can execute a simple query
            try:
                query = "SELECT COUNT(*) FROM djmdTrack"
                result = rekordbox_client.db.execute(query).fetchone()
                track_count = result[0] if result else 0
                logger.info(f"Found {track_count} tracks in Rekordbox database")
            except Exception as e:
                logger.error(f"Failed to execute query on Rekordbox database: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            logger.error("Rekordbox database connection is NOT established!")

        # Create a data provider
        rekordbox_provider = RekordboxDataProvider(rekordbox_client)
        logger.info("Created Rekordbox data provider")

        # Check provider capabilities
        capabilities = rekordbox_provider.get_capabilities()
        logger.info(f"Provider capabilities: {[c.name for c in capabilities]}")

        # Check if import capability is present
        has_import = PlatformCapability.IMPORT_PLAYLISTS in capabilities
        logger.info(f"Provider has IMPORT_PLAYLISTS capability: {has_import}")

        # Create a link manager for track import
        link_manager = PlatformLinkManager(rekordbox_client)
        logger.info("Created link manager")

        # Get playlists via direct client access first
        try:
            logger.info("Trying direct client access for playlists...")
            client_playlists = rekordbox_client.get_all_playlists()
            logger.info(f"Direct client returned {len(client_playlists)} playlists")

            if client_playlists:
                # Log first 5 playlists from client
                for i, pl in enumerate(client_playlists[:5]):
                    logger.info(f"Client Playlist {i+1}: {pl.name} (ID: {pl.id})")
        except Exception as e:
            logger.error(f"Error getting playlists directly from client: {str(e)}")
            logger.error(traceback.format_exc())

        # Get playlists via provider
        logger.info("Fetching Rekordbox playlists via provider...")
        playlists = rekordbox_provider.get_all_playlists()

        if not playlists:
            logger.error("No Rekordbox playlists found via provider")
            return

        logger.info(f"Found {len(playlists)} Rekordbox playlists via provider")

        # Log the first few playlists
        for i, playlist in enumerate(playlists[:5]):
            logger.info(f"Provider Playlist {i+1}: {playlist.name} (ID: {playlist.item_id})")

            # Check if is_imported flag is set correctly
            if hasattr(playlist, "is_imported"):
                logger.info(f"Playlist is_imported flag: {playlist.is_imported}")
            else:
                logger.warning("Playlist does not have is_imported attribute!")

        # Select a playlist to use
        if playlist_id:
            target_playlist = None
            for playlist in playlists:
                if str(playlist.item_id) == str(playlist_id):
                    target_playlist = playlist
                    break

            if not target_playlist:
                logger.error(f"Playlist with ID {playlist_id} not found")
                return
        else:
            # Use the first non-folder playlist
            target_playlist = None
            for playlist in playlists:
                if not playlist.is_folder():
                    target_playlist = playlist
                    break

            if not target_playlist:
                logger.error("No regular playlists found (all are folders)")
                return

        logger.info(f"Using playlist: {target_playlist.name} (ID: {target_playlist.item_id})")

        # Get tracks from the playlist - first try direct client
        try:
            logger.info(f"Fetching tracks directly for playlist ID {target_playlist.item_id}...")
            direct_tracks = rekordbox_client.get_playlist_tracks(str(target_playlist.item_id))
            logger.info(f"Direct client found {len(direct_tracks)} tracks in playlist")

            # Log first few tracks from direct client
            for i, track in enumerate(direct_tracks[:3]):
                logger.info(f"Direct Track {i+1}: {track.title} by {track.artist_name}")

                # Check for required attributes
                missing_attrs = []
                for attr in ["title", "artist_name"]:
                    if not hasattr(track, attr) or not getattr(track, attr):
                        missing_attrs.append(attr)

                if missing_attrs:
                    logger.warning(f"Track is missing critical attributes: {missing_attrs}")
        except Exception as e:
            logger.error(f"Error fetching tracks directly: {str(e)}")
            logger.error(traceback.format_exc())

        # Now get tracks via provider
        logger.info(f"Fetching tracks via provider for playlist {target_playlist.name}...")
        playlist_tracks = rekordbox_provider.get_playlist_tracks(target_playlist.item_id)

        if not playlist_tracks:
            logger.error(f"No tracks found in playlist {target_playlist.name}")
            return

        logger.info(f"Provider found {len(playlist_tracks)} tracks in playlist {target_playlist.name}")

        # Select a track to import
        if track_index >= len(playlist_tracks):
            logger.error(f"Track index {track_index} out of range (playlist has {len(playlist_tracks)} tracks)")
            track_index = 0

        track_to_import = playlist_tracks[track_index]
        logger.info(f"Selected track to import: {track_to_import.title} by {track_to_import.artist}")

        # Log detailed track information
        if hasattr(track_to_import, "__dict__"):
            logger.info(f"Track data: {track_to_import.__dict__}")

        # Extract key attributes
        key_attrs = ["track_id", "title", "artist", "album", "duration_ms", "location"]
        attr_values = {}
        for attr in key_attrs:
            if hasattr(track_to_import, attr):
                attr_values[attr] = getattr(track_to_import, attr)

        logger.info(f"Track key attributes: {json.dumps(attr_values, default=str)}")

        # Check for actual file
        location = getattr(track_to_import, "location", None)
        if location:
            if os.path.exists(location):
                logger.info(f"Audio file exists at location: {location}")
                file_size = os.path.getsize(location) / (1024 * 1024)  # Size in MB
                logger.info(f"Audio file size: {file_size:.2f} MB")
            else:
                logger.warning(f"Audio file does NOT exist at location: {location}")

        # Try to import the track
        logger.info("Attempting to import track...")
        try:
            # First, test the track data extraction logic ourselves
            logger.info("Testing track data extraction manually first...")

            # Title extraction
            if hasattr(track_to_import, "title"):
                title = track_to_import.title
                logger.info(f"Extracted title: {title}")
            else:
                logger.error("Failed to extract title - 'title' attribute missing")

            # Artist extraction
            if hasattr(track_to_import, "artist"):
                artist = track_to_import.artist
                logger.info(f"Extracted artist: {artist}")
            else:
                logger.error("Failed to extract artist - 'artist' attribute missing")

            # Now try the actual import
            local_track = link_manager.import_track(track_to_import)
            logger.info(f"Successfully imported track: {local_track.id} - {local_track.title} by {local_track.artist}")

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
        logger.error(f"Error in debug_rekordbox_import: {str(e)}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Parse command-line arguments if provided
    playlist_id = None
    track_index = 0

    if len(sys.argv) > 1:
        playlist_id = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            track_index = int(sys.argv[2])
        except ValueError:
            logger.error(f"Invalid track index: {sys.argv[2]}, using 0")

    debug_rekordbox_import(playlist_id, track_index)

    logger.info("Debug script completed")
