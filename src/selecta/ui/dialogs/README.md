# UI Dialogs Documentation

## Overview

The dialogs in Selecta are modal windows that handle specific user interactions such as creating playlists, importing data, and configuring settings. Each dialog provides a focused interface for completing a specific task.

## Current Dialog Files

Note: These files are currently at the ui/ root level but could be organized into a dedicated dialogs/ folder in the future.

- `create_playlist_dialog.py`: Dialog for creating new playlists or folders
- `import_rekordbox_dialog.py`: Dialog for importing playlists and tracks from Rekordbox
- `import_covers_dialog.py`: Dialog for importing album artwork from audio file metadata
- `import_export_playlist_dialog.py`: Dialog for importing/exporting playlists between platforms

## Dialog Architecture

Each dialog follows a consistent pattern:

1. Inherits from QDialog
2. Contains a _setup_ui method for UI initialization
3. Provides methods to retrieve user input (get_values, etc.)
4. Uses standard dialog buttons (OK/Cancel)
5. Returns results through the standard QDialog accept/reject mechanism

## Common Dialog Components

- Form layouts for structured data entry
- Progress indicators for long-running operations
- Confirmation buttons with standard placement
- Clear error messaging and validation

## Dependencies

- Internal: May use components from the core UI modules
- External: PyQt6 for dialog implementation

## Common Tasks

- **Adding a new dialog**: Create a new class inheriting from QDialog
- **Modifying an existing dialog**: Update the _setup_ui method and related functionality
- **Handling dialog results**: Use the exec() method and check for QDialog.Accepted

## Implementation Notes

- Dialogs should be modal (blocking) when they require immediate user attention
- Use clear, concise labels and provide helpful descriptions
- Validate user input before accepting the dialog
- For long-running operations, show progress and allow cancellation
- Follow Qt's dialog design patterns for consistency

## Future Improvements

- Organize dialogs into a dedicated subdirectory
- Create base dialog classes for common patterns
- Add more sophisticated validation
- Improve theming and visual consistency
