"""Integration tests with real platform authentication.

These tests require real credentials and will open browsers for OAuth flows.
Run these manually to test actual authentication flows.
"""

import os
import sys
from unittest.mock import patch

import pytest

# Add the src directory to Python path
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.platform.youtube.client import YouTubeClient


class TestRealAuthentication:
    """Integration tests that use real authentication flows.

    These tests are marked with @pytest.mark.integration and require:
    - Real API credentials in environment variables or settings
    - User interaction for OAuth flows (browser opening)
    - Network connectivity

    Run with: pytest -m integration
    """

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("SPOTIFY_CLIENT_ID") or not os.getenv("SPOTIFY_CLIENT_SECRET"),
        reason="Spotify credentials not found in environment",
    )
    def test_spotify_real_authentication(self):
        """Test real Spotify authentication flow."""
        # Create settings repo with real credentials
        settings_repo = SettingsRepository()
        settings_repo.set_setting("spotify_client_id", os.getenv("SPOTIFY_CLIENT_ID"))
        settings_repo.set_setting("spotify_client_secret", os.getenv("SPOTIFY_CLIENT_SECRET"))
        settings_repo.set_setting("spotify_redirect_uri", "http://localhost:8080/callback")

        # Create Spotify client
        spotify_client = SpotifyClient(settings_repo=settings_repo)

        # Test authentication status (should be False initially)
        initial_auth_status = spotify_client.is_authenticated()
        print(f"Initial auth status: {initial_auth_status}")

        # Perform authentication (this will open browser)
        print("Starting Spotify authentication flow...")
        print("This will open your browser. Please complete the OAuth flow.")

        auth_result = spotify_client.authenticate()
        print(f"Authentication result: {auth_result}")

        # Check if now authenticated
        final_auth_status = spotify_client.is_authenticated()
        print(f"Final auth status: {final_auth_status}")

        # Assert authentication worked
        assert auth_result is True, "Authentication should succeed"
        assert final_auth_status is True, "Should be authenticated after auth flow"

        # Test basic API operation
        if final_auth_status:
            print("Testing API access...")
            try:
                profile = spotify_client.get_user_profile()
                print(f"User profile: {profile.get('display_name', 'Unknown')}")
                assert profile is not None
                assert "id" in profile
            except Exception as e:
                print(f"API call failed: {e}")
                pytest.fail(f"API call failed after authentication: {e}")

    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv("YOUTUBE_API_KEY"), reason="YouTube API key not found in environment")
    def test_youtube_real_authentication(self):
        """Test real YouTube authentication flow."""
        # Create settings repo with real credentials
        settings_repo = SettingsRepository()
        settings_repo.set_setting("youtube_api_key", os.getenv("YOUTUBE_API_KEY"))

        # You would also need client secrets file for full OAuth
        client_secrets_path = os.getenv("YOUTUBE_CLIENT_SECRETS")
        if client_secrets_path:
            settings_repo.set_setting("youtube_client_secrets", client_secrets_path)

        # Create YouTube client
        youtube_client = YouTubeClient(settings_repo=settings_repo)

        # Test authentication status
        initial_auth_status = youtube_client.is_authenticated()
        print(f"Initial YouTube auth status: {initial_auth_status}")

        if client_secrets_path:
            # Perform authentication (this will open browser)
            print("Starting YouTube authentication flow...")
            print("This will open your browser. Please complete the OAuth flow.")

            auth_result = youtube_client.authenticate()
            print(f"YouTube authentication result: {auth_result}")

            # Check if now authenticated
            final_auth_status = youtube_client.is_authenticated()
            print(f"Final YouTube auth status: {final_auth_status}")

            assert auth_result is True, "YouTube authentication should succeed"
            assert final_auth_status is True, "Should be authenticated after auth flow"
        else:
            print("YouTube client secrets not provided, skipping OAuth test")

    @pytest.mark.integration
    def test_authentication_independence(self):
        """Test that platform authentication states are independent."""
        # This test doesn't require credentials, just tests the isolation
        settings_repo = SettingsRepository()

        # Create multiple clients
        spotify_client = SpotifyClient(settings_repo=settings_repo)
        youtube_client = YouTubeClient(settings_repo=settings_repo)

        # Initially, both should be unauthenticated
        assert spotify_client.is_authenticated() is False
        assert youtube_client.is_authenticated() is False

        # Mock authenticate one platform
        with patch.object(spotify_client, "is_authenticated", return_value=True):
            # Spotify should appear authenticated
            assert spotify_client.is_authenticated() is True
            # YouTube should still be unauthenticated
            assert youtube_client.is_authenticated() is False


def run_integration_tests():
    """Run integration tests manually with real authentication."""
    print("🧪 Running Integration Tests with Real Authentication")
    print("=" * 60)
    print()
    print("Prerequisites:")
    print("- Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables")
    print("- Set YOUTUBE_API_KEY environment variable")
    print("- Set YOUTUBE_CLIENT_SECRETS path to client secrets JSON file")
    print("- Have a web browser available for OAuth flows")
    print()

    # Check environment variables
    missing_env = []
    if not os.getenv("SPOTIFY_CLIENT_ID"):
        missing_env.append("SPOTIFY_CLIENT_ID")
    if not os.getenv("SPOTIFY_CLIENT_SECRET"):
        missing_env.append("SPOTIFY_CLIENT_SECRET")
    if not os.getenv("YOUTUBE_API_KEY"):
        missing_env.append("YOUTUBE_API_KEY")

    if missing_env:
        print(f"❌ Missing environment variables: {', '.join(missing_env)}")
        print()
        print("Set them like this:")
        for var in missing_env:
            print(f"export {var}='your_value_here'")
        print()
        return False

    print("✅ Environment variables found")
    print()
    print("Running integration tests...")

    # Run the tests
    exit_code = pytest.main(["-v", "-m", "integration", __file__])

    return exit_code == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
