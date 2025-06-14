"""Integration tests for cross-platform workflows.

These tests use real API connections to verify that platforms work together
for creating, importing, and syncing playlists across different services.

Prerequisites:
- Valid authentication for all platforms
- Network connectivity
- Test playlists/tracks that exist on multiple platforms
"""

import pytest

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.platform.sync_manager import PlatformSyncManager
from selecta.core.platform.youtube.client import YouTubeClient


class TestCrossPlatformWorkflows:
    """Test real cross-platform playlist workflows."""

    # Test configuration - override these in CI/local env
    TEST_PLAYLIST_PREFIX = "SELECTA_TEST_"
    TEST_TRACKS = [
        # Known tracks that should exist on multiple platforms
        {"title": "Bohemian Rhapsody", "artist": "Queen"},
        {"title": "Hotel California", "artist": "Eagles"},
        {"title": "Stairway to Heaven", "artist": "Led Zeppelin"},
    ]

    @pytest.fixture(scope="class")
    def settings_repo(self):
        """Real settings repository."""
        return SettingsRepository()

    @pytest.fixture(scope="class")
    def spotify_client(self, settings_repo):
        """Real Spotify client - requires authentication."""
        client = SpotifyClient(settings_repo)
        if not client.is_authenticated():
            pytest.skip("Spotify not authenticated - run 'selecta auth spotify' first")
        return client

    @pytest.fixture(scope="class")
    def rekordbox_client(self, settings_repo):
        """Real Rekordbox client - requires database access."""
        client = RekordboxClient(settings_repo)
        if not client.is_authenticated():
            pytest.skip("Rekordbox not accessible - ensure database is available")
        return client

    @pytest.fixture(scope="class")
    def youtube_client(self, settings_repo):
        """Real YouTube client - requires authentication."""
        client = YouTubeClient(settings_repo)
        if not client.is_authenticated():
            pytest.skip("YouTube not authenticated - run 'selecta auth youtube' first")
        return client

    def cleanup_test_playlists(self, *clients):
        """Clean up any test playlists created during testing."""
        for client in clients:
            try:
                playlists = client.get_all_playlists()
                for playlist in playlists:
                    if hasattr(playlist, "name") and playlist.name.startswith(self.TEST_PLAYLIST_PREFIX):
                        # TODO: Add delete_playlist method to clients
                        print(f"TODO: Clean up test playlist: {playlist.name}")
            except Exception as e:
                print(f"Cleanup warning for {type(client).__name__}: {e}")

    @pytest.mark.integration
    def test_spotify_to_rekordbox_workflow(self, spotify_client, rekordbox_client, settings_repo):
        """Test: Create playlist on Spotify → Import to local → Export to Rekordbox."""
        test_name = f"{self.TEST_PLAYLIST_PREFIX}Spotify_to_Rekordbox"

        try:
            # Step 1: Create test playlist on Spotify
            spotify_playlist = spotify_client.create_playlist(
                name=test_name, description="Test playlist for cross-platform sync"
            )
            assert spotify_playlist, "Failed to create Spotify playlist"
            spotify_playlist_id = spotify_playlist.id

            # Step 2: Add some test tracks to Spotify playlist
            test_track_ids = []
            for track_info in self.TEST_TRACKS[:2]:  # Use first 2 tracks
                search_results = spotify_client.search_tracks(f"{track_info['title']} {track_info['artist']}", limit=1)
                if search_results:
                    # Handle different formats - dictionary or object
                    track = search_results[0]
                    track_id = track.get("id") if isinstance(track, dict) else getattr(track, "id", None)

                    if track_id:
                        test_track_ids.append(str(track_id))

            if test_track_ids:
                spotify_client.add_tracks_to_playlist(spotify_playlist_id, test_track_ids)

            # Step 3: Import from Spotify to local database
            spotify_sync_manager = PlatformSyncManager(spotify_client)
            local_playlist, imported_tracks = spotify_sync_manager.import_playlist(
                spotify_playlist_id, target_name=test_name
            )
            assert len(imported_tracks) > 0, "No tracks imported from Spotify"
            assert local_playlist.name == test_name, "Playlist name not preserved"

            # Step 4: Export to Rekordbox
            rekordbox_sync_manager = PlatformSyncManager(rekordbox_client)
            rekordbox_playlist_id = rekordbox_sync_manager.export_playlist(
                local_playlist.id, platform_playlist_name=test_name
            )
            assert rekordbox_playlist_id, "Failed to export to Rekordbox"

            # Step 5: Verify playlist exists in Rekordbox
            rekordbox_playlist = rekordbox_client.get_playlist_by_id(rekordbox_playlist_id)
            assert rekordbox_playlist, "Playlist not found in Rekordbox"
            assert rekordbox_playlist.name == test_name, "Rekordbox playlist name mismatch"

        finally:
            self.cleanup_test_playlists(spotify_client, rekordbox_client)

    @pytest.mark.integration
    def test_rekordbox_to_spotify_workflow(self, rekordbox_client, spotify_client, settings_repo):
        """Test: Create playlist on Rekordbox → Import to local → Export to Spotify."""
        test_name = f"{self.TEST_PLAYLIST_PREFIX}Rekordbox_to_Spotify"

        try:
            # Step 1: Create test playlist in Rekordbox
            rekordbox_playlist = rekordbox_client.create_playlist(test_name)
            assert rekordbox_playlist.id, "Failed to create Rekordbox playlist"

            # Step 2: Import from Rekordbox to local database
            rekordbox_sync_manager = PlatformSyncManager(rekordbox_client)
            local_playlist, imported_tracks = rekordbox_sync_manager.import_playlist(
                rekordbox_playlist.id, target_name=test_name
            )
            assert local_playlist.name == test_name, "Playlist name not preserved"

            # Step 3: Export to Spotify
            spotify_sync_manager = PlatformSyncManager(spotify_client)
            spotify_playlist_id = spotify_sync_manager.export_playlist(
                local_playlist.id, platform_playlist_name=test_name
            )
            assert spotify_playlist_id, "Failed to export to Spotify"

            # Step 4: Verify playlist exists in Spotify
            spotify_playlists = spotify_client.get_all_playlists()
            spotify_playlist = next((p for p in spotify_playlists if p.id == spotify_playlist_id), None)
            assert spotify_playlist, "Playlist not found in Spotify"
            assert spotify_playlist.name == test_name, "Spotify playlist name mismatch"

        finally:
            self.cleanup_test_playlists(rekordbox_client, spotify_client)

    @pytest.mark.integration
    def test_bidirectional_sync(self, spotify_client, rekordbox_client, settings_repo):
        """Test bidirectional sync between platforms."""
        test_name = f"{self.TEST_PLAYLIST_PREFIX}Bidirectional_Sync"

        try:
            # Create playlist on both platforms
            spotify_playlist_id = spotify_client.create_playlist(test_name)
            rekordbox_playlist = rekordbox_client.create_playlist(test_name)

            # Import both to local database
            spotify_sync_manager = PlatformSyncManager(spotify_client)
            spotify_local_playlist, spotify_tracks = spotify_sync_manager.import_playlist(
                spotify_playlist_id, target_name=f"{test_name}_Spotify"
            )

            rekordbox_sync_manager = PlatformSyncManager(rekordbox_client)
            rekordbox_local_playlist, rekordbox_tracks = rekordbox_sync_manager.import_playlist(
                rekordbox_playlist.id, target_name=f"{test_name}_Rekordbox"
            )

            # Add different tracks to each platform
            # TODO: Add tracks and test sync conflicts resolution

            # Test sync operations - for now just verify they were imported
            assert spotify_local_playlist.name == f"{test_name}_Spotify"
            assert rekordbox_local_playlist.name == f"{test_name}_Rekordbox"

            # TODO: Implement sync conflict detection and resolution

        finally:
            self.cleanup_test_playlists(spotify_client, rekordbox_client)

    @pytest.mark.integration
    def test_platform_consistency(self, spotify_client, rekordbox_client):
        """Test that platforms handle operations consistently."""
        test_name = f"{self.TEST_PLAYLIST_PREFIX}Consistency_Test"

        try:
            # Test 1: Playlist creation consistency
            spotify_playlist_id = spotify_client.create_playlist(test_name)
            rekordbox_playlist = rekordbox_client.create_playlist(test_name)

            assert spotify_playlist_id, "Spotify playlist creation failed"
            assert rekordbox_playlist.id, "Rekordbox playlist creation failed"

            # Test 2: Search consistency
            search_query = "test"
            spotify_results = spotify_client.search_tracks(search_query, limit=5)
            rekordbox_results = rekordbox_client.search_tracks(search_query, limit=5)

            assert len(spotify_results) <= 5, "Spotify search doesn't respect limit"
            assert len(rekordbox_results) <= 5, "Rekordbox search doesn't respect limit"
            assert isinstance(spotify_results, list), "Spotify search should return list"
            assert isinstance(rekordbox_results, list), "Rekordbox search should return list"

            # Test 3: Track metadata consistency
            if spotify_results and rekordbox_results:
                spotify_track = spotify_results[0]
                rekordbox_track = rekordbox_results[0]

                # Both should have basic metadata - handle different formats
                # Spotify might return dict or object, Rekordbox returns objects
                spotify_has_title = (
                    hasattr(spotify_track, "title")
                    or hasattr(spotify_track, "name")
                    or (isinstance(spotify_track, dict) and ("name" in spotify_track or "title" in spotify_track))
                )
                rekordbox_has_title = hasattr(rekordbox_track, "title") or hasattr(rekordbox_track, "name")

                spotify_has_artist = (
                    hasattr(spotify_track, "artist_name")
                    or hasattr(spotify_track, "artist")
                    or (isinstance(spotify_track, dict) and "artists" in spotify_track)
                )
                rekordbox_has_artist = hasattr(rekordbox_track, "artist_name") or hasattr(rekordbox_track, "artist")

                assert spotify_has_title, f"Spotify track missing title/name: {type(spotify_track)}"
                assert rekordbox_has_title, f"Rekordbox track missing title/name: {type(rekordbox_track)}"
                assert spotify_has_artist, f"Spotify track missing artist: {type(spotify_track)}"
                assert rekordbox_has_artist, f"Rekordbox track missing artist: {type(rekordbox_track)}"

        finally:
            self.cleanup_test_playlists(spotify_client, rekordbox_client)


@pytest.mark.integration
class TestPlatformSpecificFeatures:
    """Test platform-specific features that should be preserved during sync."""

    def test_rekordbox_bpm_preservation(self, rekordbox_client, spotify_client, sync_manager):
        """Test that BPM data from Rekordbox is preserved during sync."""
        # TODO: Test that Rekordbox BPM/key data is maintained
        pass

    def test_spotify_playlist_metadata(self, spotify_client, sync_manager):
        """Test that Spotify playlist descriptions/covers are handled properly."""
        # TODO: Test description, cover art preservation
        pass

    def test_youtube_video_links(self, youtube_client, sync_manager):
        """Test that YouTube video links are preserved for playback."""
        # TODO: Test video URL preservation
        pass
