"""Configuration for integration tests.

These tests require real authentication and network access.
Set up authentication before running:

    selecta auth spotify
    selecta auth youtube
    # Ensure Rekordbox database is accessible

Run integration tests with:
    pytest src/tests/platform/integration/ -m integration
"""

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (require real auth)")


@pytest.fixture(scope="session", autouse=True)
def integration_test_warning():
    """Warn about integration test requirements."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("These tests require:")
    print("- Real platform authentication")
    print("- Network connectivity")
    print("- May create test playlists on your accounts")
    print("=" * 60 + "\n")
