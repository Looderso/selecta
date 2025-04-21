"""Tests for bidirectional synchronization across all platforms."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from selecta.core.data.models.db import (
    Playlist,
    PlaylistPlatformInfo,
    PlaylistSyncState,
    Track,
)
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.sync_manager import PlatformSyncManager

# Test fixture constants
TEST_PLAYLIST_NAME = "Test Sync Playlist"
PLATFORMS = ["spotify", "rekordbox", "youtube", "discogs"]


class MockPlatform(AbstractPlatform):
    """Mock platform implementation for testing."""

    def __init__(self, platform_name: str, settings_repo: SettingsRepository | None = None):
        super().__init__(settings_repo)
        self.platform_name = platform_name
        self.playlists = {}
        self.tracks = {}
        self.is_auth = True

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials."""
        return self.is_auth

    def authenticate(self) -> bool:
        """Perform the authentication flow for this platform."""
        self.is_auth = True
        return True

    def get_all_playlists(self) -> list[Any]:
        """Get all playlists from this platform."""
        return list(self.playlists.values())

    def get_playlist_tracks(self, playlist_id: str) -> list[Any]:
        """Get all tracks in a specific playlist."""
        if playlist_id not in self.playlists:
            return []

        track_ids = self.playlists[playlist_id]["track_ids"]
        return [self.tracks[tid] for tid in track_ids if tid in self.tracks]

    def search_tracks(self, query: str, limit: int = 10) -> list[Any]:
        """Search for tracks on this platform."""
        results = []
        for _, track in self.tracks.items():
            # Simple search implementation
            if query.lower() in track["name"].lower() or query.lower() in track["artist"].lower():
                results.append(track)
                if len(results) >= limit:
                    break
        return results

    def create_playlist(self, name: str, description: str = "") -> Any:
        """Create a new playlist on this platform."""
        new_id = f"{self.platform_name}_{name.replace(' ', '_')}"
        self.playlists[new_id] = {
            "name": name,
            "id": new_id,
            "description": description,
            "track_ids": [],
        }
        return self.playlists[new_id]

    def import_playlist_to_local(self, platform_playlist_id: str) -> tuple[list[Any], Any]:
        """Return tracks and playlist data for the given playlist ID."""
        if platform_playlist_id not in self.playlists:
            return [], {}

        playlist_data = self.playlists[platform_playlist_id]
        tracks = [
            self.tracks[track_id]
            for track_id in playlist_data["track_ids"]
            if track_id in self.tracks
        ]
        return tracks, playlist_data

    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Add tracks to a platform playlist."""
        if playlist_id not in self.playlists:
            return False

        # Add only valid tracks
        valid_track_ids = [tid for tid in track_ids if tid in self.tracks]
        self.playlists[playlist_id]["track_ids"].extend(valid_track_ids)
        return True

    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Remove tracks from a platform playlist."""
        if playlist_id not in self.playlists:
            return False

        for track_id in track_ids:
            if track_id in self.playlists[playlist_id]["track_ids"]:
                self.playlists[playlist_id]["track_ids"].remove(track_id)
        return True

    def export_tracks_to_playlist(
        self, playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None
    ) -> str:
        """Create or update a playlist with the given tracks."""
        if existing_playlist_id and existing_playlist_id in self.playlists:
            # Update existing playlist
            self.playlists[existing_playlist_id]["track_ids"] = [
                t for t in track_ids if t in self.tracks
            ]
            return existing_playlist_id
        else:
            # Create new playlist
            new_id = f"{self.platform_name}_{playlist_name.replace(' ', '_')}"
            self.playlists[new_id] = {
                "name": playlist_name,
                "id": new_id,
                "track_ids": [t for t in track_ids if t in self.tracks],
            }
            return new_id

    # Helper methods for test setup
    def add_mock_playlist(self, playlist_id, name, tracks=None):
        """Add a mock playlist with optional tracks."""
        self.playlists[playlist_id] = {"id": playlist_id, "name": name, "track_ids": tracks or []}

    def add_mock_track(self, track_id, name, artist):
        """Add a mock track with basic properties."""
        _ = self.platform_name[0].upper()
        self.tracks[track_id] = {
            "id": track_id,
            "name": name,
            "title": name,
            "artist": artist,
            "artist_names": [artist],
            "platform_id": track_id,
        }


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    with patch("sqlalchemy.orm.Session") as mock:
        mock_session = MagicMock()
        mock.return_value = mock_session
        # Setup methods for session behaviors
        mock_session.query.return_value.filter.return_value.first.return_value = None
        yield mock_session


@pytest.fixture
def mock_platform_clients():
    """Create mock platform clients for each supported platform."""
    clients = {}
    for platform in PLATFORMS:
        clients[platform] = MockPlatform(platform)
    yield clients


@pytest.fixture
def mock_repositories(mock_session):
    """Create mock repositories with the mock session."""
    track_repo = TrackRepository(session=mock_session)
    playlist_repo = PlaylistRepository(session=mock_session)

    # Mock required repository methods
    track_repo.create = MagicMock(return_value=Track(id=1, title="Test", artist="Test Artist"))
    track_repo.get_by_platform_id = MagicMock(return_value=None)
    track_repo.add_platform_info = MagicMock()

    playlist_repo.create = MagicMock(return_value=Playlist(id=1, name=TEST_PLAYLIST_NAME))
    playlist_repo.get_by_id = MagicMock(return_value=Playlist(id=1, name=TEST_PLAYLIST_NAME))

    # Set up platform info correctly for each platform
    def get_platform_info_side_effect(playlist_id, platform_name):
        if playlist_id == 1 and platform_name in PLATFORMS:
            platform_info = PlaylistPlatformInfo(
                id=1,
                playlist_id=1,
                platform=platform_name,
                platform_id=f"{platform_name}_playlist",
                is_personal_playlist=True,
            )
            # Add sync state to platform_info
            sync_state = PlaylistSyncState(
                platform_info_id=1,
                track_snapshot=json.dumps({"platform_tracks": {}, "library_tracks": {}}),
            )
            platform_info.sync_state = sync_state
            return platform_info
        return None

    playlist_repo.get_platform_info = MagicMock(side_effect=get_platform_info_side_effect)
    playlist_repo.add_platform_info = MagicMock()
    playlist_repo.add_track = MagicMock()
    playlist_repo.remove_track = MagicMock()
    playlist_repo.get_all = MagicMock(return_value=[])
    playlist_repo.get_playlist_tracks = MagicMock(return_value=[])

    yield track_repo, playlist_repo


@pytest.fixture
def setup_test_data(mock_platform_clients, mock_repositories):
    """Setup test data across all platforms and library."""
    track_repo, playlist_repo = mock_repositories

    # Setup initial test tracks for each platform
    for platform_name, client in mock_platform_clients.items():
        # Add 10 platform-specific tracks
        for i in range(1, 11):
            track_id = f"{platform_name}_track_{i}"
            client.add_mock_track(
                track_id=track_id,
                name=f"{platform_name.capitalize()} Track {i}",
                artist=f"{platform_name.capitalize()} Artist",
            )

        # Create a playlist with the first 5 tracks
        playlist_id = f"{platform_name}_playlist"
        track_ids = [f"{platform_name}_track_{i}" for i in range(1, 6)]
        client.add_mock_playlist(playlist_id=playlist_id, name=TEST_PLAYLIST_NAME, tracks=track_ids)

    # Mock library setup
    # Create a mock playlist in the library
    library_playlist = Playlist(id=1, name=TEST_PLAYLIST_NAME)
    playlist_repo.get_by_id.return_value = library_playlist

    # Create platform info entries for each platform
    platform_infos = []
    for platform in PLATFORMS:
        platform_info = PlaylistPlatformInfo(
            id=len(platform_infos) + 1,
            playlist_id=1,
            platform=platform,
            platform_id=f"{platform}_playlist",
            is_personal_playlist=True,
        )
        platform_infos.append(platform_info)

    library_playlist.platform_info = platform_infos

    # Mock track repository to return appropriate platform-specific tracks
    def get_by_platform_id_side_effect(platform, platform_id):
        if platform_id.startswith(platform):
            # Extract track number from ID
            track_num = int(platform_id.split("_")[-1])
            return Track(
                id=track_num,
                title=f"{platform.capitalize()} Track {track_num}",
                artist=f"{platform.capitalize()} Artist",
            )
        return None

    track_repo.get_by_platform_id.side_effect = get_by_platform_id_side_effect

    # We already have the get_platform_info mocked in the mock_repositories fixture
    # No need to override it here
    # platform_info objects are already available in the playlist.platform_info list

    # Mock get_playlist_tracks to return appropriate tracks
    playlist_tracks = [
        Track(id=i, title=f"Library Track {i}", artist="Library Artist") for i in range(1, 6)
    ]

    # Add platform info to each track
    for i, track in enumerate(playlist_tracks):
        track.platform_info = []
        for platform in PLATFORMS:
            track_platform_info = MagicMock()
            track_platform_info.platform = platform
            track_platform_info.platform_id = f"{platform}_track_{i + 1}"
            track.platform_info.append(track_platform_info)

    playlist_repo.get_playlist_tracks.return_value = playlist_tracks

    yield track_repo, playlist_repo, mock_platform_clients


def test_bidirectional_sync_add_track_on_platform(setup_test_data):
    """Test syncing a track added on the platform to the library."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Choose one platform for this test
    platform_name = "spotify"
    platform_client = platform_clients[platform_name]

    # Add a new track to the platform playlist
    new_track_id = f"{platform_name}_track_6"
    platform_client.add_mock_track(
        track_id=new_track_id,
        name=f"{platform_name.capitalize()} Track 6",
        artist=f"{platform_name.capitalize()} Artist",
    )
    platform_client.playlists[f"{platform_name}_playlist"]["track_ids"].append(new_track_id)

    # Create sync manager with the mock platform client
    with (
        patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager._get_sync_state"
        ) as mock_get_sync_state,
        patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager._find_library_track_by_platform_id"
        ) as mock_find_library,
    ):
        # Set up mock to return sync state
        mock_sync_state = MagicMock()
        mock_sync_state.get_snapshot.return_value = {
            "platform_tracks": {
                f"{platform_name}_track_1": {"library_id": 1},
                f"{platform_name}_track_2": {"library_id": 2},
                f"{platform_name}_track_3": {"library_id": 3},
                f"{platform_name}_track_4": {"library_id": 4},
                f"{platform_name}_track_5": {"library_id": 5},
            },
            "library_tracks": {
                "1": {"platform_id": f"{platform_name}_track_1"},
                "2": {"platform_id": f"{platform_name}_track_2"},
                "3": {"platform_id": f"{platform_name}_track_3"},
                "4": {"platform_id": f"{platform_name}_track_4"},
                "5": {"platform_id": f"{platform_name}_track_5"},
            },
        }
        mock_get_sync_state.return_value = mock_sync_state

        # Setup mock for finding library tracks
        mock_find_library.return_value = None

        sync_manager = PlatformSyncManager(
            platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
        )

        # Mock the get_platform_info method directly
        mock_platform_info = MagicMock()
        mock_platform_info.platform_id = f"{platform_name}_playlist"
        mock_platform_info.is_personal_playlist = True
        playlist_repo.get_platform_info.return_value = mock_platform_info

        # Run the sync
        changes = sync_manager.get_sync_changes(1)

    # Verify we detected the track addition
    assert len(changes.platform_additions) == 1
    assert changes.platform_additions[0].platform_track_id == new_track_id

    # Apply the sync changes with patching the _get_sync_state method for apply_sync_changes
    with patch(
        "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
    ) as mock_save_snapshot:
        mock_save_snapshot.return_value = None
        all_selected = {change.change_id: True for change in changes.platform_additions}
        result = sync_manager.apply_sync_changes(1, all_selected)

    # Verify the result
    assert result.platform_additions_applied == 1


def test_bidirectional_sync_remove_track_on_platform(setup_test_data):
    """Test syncing a track removed on the platform."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Choose one platform for this test
    platform_name = "spotify"
    platform_client = platform_clients[platform_name]

    # Remove a track from the platform playlist
    playlist_id = f"{platform_name}_playlist"
    track_to_remove = f"{platform_name}_track_3"

    platform_client.playlists[playlist_id]["track_ids"].remove(track_to_remove)

    # Create sync manager with the mock platform client
    with (
        patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager._get_sync_state"
        ) as mock_get_sync_state,
        patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager._find_library_track_by_platform_id"
        ) as mock_find_library,
    ):
        # Set up mock to return sync state
        mock_sync_state = MagicMock()
        mock_sync_state.get_snapshot.return_value = {
            "platform_tracks": {
                f"{platform_name}_track_1": {"library_id": 1},
                f"{platform_name}_track_2": {"library_id": 2},
                f"{platform_name}_track_3": {"library_id": 3},
                f"{platform_name}_track_4": {"library_id": 4},
                f"{platform_name}_track_5": {"library_id": 5},
            },
            "library_tracks": {
                "1": {"platform_id": f"{platform_name}_track_1"},
                "2": {"platform_id": f"{platform_name}_track_2"},
                "3": {"platform_id": f"{platform_name}_track_3"},
                "4": {"platform_id": f"{platform_name}_track_4"},
                "5": {"platform_id": f"{platform_name}_track_5"},
            },
        }
        mock_get_sync_state.return_value = mock_sync_state

        # Setup mock for finding library tracks
        mock_find_library.return_value = None

        sync_manager = PlatformSyncManager(
            platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
        )

        # Mock the get_platform_info method directly
        mock_platform_info = MagicMock()
        mock_platform_info.platform_id = f"{platform_name}_playlist"
        mock_platform_info.is_personal_playlist = True
        playlist_repo.get_platform_info.return_value = mock_platform_info

        # Run the sync
        changes = sync_manager.get_sync_changes(1)

    # Verify we detected the track removal
    assert len(changes.platform_removals) == 1
    assert changes.platform_removals[0].platform_track_id == track_to_remove

    # Apply the sync changes with patching
    with patch(
        "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
    ) as mock_save_snapshot:
        mock_save_snapshot.return_value = None
        all_selected = {change.change_id: True for change in changes.platform_removals}
        result = sync_manager.apply_sync_changes(1, all_selected)

    # Verify the result
    assert result.platform_removals_applied == 1


def test_bidirectional_sync_add_track_in_library(setup_test_data):
    """Test syncing a track added in the library to the platform."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Choose one platform for this test
    platform_name = "spotify"
    platform_client = platform_clients[platform_name]

    # Add a new track to the library playlist
    new_track = Track(id=6, title="New Library Track", artist="Library Artist")

    # Add platform info to the new track
    new_track_id = f"{platform_name}_track_6"
    track_platform_info = MagicMock()
    track_platform_info.platform = platform_name
    track_platform_info.platform_id = new_track_id
    new_track.platform_info = [track_platform_info]

    # Add the track to the library playlist
    track_repo.get_by_id = MagicMock(return_value=new_track)

    # Update the playlist tracks to include the new track
    playlist_tracks = playlist_repo.get_playlist_tracks.return_value
    playlist_tracks.append(new_track)

    # Create the platform track
    platform_client.add_mock_track(
        track_id=new_track_id, name="New Library Track", artist="Library Artist"
    )

    # Create sync manager with the mock platform client
    sync_manager = PlatformSyncManager(
        platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
    )
    sync_manager._find_library_track_by_platform_id = MagicMock(return_value=None)

    # Mock sync_state to make get_sync_changes detect the addition
    playlist_info = playlist_repo.get_platform_info(1, platform_name)
    sync_state = PlaylistSyncState(
        platform_info_id=playlist_info.id,
        track_snapshot=json.dumps(
            {
                "platform_tracks": {
                    f"{platform_name}_track_1": {"library_id": 1},
                    f"{platform_name}_track_2": {"library_id": 2},
                    f"{platform_name}_track_3": {"library_id": 3},
                    f"{platform_name}_track_4": {"library_id": 4},
                    f"{platform_name}_track_5": {"library_id": 5},
                },
                "library_tracks": {
                    "1": {"platform_id": f"{platform_name}_track_1"},
                    "2": {"platform_id": f"{platform_name}_track_2"},
                    "3": {"platform_id": f"{platform_name}_track_3"},
                    "4": {"platform_id": f"{platform_name}_track_4"},
                    "5": {"platform_id": f"{platform_name}_track_5"},
                },
            }
        ),
    )
    playlist_info.sync_state = sync_state

    # Run the sync
    changes = sync_manager.get_sync_changes(1)

    # Verify we detected the library track addition
    assert len(changes.library_additions) == 1
    assert changes.library_additions[0].library_track_id == 6

    # Apply the sync changes with patching
    with patch(
        "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
    ) as mock_save_snapshot:
        mock_save_snapshot.return_value = None
        all_selected = {change.change_id: True for change in changes.library_additions}
        result = sync_manager.apply_sync_changes(1, all_selected)

    # Verify the result
    assert result.library_additions_applied == 1


def test_bidirectional_sync_remove_track_in_library(setup_test_data):
    """Test syncing a track removed in the library to the platform."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Choose one platform for this test
    platform_name = "spotify"
    platform_client = platform_clients[platform_name]

    # Remove a track from the library playlist
    original_tracks = playlist_repo.get_playlist_tracks.return_value
    removed_track = original_tracks[2]  # Track ID 3

    # Update the playlist tracks to remove the track
    playlist_repo.get_playlist_tracks.return_value = [
        t for t in original_tracks if t.id != removed_track.id
    ]

    # Create sync manager with the mock platform client
    sync_manager = PlatformSyncManager(
        platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
    )
    sync_manager._find_library_track_by_platform_id = MagicMock(return_value=None)

    # Mock sync_state to make get_sync_changes detect the removal
    playlist_info = playlist_repo.get_platform_info(1, platform_name)
    sync_state = PlaylistSyncState(
        platform_info_id=playlist_info.id,
        track_snapshot=json.dumps(
            {
                "platform_tracks": {
                    f"{platform_name}_track_1": {"library_id": 1},
                    f"{platform_name}_track_2": {"library_id": 2},
                    f"{platform_name}_track_3": {"library_id": 3},
                    f"{platform_name}_track_4": {"library_id": 4},
                    f"{platform_name}_track_5": {"library_id": 5},
                },
                "library_tracks": {
                    "1": {"platform_id": f"{platform_name}_track_1"},
                    "2": {"platform_id": f"{platform_name}_track_2"},
                    "3": {"platform_id": f"{platform_name}_track_3"},
                    "4": {"platform_id": f"{platform_name}_track_4"},
                    "5": {"platform_id": f"{platform_name}_track_5"},
                },
            }
        ),
    )
    playlist_info.sync_state = sync_state

    # Run the sync
    changes = sync_manager.get_sync_changes(1)

    # Verify we detected the library track removal
    assert len(changes.library_removals) == 1
    assert changes.library_removals[0].library_track_id == 3

    # Apply the sync changes with patching
    with patch(
        "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
    ) as mock_save_snapshot:
        mock_save_snapshot.return_value = None
        all_selected = {change.change_id: True for change in changes.library_removals}
        result = sync_manager.apply_sync_changes(1, all_selected)

    # Verify the result
    assert result.library_removals_applied == 1


def test_bidirectional_sync_multi_platform_changes(setup_test_data):
    """Test syncing changes across multiple platforms simultaneously."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Make different changes on each platform
    changes_by_platform = {
        "spotify": {"added": ["spotify_track_6"], "removed": ["spotify_track_3"]},
        "rekordbox": {"added": ["rekordbox_track_7"], "removed": ["rekordbox_track_1"]},
        "youtube": {"added": ["youtube_track_8"], "removed": ["youtube_track_2"]},
        "discogs": {"added": ["discogs_track_9"], "removed": ["discogs_track_4"]},
    }

    # Apply the changes to the mock platforms
    for platform_name, changes in changes_by_platform.items():
        platform_client = platform_clients[platform_name]
        playlist_id = f"{platform_name}_playlist"

        # Add new tracks to the platform
        for track_id in changes["added"]:
            platform_client.add_mock_track(
                track_id=track_id,
                name=f"{platform_name.capitalize()} New Track",
                artist=f"{platform_name.capitalize()} Artist",
            )
            platform_client.playlists[playlist_id]["track_ids"].append(track_id)

        # Remove tracks from the platform
        for track_id in changes["removed"]:
            if track_id in platform_client.playlists[playlist_id]["track_ids"]:
                platform_client.playlists[playlist_id]["track_ids"].remove(track_id)

    # Test syncing with each platform
    for platform_name in PLATFORMS:
        platform_client = platform_clients[platform_name]

        # Create sync manager for this platform
        sync_manager = PlatformSyncManager(
            platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
        )

        # Mock sync_state for this platform
        playlist_info = playlist_repo.get_platform_info(1, platform_name)
        track_ids = [f"{platform_name}_track_{i}" for i in range(1, 6)]

        platform_tracks = {}
        library_tracks = {}
        for i, track_id in enumerate(track_ids, 1):
            platform_tracks[track_id] = {"library_id": i}
            library_tracks[str(i)] = {"platform_id": track_id}

        sync_state = PlaylistSyncState(
            platform_info_id=playlist_info.id,
            track_snapshot=json.dumps(
                {"platform_tracks": platform_tracks, "library_tracks": library_tracks}
            ),
        )
        playlist_info.sync_state = sync_state

        # Run the sync
        changes = sync_manager.get_sync_changes(1)

        # Verify we detected the expected changes
        platform_changes = changes_by_platform[platform_name]
        assert len(changes.platform_additions) == len(platform_changes["added"])
        assert len(changes.platform_removals) == len(platform_changes["removed"])

        # Apply the changes with patching
        with patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
        ) as mock_save_snapshot:
            mock_save_snapshot.return_value = None
            all_selected = {}
            for change in changes.platform_additions + changes.platform_removals:
                all_selected[change.change_id] = True

            result = sync_manager.apply_sync_changes(1, all_selected)

        # Verify the results
        assert result.platform_additions_applied == len(platform_changes["added"])
        assert result.platform_removals_applied == len(platform_changes["removed"])


def test_bidirectional_sync_conflicts(setup_test_data):
    """Test handling conflicts when the same track is modified differently on multiple platforms."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Setup conflict scenario:
    # - Track 3 is removed on Spotify but kept on other platforms
    # - Track 4 is kept on Spotify but removed on other platforms

    # Remove track 3 from Spotify
    spotify_client = platform_clients["spotify"]
    spotify_playlist_id = "spotify_playlist"
    track_to_remove = "spotify_track_3"
    spotify_client.playlists[spotify_playlist_id]["track_ids"].remove(track_to_remove)

    # Remove track 4 from other platforms
    for platform_name in ["rekordbox", "youtube", "discogs"]:
        platform_client = platform_clients[platform_name]
        playlist_id = f"{platform_name}_playlist"
        track_to_remove = f"{platform_name}_track_4"
        platform_client.playlists[playlist_id]["track_ids"].remove(track_to_remove)

    # Run the tests for each platform
    for platform_name in PLATFORMS:
        platform_client = platform_clients[platform_name]

        # Create sync manager for this platform
        sync_manager = PlatformSyncManager(
            platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
        )

        # Mock sync_state for this platform
        playlist_info = playlist_repo.get_platform_info(1, platform_name)
        track_ids = [f"{platform_name}_track_{i}" for i in range(1, 6)]

        platform_tracks = {}
        library_tracks = {}
        for i, track_id in enumerate(track_ids, 1):
            platform_tracks[track_id] = {"library_id": i}
            library_tracks[str(i)] = {"platform_id": track_id}

        sync_state = PlaylistSyncState(
            platform_info_id=playlist_info.id,
            track_snapshot=json.dumps(
                {"platform_tracks": platform_tracks, "library_tracks": library_tracks}
            ),
        )
        playlist_info.sync_state = sync_state

        # Run the sync
        changes = sync_manager.get_sync_changes(1)

        # Verify the appropriate changes are detected for each platform
        if platform_name == "spotify":
            # Spotify should detect removal of track 3
            assert any(
                change.platform_track_id == "spotify_track_3"
                for change in changes.platform_removals
            )
        else:
            # Other platforms should detect removal of track 4
            assert any(
                change.platform_track_id == f"{platform_name}_track_4"
                for change in changes.platform_removals
            )

        # Apply only the platform removals with patching
        with patch(
            "selecta.core.platform.sync_manager.PlatformSyncManager.save_sync_snapshot"
        ) as mock_save_snapshot:
            mock_save_snapshot.return_value = None
            removal_changes = {change.change_id: True for change in changes.platform_removals}
            result = sync_manager.apply_sync_changes(1, removal_changes)

        # Verify the results
        if platform_name == "spotify":
            assert result.platform_removals_applied == 1
        else:
            assert result.platform_removals_applied == 1


def test_bidirectional_sync_non_linkable_tracks(setup_test_data):
    """Test handling tracks that can't be linked between platforms."""
    track_repo, playlist_repo, platform_clients = setup_test_data

    # Choose one platform for this test
    platform_name = "spotify"
    platform_client = platform_clients[platform_name]

    # Add a track that has no metadata and can't be linked
    new_track_id = f"{platform_name}_unlinkable"
    platform_client.add_mock_track(track_id=new_track_id, name="Unlinkable Track", artist="Unknown")
    platform_client.playlists[f"{platform_name}_playlist"]["track_ids"].append(new_track_id)

    # Make track_repo.get_by_platform_id return None for this track
    original_side_effect = track_repo.get_by_platform_id.side_effect

    def modified_side_effect(platform, platform_id):
        if platform_id == new_track_id:
            return None
        return original_side_effect(platform, platform_id)

    track_repo.get_by_platform_id.side_effect = modified_side_effect

    # Create sync manager with the mock platform client
    sync_manager = PlatformSyncManager(
        platform_client=platform_client, track_repo=track_repo, playlist_repo=playlist_repo
    )
    sync_manager._find_library_track_by_platform_id = MagicMock(return_value=None)

    # Mock sync_state
    playlist_info = playlist_repo.get_platform_info(1, platform_name)
    sync_state = PlaylistSyncState(
        platform_info_id=playlist_info.id,
        track_snapshot=json.dumps(
            {
                "platform_tracks": {
                    f"{platform_name}_track_1": {"library_id": 1},
                    f"{platform_name}_track_2": {"library_id": 2},
                    f"{platform_name}_track_3": {"library_id": 3},
                    f"{platform_name}_track_4": {"library_id": 4},
                    f"{platform_name}_track_5": {"library_id": 5},
                },
                "library_tracks": {
                    "1": {"platform_id": f"{platform_name}_track_1"},
                    "2": {"platform_id": f"{platform_name}_track_2"},
                    "3": {"platform_id": f"{platform_name}_track_3"},
                    "4": {"platform_id": f"{platform_name}_track_4"},
                    "5": {"platform_id": f"{platform_name}_track_5"},
                },
            }
        ),
    )
    playlist_info.sync_state = sync_state

    # Run the sync
    changes = sync_manager.get_sync_changes(1)

    # Verify we detected the unlinkable track
    assert len(changes.platform_additions) == 1
    assert changes.platform_additions[0].platform_track_id == new_track_id
    assert changes.platform_additions[0].library_track_id is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
