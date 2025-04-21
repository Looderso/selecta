"""Platform-specific integration components for playlist UI."""

# Core platform functionality
from selecta.ui.components.playlist.platform.base_platform_provider import BasePlatformDataProvider
from selecta.ui.components.playlist.platform.discogs.discogs_data_provider import DiscogsDataProvider
from selecta.ui.components.playlist.platform.platform_init import initialize_platforms
from selecta.ui.components.playlist.platform.platform_registry import get_platform_registry
from selecta.ui.components.playlist.platform.rekordbox.rekordbox_data_provider import RekordboxDataProvider

# Platform-specific providers
from selecta.ui.components.playlist.platform.spotify.spotify_data_provider import SpotifyDataProvider
from selecta.ui.components.playlist.platform.youtube.youtube_data_provider import YouTubeDataProvider

__all__ = [
    # Core platform functionality
    "BasePlatformDataProvider",
    "initialize_platforms",
    "get_platform_registry",
    # Platform providers
    "SpotifyDataProvider",
    "YouTubeDataProvider",
    "RekordboxDataProvider",
    "DiscogsDataProvider",
]
