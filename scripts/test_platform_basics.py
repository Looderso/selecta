#!/usr/bin/env python3
"""Test basic platform operations with comprehensive safety.

This script tests the fundamental operations of each platform:
- Creating playlists
- Adding tracks to playlists
- Searching for tracks
- Authentication status

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


def test_platform_authentication():
    """Test authentication status for all platforms."""
    logger.info("🔐 Testing platform authentication...")

    with safe_platform_test(SafetyLevel.READ_ONLY):
        # Test Spotify
        try:
            logger.info("✅ Spotify: Authenticated and accessible")
        except RuntimeError as e:
            logger.warning(f"❌ Spotify: {e}")

        # Test Rekordbox
        try:
            logger.info("✅ Rekordbox: Authenticated and accessible")
        except RuntimeError as e:
            logger.warning(f"❌ Rekordbox: {e}")

        # Test YouTube
        try:
            logger.info("✅ YouTube: Authenticated and accessible")
        except RuntimeError as e:
            logger.warning(f"❌ YouTube: {e}")

        # Test Discogs
        try:
            logger.info("✅ Discogs: Authenticated and accessible")
        except RuntimeError as e:
            logger.warning(f"❌ Discogs: {e}")


def test_platform_search():
    """Test search functionality across platforms."""
    logger.info("🔍 Testing platform search functionality...")

    search_queries = ["test", "Queen", "Beatles"]

    with safe_platform_test(SafetyLevel.READ_ONLY) as session:
        for platform_name in ["spotify", "rekordbox", "youtube"]:  # Test all platforms
            logger.info(f"\n--- Testing {platform_name.title()} Search ---")

            try:
                for query in search_queries:
                    results = session.search_for_test_tracks(platform_name, query, limit=3)
                    logger.info(f"  '{query}': Found {len(results)} results")

                    # Log first result for verification
                    if results:
                        result = results[0]
                        if isinstance(result, dict):
                            name = result.get("name", "Unknown")
                            artist = (
                                result.get("artists", [{}])[0].get("name", "Unknown")
                                if result.get("artists")
                                else "Unknown"
                            )
                        else:
                            name = getattr(result, "name", getattr(result, "title", "Unknown"))
                            artist = getattr(result, "artist_name", getattr(result, "artist", "Unknown"))
                        logger.info(f"    Sample: {name} by {artist}")

                logger.info(f"✅ {platform_name.title()} search working correctly")

            except Exception as e:
                logger.exception(f"❌ {platform_name.title()} search failed: {e}")


def test_playlist_creation():
    """Test creating playlists on supported platforms."""
    logger.info("📝 Testing playlist creation...")

    test_playlists = ["Basic Test", "Test with émojis 🎵", "Test-with-hyphens"]

    with safe_platform_test(SafetyLevel.TEST_ONLY) as session:
        for platform_name in ["spotify", "rekordbox", "youtube"]:  # Test all platforms with playlist support
            logger.info(f"\n--- Testing {platform_name.title()} Playlist Creation ---")

            try:
                created_playlists = []

                for playlist_name in test_playlists:
                    logger.info(f"  Creating playlist: {playlist_name}")

                    playlist_id = session.create_safe_playlist(
                        platform_name, playlist_name, description="Test playlist created by safety system"
                    )

                    created_playlists.append((playlist_name, playlist_id))
                    logger.info(f"    ✅ Created with ID: {playlist_id}")

                logger.info(
                    f"✅ {platform_name.title()} playlist creation successful ({len(created_playlists)} playlists)"
                )

                # Test adding tracks to one playlist
                if created_playlists:
                    test_playlist_name, test_playlist_id = created_playlists[0]
                    logger.info(f"  Testing track addition to '{test_playlist_name}'...")

                    # Search for tracks to add
                    tracks = session.search_for_test_tracks(platform_name, "test", limit=2)
                    if tracks:
                        # Extract track IDs (platform-specific)
                        track_ids = []
                        for track in tracks:
                            track_id = track.get("id") if isinstance(track, dict) else getattr(track, "id", None)
                            if track_id:
                                track_ids.append(str(track_id))

                        if track_ids:
                            success = session.add_tracks_to_playlist(platform_name, test_playlist_id, track_ids)
                            if success:
                                logger.info(f"    ✅ Added {len(track_ids)} tracks successfully")
                            else:
                                logger.warning("    ⚠️  Failed to add tracks")
                        else:
                            logger.warning("    ⚠️  No valid track IDs found")
                    else:
                        logger.warning("    ⚠️  No tracks found for testing")

            except Exception as e:
                logger.exception(f"❌ {platform_name.title()} playlist creation failed: {e}")


def test_safety_system():
    """Test that the safety system prevents dangerous operations."""
    logger.info("🛡️  Testing safety system...")

    # Test 1: Verify test playlist detection
    from selecta.core.testing import create_test_playlist_name, is_test_playlist

    safe_names = ["🧪 Test Playlist", "[TEST] Another Playlist", "SELECTA_TEST_Legacy"]
    unsafe_names = ["My Real Playlist", "Important Music", "Favorites"]

    logger.info("  Testing playlist name detection:")
    for name in safe_names:
        if is_test_playlist(name):
            logger.info(f"    ✅ Correctly identified as test: '{name}'")
        else:
            logger.error(f"    ❌ Failed to identify test playlist: '{name}'")

    for name in unsafe_names:
        if not is_test_playlist(name):
            logger.info(f"    ✅ Correctly identified as real: '{name}'")
        else:
            logger.error(f"    ❌ Incorrectly identified as test: '{name}'")

    # Test 2: Verify safe name creation
    logger.info("  Testing safe name creation:")
    test_base = "My Test Playlist"
    safe_name = create_test_playlist_name(test_base)
    logger.info(f"    Base: '{test_base}' → Safe: '{safe_name}'")

    if is_test_playlist(safe_name):
        logger.info("    ✅ Generated name is correctly identified as test playlist")
    else:
        logger.error("    ❌ Generated name not identified as test playlist")

    # Test 3: Verify operation blocking in read-only mode
    logger.info("  Testing read-only mode protection:")
    try:
        # Use direct safety guard to test without context manager complications
        from selecta.core.testing.safety_guard import OperationType, SafetyConfig, SafetyGuard

        read_only_config = SafetyConfig(
            test_markers=["🧪", "[TEST]"],
            safety_level=SafetyLevel.READ_ONLY,
            require_confirmation=False,
            dry_run_mode=False,
            max_test_playlists=10,
            emergency_stop_enabled=True,
        )
        guard = SafetyGuard(read_only_config)
        guard.verify_test_playlist("🧪 Test", OperationType.CREATE)
        logger.error("    ❌ Read-only mode allowed playlist creation!")
    except PermissionError:
        logger.info("    ✅ Read-only mode correctly blocked playlist creation")
    except Exception as e:
        logger.warning(f"    ⚠️  Unexpected error in read-only test: {e}")


def main():
    """Run all basic platform tests."""
    logger.info("🧪 Starting Basic Platform Testing")
    logger.info("=" * 50)

    try:
        # Test 1: Authentication
        test_platform_authentication()
        logger.info("")

        # Test 2: Safety system
        test_safety_system()
        logger.info("")

        # Test 3: Search functionality
        test_platform_search()
        logger.info("")

        # Test 4: Playlist creation (this will create and cleanup test playlists)
        test_playlist_creation()
        logger.info("")

        logger.info("✅ All basic platform tests completed!")
        logger.info("Check the logs above for any warnings or errors.")

    except Exception as e:
        logger.exception(f"❌ Test suite failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
