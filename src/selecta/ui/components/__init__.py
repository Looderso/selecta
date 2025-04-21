"""UI Components for the Selecta application."""

# Import from components subpackages
from selecta.ui.components.auth import PlatformAuthPanel
from selecta.ui.components.common import DatabaseImageLoader, SelectionState
from selecta.ui.components.player import AudioPlayerComponent, create_youtube_player_window
from selecta.ui.components.views import (
    BottomContent,
    DynamicContent,
    MainContent,
    NavigationBar,
    PlaylistContent,
    SideDrawer,
    TrackDetailsPanel,
)

# Keep re-exports for backward compatibility
from selecta.ui.widgets import (
    FolderSelectionWidget,
    LoadingWidget,
    PlatformAuthWidget,
    SearchBar,
)

__all__ = [
    # Auth components
    "PlatformAuthPanel",
    # Common components
    "DatabaseImageLoader",
    "SelectionState",
    # Player components
    "AudioPlayerComponent",
    "create_youtube_player_window",
    # View components
    "BottomContent",
    "DynamicContent",
    "MainContent",
    "NavigationBar",
    "PlaylistContent",
    "SideDrawer",
    "TrackDetailsPanel",
    # Widget re-exports
    "FolderSelectionWidget",
    "LoadingWidget",
    "PlatformAuthWidget",
    "SearchBar",
]
