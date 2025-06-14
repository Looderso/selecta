#!/usr/bin/env python3
"""Setup and verify test environment for safe platform testing.

This script helps set up the testing environment and verifies that
all safety systems are working correctly before running platform tests.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from loguru import logger

from selecta.core.testing import SafetyGuard


def setup_environment():
    """Set up environment variables for testing."""
    logger.info("🔧 Setting up test environment...")

    # Set environment to indicate we're in test mode
    os.environ["SELECTA_ENVIRONMENT"] = "testing"

    # Configure safety level (can be overridden)
    if "SELECTA_SAFETY_LEVEL" not in os.environ:
        os.environ["SELECTA_SAFETY_LEVEL"] = "test_only"

    # Enable confirmation by default for manual testing
    if "SELECTA_REQUIRE_CONFIRMATION" not in os.environ:
        os.environ["SELECTA_REQUIRE_CONFIRMATION"] = "false"  # Auto-confirm for scripts

    # Disable dry run by default
    if "SELECTA_DRY_RUN" not in os.environ:
        os.environ["SELECTA_DRY_RUN"] = "false"

    logger.info(f"  Environment: {os.environ['SELECTA_ENVIRONMENT']}")
    logger.info(f"  Safety Level: {os.environ['SELECTA_SAFETY_LEVEL']}")
    logger.info(f"  Require Confirmation: {os.environ['SELECTA_REQUIRE_CONFIRMATION']}")
    logger.info(f"  Dry Run: {os.environ['SELECTA_DRY_RUN']}")


def verify_safety_system():
    """Verify that the safety system is working correctly."""
    logger.info("🛡️  Verifying safety system...")

    # Test safety guard initialization
    try:
        guard = SafetyGuard()
        logger.info("  ✅ SafetyGuard initialized successfully")
    except Exception as e:
        logger.error(f"  ❌ SafetyGuard initialization failed: {e}")
        return False

    # Test playlist name detection
    test_cases = [
        ("🧪 Test Playlist", True),
        ("[TEST] Another Test", True),
        ("SELECTA_TEST_Legacy", True),
        ("My Real Playlist", False),
        ("Important Music", False),
    ]

    logger.info("  Testing playlist name detection:")
    all_passed = True
    for name, should_be_test in test_cases:
        is_test = guard.is_test_playlist(name)
        if is_test == should_be_test:
            status = "✅"
        else:
            status = "❌"
            all_passed = False

        logger.info(f"    {status} '{name}' → {is_test} (expected {should_be_test})")

    if all_passed:
        logger.info("  ✅ Playlist detection working correctly")
    else:
        logger.error("  ❌ Playlist detection has issues")
        return False

    # Test environment validation
    try:
        guard.validate_test_environment()
        logger.info("  ✅ Test environment validation passed")
    except Exception as e:
        logger.error(f"  ❌ Test environment validation failed: {e}")
        return False

    return True


def check_platform_authentication():
    """Check which platforms are currently authenticated."""
    logger.info("🔐 Checking platform authentication status...")

    from selecta.core.data.repositories.settings_repository import SettingsRepository
    from selecta.core.platform.rekordbox.client import RekordboxClient
    from selecta.core.platform.spotify.client import SpotifyClient

    settings_repo = SettingsRepository()
    auth_status = {}

    # Check Spotify
    try:
        spotify_client = SpotifyClient(settings_repo)
        auth_status["Spotify"] = spotify_client.is_authenticated()
    except Exception as e:
        auth_status["Spotify"] = f"Error: {e}"

    # Check Rekordbox
    try:
        rekordbox_client = RekordboxClient(settings_repo)
        auth_status["Rekordbox"] = rekordbox_client.is_authenticated()
    except Exception as e:
        auth_status["Rekordbox"] = f"Error: {e}"

    # Display results
    for platform, status in auth_status.items():
        if status is True:
            logger.info(f"  ✅ {platform}: Authenticated")
        elif status is False:
            logger.warning(f"  ❌ {platform}: Not authenticated")
        else:
            logger.error(f"  ❌ {platform}: {status}")

    # Count authenticated platforms
    authenticated_count = sum(1 for status in auth_status.values() if status is True)
    total_count = len(auth_status)

    logger.info(f"  {authenticated_count}/{total_count} platforms authenticated")

    if authenticated_count == 0:
        logger.warning("⚠️  No platforms authenticated - tests will be limited")
        logger.info("Run authentication commands:")
        logger.info("  selecta auth spotify")
        logger.info("  selecta auth rekordbox")

    return authenticated_count > 0


def show_safety_recommendations():
    """Show safety recommendations for testing."""
    logger.info("💡 Safety Recommendations:")
    logger.info("")
    logger.info("  1. Always use test playlist markers:")
    logger.info("     - Start playlist names with 🧪 (preferred)")
    logger.info("     - Or use [TEST] prefix")
    logger.info("     - Scripts will automatically add these")
    logger.info("")
    logger.info("  2. Safety levels available:")
    logger.info("     - READ_ONLY: No modifications allowed")
    logger.info("     - TEST_ONLY: Only marked test playlists (recommended)")
    logger.info("     - INTERACTIVE: Prompts for confirmation")
    logger.info("     - DISABLED: No safety (dangerous!)")
    logger.info("")
    logger.info("  3. Environment variables:")
    logger.info("     - SELECTA_SAFETY_LEVEL=test_only")
    logger.info("     - SELECTA_DRY_RUN=true (to see what would happen)")
    logger.info("     - SELECTA_REQUIRE_CONFIRMATION=true")
    logger.info("")
    logger.info("  4. Emergency stop:")
    logger.info("     - If something goes wrong, press Ctrl+C")
    logger.info("     - All test scripts have automatic cleanup")
    logger.info("")


def main():
    """Set up and verify the test environment."""
    logger.info("🧪 Selecta Platform Testing Environment Setup")
    logger.info("=" * 50)

    try:
        # Step 1: Set up environment
        setup_environment()
        logger.info("")

        # Step 2: Verify safety system
        if not verify_safety_system():
            logger.error("❌ Safety system verification failed - do not run tests!")
            return 1
        logger.info("")

        # Step 3: Check authentication
        has_auth = check_platform_authentication()
        logger.info("")

        # Step 4: Show recommendations
        show_safety_recommendations()

        # Summary
        logger.info("✅ Test environment setup complete!")

        if has_auth:
            logger.info("🚀 Ready to run platform tests:")
            logger.info("   python scripts/test_platform_basics.py")
        else:
            logger.warning("⚠️  Authenticate platforms first before running tests")

        return 0

    except Exception as e:
        logger.exception(f"❌ Environment setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
