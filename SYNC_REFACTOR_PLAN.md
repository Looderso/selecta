# Playlist Synchronization Refactoring Plan

This document outlines the detailed plan for enhancing the playlist synchronization functionality in Selecta to provide a more intuitive and comprehensive bidirectional sync experience.

## Status: IMPLEMENTED ✅

The enhanced synchronization functionality has been fully implemented as described in this document. The implementation includes:

1. Data model for tracking sync state
2. Comprehensive change detection system
3. Preview dialog for user review of changes
4. Selective application of changes
5. Personal vs. shared playlist handling
6. Bidirectional sync with additions and removals

## Goals

1. Implement true bidirectional synchronization between the library and external platforms ✅
2. Show users a preview of sync changes before applying them ✅
3. Allow selective application of changes ✅
4. Handle additions and removals properly in both directions ✅
5. Distinguish between personal playlists and shared/public playlists ✅
6. Maintain a sync state snapshot for change detection ✅

## Synchronization Design

### Core Concepts

**Change Detection**
- Compare current state of library and platform playlists against last sync state
- Detect added and removed tracks on both sides
- Only process tracks with appropriate platform metadata

**Change Categories**
- Platform Additions: Tracks added to platform since last sync
- Platform Removals: Tracks removed from platform since last sync
- Library Additions: Tracks added to library since last sync
- Library Removals: Tracks removed from library since last sync

**Sync Preview Dialog**
- Show all detected changes organized by category
- Allow selecting/deselecting individual changes
- Display clear previews of what will happen
- Provide warnings about data loss for removals

**Playlist Type Handling**
- Personal playlists: Full bidirectional sync (additions and removals)
- Shared/public playlists: Import-only operations, no sync

## Architecture Design

### Data Model

```python
# Model for tracking playlist sync state
class PlaylistSyncState:
    # Library playlist details
    playlist_id: int

    # Platform details
    platform: str                # "spotify", "youtube", etc.
    platform_playlist_id: str
    is_personal_playlist: bool   # Whether this is a personal playlist

    # Sync metadata
    last_synced: datetime
    track_snapshot: dict         # Tracks that were present at last sync
```

**Track Snapshot Structure**:
```python
{
    "library_tracks": {
        track_id: {"platform_id": platform_id, "added_at": timestamp},
        ...
    },
    "platform_tracks": {
        platform_id: {"library_id": track_id, "added_at": timestamp},
        ...
    }
}
```

### PlatformSyncManager Enhancements

#### New Methods

```python
def get_sync_changes(self, local_playlist_id: int) -> SyncChanges:
    """
    Analyze changes between library and platform playlist since last sync.
    Returns detailed information about all additions and removals on both sides.

    Args:
        local_playlist_id: Library playlist ID

    Returns:
        SyncChanges object with all detected changes
    """
    # Implementation steps:
    # 1. Get the library playlist and its linked platform playlist
    # 2. Get the previous sync snapshot
    # 3. Compare current library tracks with snapshot
    # 4. Compare current platform tracks with snapshot
    # 5. Categorize all changes
    # 6. Return comprehensive change set
    pass

def preview_sync(self, local_playlist_id: int) -> SyncPreview:
    """
    Generate a preview of sync changes for display to the user.

    Args:
        local_playlist_id: Library playlist ID

    Returns:
        SyncPreview object with human-readable changes
    """
    # Implementation steps:
    # 1. Get sync changes using get_sync_changes
    # 2. Convert raw changes to human-readable format with track details
    # 3. Organize by change category
    # 4. Return formatted preview
    pass

def apply_sync_changes(
    self,
    local_playlist_id: int,
    selected_changes: dict,
) -> SyncResult:
    """
    Apply selected sync changes based on user input.

    Args:
        local_playlist_id: Library playlist ID
        selected_changes: Dictionary of change IDs that user selected to apply

    Returns:
        SyncResult with details of applied changes
    """
    # Implementation steps:
    # 1. Get all possible changes
    # 2. Filter to only those selected by user
    # 3. Apply each change:
    #    - Add platform tracks to library
    #    - Add library tracks to platform
    #    - Remove platform tracks
    #    - Remove library tracks
    # 4. Create new sync snapshot
    # 5. Return results summary
    pass

def save_sync_snapshot(self, local_playlist_id: int) -> None:
    """
    Save current state of both playlists for future change detection.

    Args:
        local_playlist_id: Library playlist ID
    """
    # Implementation steps:
    # 1. Get current library playlist tracks
    # 2. Get current platform playlist tracks
    # 3. Create snapshot data structure
    # 4. Save to database
    pass
```

#### Enhanced Sync Method

```python
def sync_playlist(
    self,
    local_playlist_id: int,
    apply_all_changes: bool = False
) -> Union[SyncPreview, SyncResult]:
    """
    Sync a playlist between library and platform.

    Args:
        local_playlist_id: Library playlist ID
        apply_all_changes: If True, apply all changes without preview
                          If False, return preview only

    Returns:
        If apply_all_changes is True: SyncResult with applied changes
        If apply_all_changes is False: SyncPreview with potential changes
    """
    # Implementation steps:
    # 1. If apply_all_changes is False, return preview_sync()
    # 2. If apply_all_changes is True:
    #    - Get all possible changes
    #    - Apply all changes
    #    - Save new snapshot
    #    - Return results
    pass
```

### UI Components

#### SyncPreviewDialog

A modal dialog showing:

1. Summary section
   - Counts of each change type
   - Clear indicators of what will happen

2. Change details sections
   - Platform Additions section
     - List of tracks added on platform
     - Checkboxes to select which to import

   - Platform Removals section
     - List of tracks removed on platform
     - Checkboxes to select which to remove from library

   - Library Additions section
     - List of tracks added to library
     - Checkboxes to select which to export

   - Library Removals section
     - List of tracks removed from library
     - Checkboxes to select which to remove from platform

3. Action buttons
   - Apply Selected Changes
   - Cancel
   - Select All / Deselect All options

#### Change Display Components

- TrackChangeListItem: Component showing track details with selection checkbox
- ChangeCategory: Component showing a category of changes with expand/collapse
- SyncProgressIndicator: Progress visualization during sync operation

## Implementation Plan

### Phase 1: Data Model and Infrastructure

1. Create PlaylistSyncState model and database table
2. Implement methods to save and retrieve sync snapshots
3. Add platform playlist ownership detection (personal vs. shared)

### Phase 2: Change Detection System

1. Implement core change detection logic
2. Create SyncChanges and SyncPreview data structures
3. Build test cases for various change scenarios

### Phase 3: Core Sync Logic

1. Enhance PlatformSyncManager with new methods
2. Implement platform-specific track matching logic
3. Build selective change application system

### Phase 4: UI Implementation

1. Design and build SyncPreviewDialog
2. Create supporting UI components
3. Integrate with context menu actions

### Phase 5: Platform-Specific Adaptations

1. Implement Spotify-specific sync handler
2. Implement YouTube-specific sync handler
3. Implement Rekordbox-specific sync handler
4. Implement Discogs-specific sync handler (collection/wantlist)

## Platform-Specific Considerations

### Spotify

- Check if playlist is owned by user or collaborative
- Handle Spotify's rate limits for large playlists
- Use batch operations where possible

### YouTube

- Check if playlist is owned by user
- Handle video availability issues
- Consider YouTube's API limitations

### Rekordbox

- Special handling for database access when Rekordbox is running
- Proper path management for local files
- Translation between Rekordbox IDs and file paths

### Discogs

- Special handling as not a true playlist system
- Custom UI for collection/wantlist sync
- Different handling than standard playlists

## Testing Strategy

1. Unit tests for change detection logic
2. Integration tests for sync operations
3. UI tests for sync dialog
4. Manual testing scenarios for each platform

## Migration Path

1. Update database schema to add sync state tracking
2. Implement the core sync logic without UI changes first
3. Add the preview dialog while maintaining backward compatibility
4. Roll out platform-specific adaptations one by one

## User Experience Flow

1. User initiates sync from context menu
2. System analyzes changes and shows preview dialog
3. User selects which changes to apply
4. System applies selected changes with progress indicator
5. System shows success/error summary
6. System updates UI to reflect new state

## Future Enhancements

- Conflict resolution for metadata differences
- Automated background sync
- Scheduled sync operations
- Diff visualization for track metadata
- Multi-playlist sync operations
