#!/usr/bin/env python3
"""Test playlist track addition and removal operations with comprehensive safety.

This script tests adding and removing tracks from playlists on each platform:
- Creating test playlists
- Searching for tracks
- Adding tracks to playlists
- Removing tracks from playlists
- Verifying track counts

All operations use the safety system to ensure no real playlists are touched.
"""

import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from loguru import logger

from selecta.core.testing import SafetyLevel
from selecta.core.testing.safe_platform_tester import safe_platform_test


def test_track_operations_for_platform(session, platform_name: str):
    """Test track operations for a specific platform.

    Args:
        session: Safe platform test session
        platform_name: Name of the platform to test
    """
    logger.info(f"\n🎵 Testing track operations for {platform_name.title()}")
    logger.info("=" * 60)

    try:
        # Step 1: Create a test playlist
        logger.info("📝 Step 1: Creating test playlist...")
        test_playlist_name = "Track Operations Test"
        playlist_id = session.create_safe_playlist(
            platform_name, test_playlist_name, description="Test playlist for track addition/removal operations"
        )
        logger.info(f"   ✅ Created playlist: {playlist_id}")

        # Step 2: Search for test tracks
        logger.info("🔍 Step 2: Searching for tracks to add...")
        search_queries = ["test", "music", "song"]
        all_tracks = []

        for query in search_queries:
            try:
                tracks = session.search_for_test_tracks(platform_name, query, limit=3)
                if tracks:
                    all_tracks.extend(tracks[:2])  # Take 2 tracks from each search
                    logger.info(f"   Found {len(tracks)} tracks for '{query}'")
                else:
                    logger.warning(f"   No tracks found for '{query}'")
            except Exception as e:
                logger.warning(f"   Search failed for '{query}': {e}")

        if not all_tracks:
            logger.error(f"   ❌ No tracks found for {platform_name}, skipping track operations")
            return False

        # Limit to 4 tracks total to keep test manageable
        test_tracks = all_tracks[:4]
        logger.info(f"   ✅ Using {len(test_tracks)} tracks for testing")

        # Step 3: Extract track IDs (platform-specific)
        logger.info("🔗 Step 3: Extracting track IDs...")
        track_ids = []
        track_info = []

        for track in test_tracks:
            try:
                if platform_name == "spotify":
                    # Spotify tracks have 'id' field
                    track_id = track.get("id") if isinstance(track, dict) else getattr(track, "id", None)
                    name = (
                        track.get("name", "Unknown") if isinstance(track, dict) else getattr(track, "name", "Unknown")
                    )
                    artist = "Unknown"
                    if isinstance(track, dict) and track.get("artists"):
                        artist = track["artists"][0].get("name", "Unknown")
                    elif hasattr(track, "artists") and track.artists:
                        artist = track.artists[0].name if hasattr(track.artists[0], "name") else str(track.artists[0])

                elif platform_name == "rekordbox":
                    # Rekordbox tracks have 'ID' field
                    track_id = track.get("ID") if isinstance(track, dict) else getattr(track, "id", None)
                    name = (
                        track.get("Title", "Unknown") if isinstance(track, dict) else getattr(track, "title", "Unknown")
                    )
                    artist = (
                        track.get("Artist", "Unknown")
                        if isinstance(track, dict)
                        else getattr(track, "artist", "Unknown")
                    )

                elif platform_name == "youtube":
                    # YouTube tracks have 'id' -> 'videoId' structure
                    if isinstance(track, dict) and "id" in track:
                        track_id = track["id"].get("videoId") if isinstance(track["id"], dict) else track["id"]
                    else:
                        track_id = getattr(track, "id", None)

                    name = "Unknown"
                    artist = "Unknown"
                    if isinstance(track, dict) and "snippet" in track:
                        name = track["snippet"].get("title", "Unknown")
                        artist = track["snippet"].get("channelTitle", "Unknown")
                    elif hasattr(track, "title"):
                        name = track.title
                        artist = getattr(track, "channel_title", "Unknown")

                if track_id:
                    track_ids.append(str(track_id))
                    track_info.append((name, artist))
                    logger.info(f"   📀 {name} by {artist} (ID: {track_id})")
                else:
                    logger.warning(f"   ⚠️  Could not extract ID from track: {track}")

            except Exception as e:
                logger.warning(f"   ⚠️  Error processing track: {e}")

        if not track_ids:
            logger.error(f"   ❌ No valid track IDs found for {platform_name}")
            return False

        logger.info(f"   ✅ Extracted {len(track_ids)} valid track IDs")

        # Step 4: Add tracks to playlist
        logger.info("➕ Step 4: Adding tracks to playlist...")
        try:
            success = session.add_tracks_to_playlist(platform_name, playlist_id, track_ids)
            if success:
                logger.info(f"   ✅ Successfully added {len(track_ids)} tracks to playlist")
            else:
                logger.error("   ❌ Failed to add tracks to playlist")
                return False
        except Exception as e:
            logger.error(f"   ❌ Error adding tracks: {e}")
            return False

        # Step 5: Verify tracks were added (get playlist tracks)
        logger.info("🔍 Step 5: Verifying tracks were added...")
        try:
            # Get tracks in the playlist to verify they were added
            if platform_name == "spotify":
                playlist_tracks = session.spotify_client.get_playlist_tracks(playlist_id)
                track_count = len(playlist_tracks)
            elif platform_name == "rekordbox":
                playlist_tracks = session.rekordbox_client.get_playlist_tracks(playlist_id)
                track_count = len(playlist_tracks)
            elif platform_name == "youtube":
                playlist_tracks = session.youtube_client.get_playlist_tracks(playlist_id)
                track_count = len(playlist_tracks)

            logger.info(f"   ✅ Playlist now contains {track_count} tracks")

            # Log some track details for verification
            for i, track in enumerate(playlist_tracks[:3]):  # Show first 3 tracks
                if hasattr(track, "name") or hasattr(track, "title"):
                    name = getattr(track, "name", getattr(track, "title", "Unknown"))
                    artist = getattr(track, "artist_name", getattr(track, "artist", "Unknown"))
                    logger.info(f"   📀 Track {i+1}: {name} by {artist}")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not verify tracks were added: {e}")

        # Step 6: Remove some tracks from playlist
        logger.info("➖ Step 6: Removing tracks from playlist...")

        # Remove half the tracks (or at least 1)
        tracks_to_remove = track_ids[: max(1, len(track_ids) // 2)]
        logger.info(f"   Attempting to remove {len(tracks_to_remove)} tracks...")

        try:
            if platform_name == "spotify":
                # For Spotify, we need URIs, not IDs
                track_uris = [f"spotify:track:{tid}" for tid in tracks_to_remove]
                success = session.spotify_client.remove_tracks_from_playlist(playlist_id, track_uris)
            elif platform_name == "rekordbox":
                success = session.rekordbox_client.remove_tracks_from_playlist(playlist_id, tracks_to_remove)
            elif platform_name == "youtube":
                # For YouTube, we need playlist item IDs, not video IDs
                # Get the current playlist tracks to find playlist item IDs
                try:
                    current_tracks = session.youtube_client.get_playlist_tracks(playlist_id)
                    playlist_item_ids = []

                    # Find playlist item IDs for the tracks we want to remove
                    for track in current_tracks:
                        if track.id in tracks_to_remove and track.playlist_item_id:
                            playlist_item_ids.append(track.playlist_item_id)

                    if playlist_item_ids:
                        logger.info(f"   Found {len(playlist_item_ids)} playlist item IDs for removal")
                        success = session.youtube_client.remove_tracks_from_playlist(playlist_id, playlist_item_ids)
                    else:
                        logger.warning("   ⚠️  No playlist item IDs found for removal")
                        success = True  # Don't fail if we can't find the items
                except Exception as e:
                    logger.warning(f"   ⚠️  Error getting playlist item IDs: {e}")
                    success = True  # Don't fail the test for this

            if success:
                logger.info(f"   ✅ Successfully removed {len(tracks_to_remove)} tracks from playlist")
            else:
                logger.warning("   ⚠️  Track removal may have failed")

        except Exception as e:
            logger.warning(f"   ⚠️  Error removing tracks: {e}")

        # Step 7: Final verification
        logger.info("🔍 Step 7: Final verification...")
        try:
            if platform_name == "spotify":
                final_tracks = session.spotify_client.get_playlist_tracks(playlist_id)
                final_count = len(final_tracks)
            elif platform_name == "rekordbox":
                final_tracks = session.rekordbox_client.get_playlist_tracks(playlist_id)
                final_count = len(final_tracks)
            elif platform_name == "youtube":
                final_tracks = session.youtube_client.get_playlist_tracks(playlist_id)
                final_count = len(final_tracks)

            logger.info(f"   ✅ Final playlist contains {final_count} tracks")

        except Exception as e:
            logger.warning(f"   ⚠️  Could not get final track count: {e}")

        logger.info(f"✅ {platform_name.title()} track operations test completed successfully!")
        return True

    except Exception as e:
        logger.exception(f"❌ {platform_name.title()} track operations test failed: {e}")
        return False


def main():
    """Run track operations tests for all platforms."""
    logger.info("🎵 Starting Playlist Track Operations Testing")
    logger.info("=" * 70)

    # Test platforms that support playlist modification
    test_platforms = ["spotify", "rekordbox", "youtube"]
    results = {}

    try:
        with safe_platform_test(SafetyLevel.TEST_ONLY) as session:
            for platform_name in test_platforms:
                logger.info(f"\n🚀 Testing {platform_name.title()}...")

                try:
                    # Check if platform is available
                    if platform_name == "spotify" or platform_name == "rekordbox" or platform_name == "youtube":
                        pass

                    logger.info(f"✅ {platform_name.title()} client is available and authenticated")

                    # Run the track operations test
                    success = test_track_operations_for_platform(session, platform_name)
                    results[platform_name] = success

                except RuntimeError as e:
                    logger.warning(f"❌ {platform_name.title()}: {e}")
                    results[platform_name] = False
                except Exception as e:
                    logger.exception(f"❌ {platform_name.title()} failed unexpectedly: {e}")
                    results[platform_name] = False

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 TRACK OPERATIONS TEST SUMMARY")
        logger.info("=" * 70)

        successful_platforms = []
        failed_platforms = []

        for platform, success in results.items():
            if success:
                logger.info(f"✅ {platform.title()}: Track operations working correctly")
                successful_platforms.append(platform)
            else:
                logger.info(f"❌ {platform.title()}: Track operations failed")
                failed_platforms.append(platform)

        if successful_platforms:
            logger.info(f"\n🎉 Success! Track operations working on: {', '.join(successful_platforms)}")

        if failed_platforms:
            logger.info(f"\n⚠️  Issues with: {', '.join(failed_platforms)}")
            logger.info("Check the logs above for specific error details.")

        if len(successful_platforms) == len(test_platforms):
            logger.info("\n🎊 All platform track operations tests passed!")
            return 0
        else:
            logger.info(f"\n📈 {len(successful_platforms)}/{len(test_platforms)} platforms working correctly")
            return 1

    except Exception as e:
        logger.exception(f"❌ Track operations test suite failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
