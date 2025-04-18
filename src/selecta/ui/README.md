# UI Module Documentation

## Overview

The UI module contains all user interface components for Selecta. It's built using PyQt6 and follows a component-based architecture. The UI provides views for browsing, searching, playing, and managing music across multiple platforms.

## Key Components

- **SelectaMainWindow**: Main application window class that sets up the overall UI structure
- **Dialogs**: Specialized dialog windows for specific tasks (creating playlists, importing data)
- **Components**: Reusable UI components that make up the interface (see components/README.md)
- **Themes**: Theme management and styling for consistent appearance

## File Structure

- `app.py`: Main window implementation and application entry point
- `components/`: UI component modules (see components/README.md)
  - Core layout components (navigation, content areas)
  - Platform-specific components (Spotify, Rekordbox, etc.)
  - Playlist and track components
  - Player components
- `themes/`: Theme and styling management
  - `theme_manager.py`: Theme application and management
  - `style.py`: Style definitions and constants
- Dialog files:
  - `create_playlist_dialog.py`: Dialog for creating new playlists
  - `import_rekordbox_dialog.py`: Dialog for importing from Rekordbox
  - `import_covers_dialog.py`: Dialog for importing album artwork
  - `import_export_playlist_dialog.py`: Dialog for importing/exporting playlists
- `widgets/`: Base widget implementations and utilities

## UI Layout Structure

The main window is organized in the following layout:

```
┌───────────────────────────────────────────────────────┐
│                     NavigationBar                     │
├───────────────────────────────────┬───────────────────┤
│                                   │                   │
│                                   │                   │
│                                   │                   │
│      Playlist/Content Area        │   Side Panel      │
│        (Left Container)           │ (Right Container) │
│                                   │                   │
│                                   │                   │
│                                   │                   │
├───────────────────────────────────┴───────────────────┤
│                  Audio Player Component               │
│                    (Bottom Container)                 │
└───────────────────────────────────────────────────────┘
```

## Dependencies

- Internal: core.platform for platform integration, core.data for database access
- External: PyQt6 for UI framework, loguru for logging

## Common Tasks

- **Adding a new view**: Create a new component and update dynamic_content.py
- **Improving platform integration UI**: Update platform-specific components
- **Modifying layout**: Update app.py and the appropriate container components
- **Adding a new dialog**: Create a new dialog class following existing patterns
- **Theme changes**: Update themes/style.py and themes/theme_manager.py

## Implementation Notes

- The UI is built around a central QSplitter layout with adjustable panels
- Platform switching happens through a common interface in the navigation bar
- Dynamic content is loaded in the right panel based on context
- PyQt signals/slots are used for communication between components
- Authentication state is checked when switching platforms

## Change History

- Initial UI implementation with basic layout
- Added platform-specific components and views
- Added audio player implementation
- Added theme support and styling
- Added dialogs for playlist operations
- Added cover artwork support
