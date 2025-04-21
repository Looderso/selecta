# SESSION_RULES.md

This file contains session-specific rules and instructions for Claude Code to follow when working on the Selecta project.

## Current Session Focus

Refactor the playlist view and handling system to improve cross-platform functionality and track management, with special focus on establishing a robust platform synchronization framework.

## Refactoring Goals

1. **Rename "Local" Platform to "Library"**
   - Update all references from "Local" to "Library" to better reflect its role as the central unified database
   - Update UI labels, component names, and documentation

2. **Collection Playlist Improvements**
   - Add special handling for the Collection playlist (the master list containing all tracks)
   - Prevent Collection deletion and implement special context menu options
   - Allow bulk import to Collection through dedicated routines (not direct user modification)
   - Ensure all tracks in playlists are automatically in Collection

3. **Context Menu Refinement**
   - Make context menus platform-aware (different options depending on current platform)
   - Remove redundant options (e.g., don't show "Search on Spotify" when in Spotify view)
   - Ensure Library view has the complete set of options while others are limited
   - Implement proper platform-specific operations (import/export/sync)

4. **Platform Synchronization Visualization**
   - Add platform icons next to playlists to indicate sync status
   - Show which platforms each playlist is currently synced with
   - Update icons when sync status changes

5. **Track Duplicate Detection and Linking**
   - Implement detection of potential duplicate tracks across platforms
   - Create a dialog for presenting and confirming matches
   - Develop track merging functionality to combine platform-specific metadata
   - Add scheduled/on-demand process to scan for potential duplicates

6. **Platform-Specific Operation Logic**
   - Restrict metadata editing to Library view only
   - Define clear import/export/sync operations for each platform
   - Prevent invalid operations on specific platforms

7. **Discogs Integration Improvements**
   - Add visual indicators for tracks in Discogs wantlist/collection
   - Implement fuzzy matching for Discogs entries
   - Add functionality to check unlinked items in wantlist/collection

8. **Unified Platform Synchronization Architecture**
   - Clarify the conceptual separation between track linking and playlist synchronization
   - Refactor PlatformLinkManager to focus exclusively on track-level operations
   - Enhance PlatformSyncManager to handle all playlist-level operations
   - Ensure consistent implementation across all platforms (Spotify, Rekordbox, YouTube, Discogs)
   - Standardize platform data providers to use a consistent synchronization approach
   - Include all platforms (Spotify, Rekordbox, YouTube, Discogs) with consistent treatment
   - Ensure YouTube videos are properly handled as tracks in the linking and synchronization system

## Implementation Sequence

### Phase 1: Unified Synchronization Architecture ✅

- ✅ Refactor PlatformLinkManager to focus exclusively on track-level operations
- ✅ Enhance PlatformSyncManager to handle all playlist-level operations
- ✅ Create clear conceptual separation between track linking and playlist synchronization
- ✅ Standardize platform data providers to use consistent synchronization (done for Spotify, Rekordbox, YouTube, Discogs)
- ✅ Database schema changes implemented with PlaylistPlatformInfo model, database rebuilt
- ✅ Ensure all platforms (Spotify, Rekordbox, YouTube, Discogs) are treated consistently
- ✅ Added YouTube support in PlatformLinkManager for treating videos as tracks

### Phase 2: Foundation Changes

- ✅ Rename "Local" to "Library" across the codebase
- ✅ Update PlaylistComponent to handle the Collection playlist specially
- ✅ Modify LocalPlaylistDataProvider to be renamed as LibraryPlaylistDataProvider
- ✅ Ensure Collection is loaded by default and cannot be deleted

### Phase 3: UI Improvements

- ✅ Update context menu generation to be platform-aware
- ✅ Implement platform-aware sync options in context menus
- ✅ Add platform synchronization icons to playlist items
- ✅ Implement playlist sync status tracking
- ✅ Update UI components to reflect platform synchronization status
- ✅ Ensure consistent visualization of platform connections (Spotify, Rekordbox, YouTube, Discogs)

### Phase 4: Enhanced Synchronization ✅

- ✅ Design and implement the improved synchronization preview dialog
- ✅ Show detailed changes (additions/removals) before syncing
- ✅ Allow users to selectively apply changes
- ✅ Implement track-level change detection between platforms and library
- ✅ Create snapshot mechanism to track playlist state between syncs
- ✅ Add handling for personal vs. shared/public playlists

### Phase 5: Track Linking System

- ✅ Fix album handling in PlatformLinkManager to properly create Album objects
- Design and implement the track duplicate detection algorithm
- Create a MatchConfirmationDialog for user review of potential matches
- Implement track merging functionality
- Add UI elements to trigger duplicate detection
- Ensure linking works correctly between all platforms including YouTube videos

### Phase 6: Collection Playlist Enhancement

- ✅ Ensure all tracks imported from platforms are added to the Collection
- ✅ Fix Collection icon display in playlist view
- ✅ Add Collection track handling during sync operations
- ✅ Ensure only Collection has a left icon for better visual alignment
- Implement "Add Selected Tracks to Collection" context menu option
- Add Collection statistics and auto-scanning for local tracks

### Phase 7: Platform-Specific Logic

- Update operations for platform-specific playlist handling
- Ensure proper metadata editing restrictions
- Implement improved sync/import/export operations
- Add error handling for platform-specific operations
- Include YouTube-specific operations for video playlists
- Handle shared/public playlists differently from personal playlists

### Phase 8: Discogs Integration

- Add wantlist/collection indicators for tracks
- Implement Discogs-specific matching functionality
- Create visual indicators for Discogs status
- Add process to check for unlinked Discogs items

## Code Style Rules

- Follow Python typing guidelines as defined in the Typing Guidelines document
- Maintain consistent error handling patterns
- Use SQLAlchemy 2.0 style for database operations
- Keep UI components modular and reusable
- Ensure proper documentation of all new components and functions
- Follow existing naming conventions

## Implementation Strategy

For each phase:

1. First identify all affected files by examining relevant documentation
2. Create a clear plan for changes needed in specific files
3. Make changes in a consistent order: models → repositories → business logic → UI
4. Test each component individually before integrating
5. Update documentation to reflect changes

## File Areas To Focus On

- `src/selecta/core/platform/link_manager.py`: Track linking operations
- `src/selecta/core/platform/sync_manager.py`: Playlist synchronization logic
- `src/selecta/core/platform/youtube/client.py`: YouTube platform client
- `src/selecta/core/platform/youtube/sync.py`: YouTube synchronization functionality
- `src/selecta/ui/components/playlist/`: Playlist view components
- `src/selecta/core/data/models/db.py`: Database model definitions
- `src/selecta/core/data/repositories/`: Data access repositories
- `src/selecta/ui/components/playlist/playlist_component.py`: Main playlist UI
- `src/selecta/ui/components/playlist/*/playlist_data_provider.py`: Platform-specific data providers

## Platform Synchronization Architecture

### Conceptual Model

1. **Track Linking (PlatformLinkManager)**
   - Focus: Creating connections between individual tracks across platforms
   - Operations: Import tracks, extract and store platform-specific metadata
   - Data: TrackPlatformInfo model, Album model
   - Principle: All platform "tracks" (Spotify tracks, Rekordbox tracks, YouTube videos, Discogs releases)
     are treated as equivalent entities that can be linked to a library track
   - Album Handling: When importing tracks, create proper Album objects and establish relationships between tracks and albums

2. **Playlist Synchronization (PlatformSyncManager)**
   - Focus: Managing playlists across platforms
   - Operations: Import/export/sync playlists, handle platform-specific playlist operations
   - Uses: PlatformLinkManager for track-level operations
   - Data: Playlist model with platform source and ID
   - Sync Process:
     - Show the user a preview of changes (additions/removals) before applying
     - Only sync tracks that have the appropriate platform metadata
     - Treat personal playlists differently from shared/public playlists
     - For personal playlists: Full bidirectional sync (additions and removals)
     - For shared/public playlists: Import-only, no sync

3. **UI Integration (PlaylistDataProvider)**
   - Focus: Consistent platform operations in the UI
   - Operations: Handle import/export/sync UI interactions
   - Uses: PlatformSyncManager for all synchronization operations

### Implementation Guide

1. **PlatformLinkManager**
   - Should handle ONLY track-level operations
   - Primary methods: import_track, link_tracks, _get_or_create_album
   - Responsible for TrackPlatformInfo management and Album object creation
   - Ensures proper database relationships between Track and Album objects

2. **PlatformSyncManager**
   - Should handle ALL playlist-level operations
   - Primary methods: import_playlist, export_playlist, sync_playlist
   - Uses PlatformLinkManager for track operations
   - Manages Playlist synchronization status

3. **Platform Integration**
   - All platforms must be treated equally (Spotify, Rekordbox, YouTube, Discogs)
   - YouTube videos are treated as tracks, with the same linking and synchronization approach
   - Rekordbox integration must be fully supported for DJ library management
   - Platform data providers should use a consistent approach across all platforms

### Database Notes

- If schema changes are needed, rebuild the database rather than migrating
- This can be done manually by the developer with:
  ```bash
  selecta database init --force
  ```
