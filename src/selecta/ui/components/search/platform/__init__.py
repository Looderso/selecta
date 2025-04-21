"""Platform-specific search implementations."""

# Import platform-specific implementations
from selecta.ui.components.search.platform.discogs import DiscogsReleaseItem, DiscogsSearchPanel
from selecta.ui.components.search.platform.spotify import SpotifySearchPanel, SpotifyTrackItem
from selecta.ui.components.search.platform.youtube import YouTubeSearchPanel, YouTubeVideoItem

__all__ = [
    "SpotifySearchPanel",
    "SpotifyTrackItem",
    "YouTubeSearchPanel",
    "YouTubeVideoItem",
    "DiscogsSearchPanel",
    "DiscogsReleaseItem",
]
