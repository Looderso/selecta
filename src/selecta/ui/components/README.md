# UI Components Documentation

## Overview
This module contains the UI components that make up the Selecta application interface. It includes the main layout components, navigation, playlist views, and platform-specific UI elements.

## Key Components
- **MainContent**: Central component that manages the main content area
- **NavigationBar**: Top navigation bar with main app controls
- **SideDrawer**: Side menu for platform selection
- **DynamicContent**: Content area that changes based on selected view
- **Platform-specific components**: UI elements for each music platform
- **PlaylistContent**: Playlist browsing and management UI
- **Player**: Audio player controls and visualization

## File Structure
- `main_content.py`: Main content area container
- `navigation_bar.py`: Top navigation bar
- `side_drawer.py`: Side menu panel
- `dynamic_content.py`: Content switching component
- `bottom_content.py`: Bottom panel with player controls
- `search_bar.py`: Global search functionality
- `loading_widget.py`: Loading indicators
- `selection_state.py`: Shared selection state management
- `platform_auth_panel.py`: Authentication UI for platforms
- `platform_auth_widget.py`: Authentication widget components
- `platform_search_panel.py`: Search interface for platforms
- `discogs/`: Discogs-specific UI components
- `spotify/`: Spotify-specific UI components
- `youtube/`: YouTube-specific UI components
- `playlist/`: Playlist components (see playlist/README.md)
- `player/`: Audio player components

## Dependencies
- Internal: core.platform for platform clients
- External: PyQt6 for UI framework

## Common Tasks
- **Adding a new view**: Create a new component and integrate with dynamic_content.py
- **Improving platform UI**: Modify the respective platform folder components
- **Updating layout**: Modify main_content.py and related components
- **Adding UI features**: Identify the appropriate component based on feature location

## Implementation Notes
- Built using PyQt6 for cross-platform compatibility
- Uses signals/slots for communication between components
- Component hierarchy follows platform module structure
- Shared state management through selection_state.py

## Change History
- Initial UI implementation
- Added dark mode support
- Improved responsiveness
- Added platform filter controls
