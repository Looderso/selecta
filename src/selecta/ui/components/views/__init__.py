"""View components for the UI."""

# Use lazy imports to avoid circular dependencies
from importlib import import_module

# Import components that don't cause circular imports directly
from selecta.ui.components.views.bottom_panel import BottomContent
from selecta.ui.components.views.main_panel import MainContent
from selecta.ui.components.views.navigation_bar import NavigationBar
from selecta.ui.components.views.playlist_panel import PlaylistContent
from selecta.ui.components.views.side_drawer import SideDrawer

# Define __all__ to include all components
__all__ = [
    "BottomContent",
    "DynamicContent",
    "DynamicContentNavigationBar",
    "MainContent",
    "NavigationBar",
    "PlaylistContent",
    "PlaylistDetailsPanel",
    "SideDrawer",
    "TrackDetailsPanel",
]


# Use __getattr__ to lazy-load components that might cause circular imports
def __getattr__(name):
    if name == "DynamicContent":
        return import_module("selecta.ui.components.views.dynamic_content").DynamicContent
    elif name == "DynamicContentNavigationBar":
        return import_module("selecta.ui.components.views.dynamic_content_navigation").DynamicContentNavigationBar
    elif name == "PlaylistDetailsPanel":
        return import_module("selecta.ui.components.views.playlist_details_panel").PlaylistDetailsPanel
    elif name == "TrackDetailsPanel":
        return import_module("selecta.ui.components.views.track_details_panel").TrackDetailsPanel
    raise AttributeError(f"module {__name__} has no attribute {name}")
