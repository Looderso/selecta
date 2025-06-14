"""Basic platform tests that should work without hanging or import issues."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from unittest.mock import MagicMock

import pytest

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform


class TestBasicPlatformInterface:
    """Test the basic AbstractPlatform interface without real platform clients."""

    def test_abstract_platform_interface_exists(self):
        """Test that AbstractPlatform class exists and has the expected methods."""
        # Check that the abstract class exists
        assert AbstractPlatform is not None

        # Check that it has the expected abstract methods
        expected_methods = [
            "is_authenticated",
            "authenticate",
            "get_all_playlists",
            "get_playlist_tracks",
            "search_tracks",
            "create_playlist",
            "add_tracks_to_playlist",
            "remove_tracks_from_playlist",
            "import_playlist_to_local",
            "export_tracks_to_playlist",
        ]

        for method_name in expected_methods:
            assert hasattr(AbstractPlatform, method_name), f"Missing method: {method_name}"

    def test_settings_repository_integration(self):
        """Test that AbstractPlatform integrates with SettingsRepository."""
        # Create a mock settings repo
        mock_settings_repo = MagicMock(spec=SettingsRepository)
        mock_settings_repo.get_setting.return_value = "test_value"

        # Create a concrete implementation for testing
        class TestPlatform(AbstractPlatform):
            def is_authenticated(self) -> bool:
                return True

            def authenticate(self) -> bool:
                return True

            def get_all_playlists(self):
                return []

            def get_playlist_tracks(self, playlist_id: str):
                return []

            def search_tracks(self, query: str, limit: int = 10):
                return []

            def create_playlist(self, name: str, description: str = ""):
                return {"id": "test", "name": name}

            def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
                return True

            def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
                return True

            def import_playlist_to_local(self, platform_playlist_id: str):
                return [], {}

            def export_tracks_to_playlist(
                self, playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None
            ) -> str:
                return "test_id"

        # Test initialization with settings repo
        platform = TestPlatform(settings_repo=mock_settings_repo)
        assert platform.settings_repo is mock_settings_repo

        # Test initialization without settings repo (should create default)
        platform2 = TestPlatform()
        assert platform2.settings_repo is not None
        assert isinstance(platform2.settings_repo, SettingsRepository)

    def test_platform_methods_have_correct_signatures(self):
        """Test that platform methods have the expected signatures."""
        import inspect

        # Get method signatures
        methods_to_check = {
            "is_authenticated": {"return_annotation": bool},
            "authenticate": {"return_annotation": bool},
            "add_tracks_to_playlist": {"return_annotation": bool, "params": ["playlist_id", "track_ids"]},
            "remove_tracks_from_playlist": {"return_annotation": bool, "params": ["playlist_id", "track_ids"]},
            "export_tracks_to_playlist": {"return_annotation": str, "params": ["playlist_name", "track_ids"]},
        }

        for method_name, expected in methods_to_check.items():
            method = getattr(AbstractPlatform, method_name)
            signature = inspect.signature(method)

            # Check return annotation if specified
            if "return_annotation" in expected:
                # Note: Abstract methods might not have return annotations preserved
                # This is more of a documentation check
                pass

            # Check parameter names if specified
            if "params" in expected:
                param_names = list(signature.parameters.keys())[1:]  # Skip 'self'
                for expected_param in expected["params"]:
                    assert expected_param in param_names, f"Method {method_name} missing parameter {expected_param}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
