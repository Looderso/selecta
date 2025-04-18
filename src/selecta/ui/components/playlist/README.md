# Playlist UI Components Documentation

## Overview

The playlist module provides UI components for displaying, managing, and interacting with playlists and tracks from various platforms. It handles the presentation layer for playlist data from all platforms in a consistent way.

## Key Components

- **PlaylistComponent**: Main playlist UI component combining tree view and track list
- **PlaylistDataProvider**: Interface for platform-specific playlist data access
- **PlaylistTreeModel**: Qt model for playlist tree structure
- **TracksTableModel**: Qt model for track list display
- **TrackDetailsPanel**: Panel for viewing and editing track metadata
- **Platform-specific implementations**: Specialized components for each music platform

## File Structure

- `abstract_playlist_data_provider.py`: Base class for all playlist data providers
- `playlist_component.py`: Main playlist UI component
- `playlist_data_provider.py`: Interface for playlist data access
- `playlist_tree_model.py`: Model for playlist tree display
- `playlist_item.py`: Base class for playlist items
- `track_item.py`: Base class for track items
- `tracks_table_model.py`: Model for tracks table display
- `track_details_panel.py`: Panel showing detailed track information with editing capabilities
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
- **Extending metadata editing**: Update track_details_panel.py with new metadata fields

## Implementation Notes

- Uses Qt's Model/View architecture for efficient UI updates
- Platform-specific providers inherit from abstract base classes
- Delegates handle custom rendering of track elements
- UI components use the platform module for data operations
- Track details panel supports metadata editing with platform data integration

## Track Details Panel

The TrackDetailsPanel provides a comprehensive interface for viewing and editing track metadata:

- **Metadata Fields**: Display and edit track metadata (title, artist, album, year, BPM)
- **Platform Integration**: Pull metadata from different connected platforms
- **Visual Platform Indicators**: Icons show which platforms have alternative metadata values
- **Edit Workflow**: Apply/Cancel buttons provide a clear editing workflow
- **Quality Rating**: Rate tracks on a 1-5 star scale for personal collection management
- **Cover Image Management**: Update track covers using images from platforms

### Metadata Editing

The panel includes several key features for metadata management:

1. **Update From Platforms**: Button that analyzes connected platform data and suggests alternative values
2. **Platform Suggestions**: Platform icons appear next to fields with alternative values from connected platforms
3. **Visual Selection**: Click platform icons to adopt values from specific platforms
4. **Reset Capability**: Each field can be reset to its original value
5. **Unified Apply/Cancel**: Changes are only persisted when explicitly applied

### Cover Image Management

The panel also provides functionality for managing track cover images:

1. **Platform Cover Selection**: Choose from available cover images across platforms
2. **Visual Selection Dialog**: View and select cover images from a dedicated dialog
3. **Cover Preview**: Preview selected images before applying them
4. **Multiple Platform Support**: Get cover images from Spotify, Discogs, and other connected platforms

## Change History

- Added cover image selection and management from platforms to TrackDetailsPanel
- Added CoverSelectionDialog for choosing cover images from different platforms
- Refactored TrackDetailsPanel with metadata editing capabilities and platform integration
- Added platform-specific metadata suggestion system with interactive UI
- Added track quality indicators
- Added platform filtering support
- Added track linking visualization
- Initial implementation of playlist components
