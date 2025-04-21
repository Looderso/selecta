"""Playlist UI components for Selecta."""

# Import icon delegates
from selecta.ui.components.playlist.icons import (
    PlatformIconDelegate,
    PlaylistIconDelegate,
    TrackImageDelegate,
    TrackQualityDelegate,
)
from selecta.ui.components.playlist.interfaces import IPlatformDataProvider
from selecta.ui.components.playlist.library.library_data_provider import LibraryDataProvider

# Import models
from selecta.ui.components.playlist.model import PlaylistTreeModel, TracksTableModel

# Import platform registry for initialization
from selecta.ui.components.playlist.platform import get_platform_registry, initialize_platforms
from selecta.ui.components.playlist.playlist_component import PlaylistComponent

# Import track components
from selecta.ui.components.playlist.track import TrackDetailsPanel

__all__ = [
    # Core components
    "PlaylistComponent",
    "IPlatformDataProvider",
    "LibraryDataProvider",
    # Platform initialization
    "initialize_platforms",
    "get_platform_registry",
    # Models
    "PlaylistTreeModel",
    "TracksTableModel",
    # Icon delegates
    "PlatformIconDelegate",
    "PlaylistIconDelegate",
    "TrackImageDelegate",
    "TrackQualityDelegate",
    # Track components
    "TrackDetailsPanel",
]
