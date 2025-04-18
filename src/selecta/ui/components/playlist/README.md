# Playlist UI Components Documentation

## Overview

The playlist module provides UI components for displaying, managing, and interacting with playlists and tracks from various platforms. It handles the presentation layer for playlist data from all platforms in a consistent way.

## Key Components

- **PlaylistComponent**: Main playlist UI component combining tree view and track list
- **PlaylistDataProvider**: Interface for platform-specific playlist data access
- **PlaylistTreeModel**: Qt model for playlist tree structure
- **TracksTableModel**: Qt model for track list display
- **Platform-specific implementations**: Specialized components for each music platform

## File Structure

- `abstract_playlist_data_provider.py`: Base class for all playlist data providers
- `playlist_component.py`: Main playlist UI component
- `playlist_data_provider.py`: Interface for playlist data access
- `playlist_tree_model.py`: Model for playlist tree display
- `playlist_item.py`: Base class for playlist items
- `track_item.py`: Base class for track items
- `tracks_table_model.py`: Model for tracks table display
- `track_details_panel.py`: Panel showing detailed track information
- `track_image_delegate.py`: Custom delegate for track images
- `track_quality_delegate.py`: Custom delegate for track quality indicators
- `platform_icon_delegate.py`: Custom delegate for platform icons
- `spotify/`: Spotify-specific playlist components
- `rekordbox/`: Rekordbox-specific playlist components
- `discogs/`: Discogs-specific playlist components
- `youtube/`: YouTube-specific playlist components
- `local/`: Local playlist components

## Dependencies

- Internal: core.platform for platform clients and sync
- External: PyQt6 for UI components

## Common Tasks

- **Adding support for a new platform**: Create a new subfolder with platform-specific implementations
- **Improving track display**: Modify tracks_table_model.py and relevant delegates
- **Adding playlist features**: Update playlist_component.py and playlist_data_provider.py
- **Adding track actions**: Update context menus in playlist component or track items

## Implementation Notes

- Uses Qt's Model/View architecture for efficient UI updates
- Platform-specific providers inherit from abstract base classes
- Delegates handle custom rendering of track elements
- UI components use the platform module for data operations

## Change History

- Initial implementation of playlist components
- Added track quality indicators
- Added platform filtering support
- Added track linking visualization
