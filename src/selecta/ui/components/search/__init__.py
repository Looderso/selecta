"""Search components module for Selecta UI."""

from selecta.ui.components.search.base_search_panel import BaseSearchPanel
from selecta.ui.components.search.base_search_result import BaseSearchResult
from selecta.ui.components.search.platform.discogs import DiscogsReleaseItem, DiscogsSearchPanel
from selecta.ui.components.search.platform.spotify import SpotifySearchPanel, SpotifyTrackItem
from selecta.ui.components.search.platform.youtube import YouTubeSearchPanel, YouTubeVideoItem

__all__ = [
    # Base classes
    "BaseSearchPanel",
    "BaseSearchResult",
    # Spotify implementation
    "SpotifySearchPanel",
    "SpotifyTrackItem",
    # YouTube implementation
    "YouTubeSearchPanel",
    "YouTubeVideoItem",
    # Discogs implementation
    "DiscogsSearchPanel",
    "DiscogsReleaseItem",
]
