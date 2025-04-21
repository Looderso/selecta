Current Sync Strategy Analysis

  The current implementation has a bidirectional sync approach that aims to handle these cases through the
  PlatformSyncManager.sync_playlist() method, which does the following:

  1. Imports any new tracks from the platform playlist to the library playlist
  2. Exports any tracks from the library playlist that aren't on the platform yet

  However, there are important edge cases to consider:

  Scenario 1: Adding tracks outside the app

  If you add tracks to a Spotify/YouTube playlist while outside the app, the current sync strategy should properly
  handle this when you press "Sync" in the context menu. The implementation retrieves the latest playlist contents
  from the platform API and adds any new tracks to the library playlist.

  Scenario 2: Removing tracks from the library

  The current implementation doesn't explicitly handle removals. If you remove a track from a library playlist,
  pressing "Sync" won't automatically remove it from the platform playlist. This is a significant gap in the
  bidirectional sync model.

  Scenario 3: Removing tracks on the platform

  Similarly, if you remove tracks from a playlist on Spotify/YouTube outside the app, the current sync wouldn't remove
   those tracks from your library playlist.

  Improved Sync Strategy Recommendation

  A more comprehensive sync strategy should handle all these cases with a true bidirectional approach:

  1. Track Additions:
    - Platform → Library: Add new tracks found on the platform to the library playlist
    - Library → Platform: Add new tracks found in the library to the platform playlist
  2. Track Removals:
    - Platform → Library: Remove tracks from the library playlist that were removed on the platform
    - Library → Platform: Remove tracks from the platform playlist that were removed from the library
  3. User Control:
    - Provide options for how sync should handle removals vs. additions
    - Allow users to choose sync behavior with options like:
        - "Full sync" (bidirectional additions and removals)
      - "Add only" (only add new tracks, never remove)
      - "From platform" (make library match platform exactly)
      - "To platform" (make platform match library exactly)

  Implementation Considerations

  For a proper implementation, we would need to:

  1. Update the PlatformSyncManager.sync_playlist() method to compare the current state of both playlists and
  determine what tracks were added or removed on either side.
  2. Add a sync dialog that allows users to choose the sync behavior before performing the operation, showing:
    - Tracks that will be added to the library
    - Tracks that will be added to the platform
    - Tracks that will be removed from the library
    - Tracks that will be removed from the platform
    - Options to control which of these actions to perform
  3. Store sync preferences per playlist, so users can set different behaviors for different playlists (e.g., a
  collaborative playlist might use "add only" sync to avoid removing others' additions).

  Platform-Specific Challenges

  Different platforms have different limitations:

  1. Spotify: Full API support for bidirectional sync, but rate limits could be an issue for large playlists.
  2. YouTube: Similar to Spotify, but with some API restrictions that might affect large-scale operations.
  3. Rekordbox: More complex since we're working with a local database, but we can still implement proper
  bidirectional sync.
  4. Discogs: Special case since it's not a traditional playlist system - needs custom handling for
  collection/wantlist.

  Summary

  The current implementation provides basic bidirectional sync for additions but doesn't properly handle removals. A
  comprehensive sync strategy would address both additions and removals in both directions, with user control over the
   specific sync behavior. This would deliver the seamless experience users expect when managing their music across
  multiple platforms.

  Would you like me to suggest a more detailed design for this improved sync strategy, or would you prefer to focus on
   implementing other aspects of the project first?

> suggest a design please and dont start implementing it.

⏺ Comprehensive Playlist Synchronization Strategy Design

  Overview

  The improved synchronization strategy aims to provide a true bidirectional synchronization between the library and
  external platforms, with user-configurable options to control the behavior of additions and removals.

  Core Concepts

  1. Sync Modes

  Four distinct sync modes to give users control over synchronization behavior:

  Full Sync (Default)

- Additions: Add new tracks in both directions
- Removals: Remove tracks that were deleted in either location
- Result: Library and platform playlists will be identical after sync

  Add Only Mode

- Additions: Add new tracks in both directions
- Removals: Ignore removals (tracks removed from one side remain on the other)
- Result: Playlists grow but never shrink during sync

  Mirror Platform Mode

- Behavior: Make library playlist exactly match the platform playlist
- Additions: Add platform tracks to library
- Removals: Remove library tracks not present on platform
- Result: Library playlist becomes a mirror of platform playlist

  Push to Platform Mode

- Behavior: Make platform playlist exactly match the library playlist
- Additions: Add library tracks to platform
- Removals: Remove platform tracks not present in library
- Result: Platform playlist becomes a mirror of library playlist

  2. Track Change Detection

  To properly identify changes, we need to track the last sync state:

  Sync State Tracking

- Store a snapshot of both playlists after each successful sync
- Compare current state against last sync state to detect:
  - Newly added tracks on both sides
  - Removed tracks on both sides
  - Tracks that remain unchanged

  Change Categories

- Platform Additions: Tracks added to platform since last sync
- Platform Removals: Tracks removed from platform since last sync
- Library Additions: Tracks added to library since last sync
- Library Removals: Tracks removed from library since last sync

  3. User Interface Components

  Sync Dialog

- Summary section showing counts of changes to be made
- Detailed view with expandable sections for each change category
- Options to select sync mode for this operation
- Option to save chosen sync mode as default for this playlist
- Preview of what the playlist will look like after sync
- Clear warnings about data that will be removed

  Sync Settings Panel

- Global default sync mode setting
- Per-playlist sync preferences
- Schedule options for automatic background sync
- Conflict resolution preferences

  Architectural Design

  1. Data Model Enhancements

# New model for tracking playlist sync state

  class PlaylistSyncState:
      playlist_id: int                 # Library playlist ID
      platform: str                    # Platform name (spotify, youtube, etc.)
      platform_playlist_id: str        # ID on the platform
      last_synced: datetime            # When last synced
      track_snapshot: dict             # Snapshot of tracks at last sync
      sync_mode: str                   # Chosen sync mode for this playlist
      auto_sync: bool                  # Whether to auto-sync this playlist

# Track snapshot structure

  TrackSnapshot = {
      "library_tracks": [track_ids],   # IDs of tracks in library
      "platform_tracks": [track_ids]   # IDs of tracks on platform
  }

  2. PlatformSyncManager Enhancements

  class PlatformSyncManager:
      # Existing methods...

      def analyze_sync_changes(self, playlist_id: int) -> SyncChanges:
          """
          Analyze changes between library and platform playlist since last sync.
          Returns details of all additions and removals on both sides.
          """
          pass

      def sync_playlist(
          self,
          local_playlist_id: int,
          sync_mode: str = "full",
          handle_additions: bool = True,
          handle_removals: bool = True
      ) -> SyncResult:
          """
          Sync playlist with configurable behavior.

          Args:
              local_playlist_id: Library playlist ID
              sync_mode: One of "full", "add_only", "mirror_platform", "push_to_platform"
              handle_additions: Whether to process additions (override from sync_mode)
              handle_removals: Whether to process removals (override from sync_mode)

          Returns:
              SyncResult with details of changes made
          """
          pass

      def save_sync_snapshot(self, playlist_id: int) -> None:
          """
          Save current state of both playlists as a snapshot for future change detection.
          """
          pass

  3. Sync Dialog Flow

  1. User initiates sync from context menu
  2. System analyzes changes using analyze_sync_changes
  3. Sync dialog displays changes organized by category
  4. User selects sync mode and options
  5. System executes sync with chosen parameters
  6. System saves new sync snapshot
  7. System displays results summary

  Implementation Considerations

  1. Performance Optimization

  For large playlists, we should implement:

- Pagination for retrieving platform playlists
- Batched API calls for updating platforms
- Progress indicators for long-running operations
- Background processing for heavy sync operations

  2. Conflict Resolution

  When tracks have been modified on both sides, we need strategies for:

- Metadata conflicts (different titles, artists, etc.)
- Order conflicts (different track positioning)
- Special track handling (e.g., tracks unavailable on certain platforms)

  3. Error Handling

  Robust error handling for:

- Network failures during sync
- API rate limiting
- Partial sync completion
- Permission changes on platforms
- Unavailable tracks/resources

  4. Platform-Specific Adaptations

  Spotify

- Handle collaborative playlists specially (prefer add-only mode)
- Account for Spotify's specific limits on additions/removals

  YouTube

- Consider video availability issues
- Handle privacy settings appropriately

  Rekordbox

- Special handling for local file paths
- Consider running vs. non-running Rekordbox states

  Discogs

- Special handling for collection/wantlist synchronization
- Matching strategy for releases vs. tracks

  User Experience Flow

  1. Initial Sync Setup
    - When a user first imports a playlist, offer sync mode selection
    - Provide explanations of different sync behaviors
    - Set default preferences based on playlist type (collaborative, personal, etc.)
  2. Regular Sync
    - Quick sync option using saved preferences
    - Advanced sync option showing the detailed dialog
    - Visual indicators of sync status (up-to-date, needs sync, etc.)
  3. Automatic Sync
    - Background sync on app startup (optional)
    - Scheduled sync intervals (optional)
    - Notification of significant changes detected

  Migration Path

  1. Enhance database schema to store sync states
  2. Update UI to include sync mode options
  3. Implement change detection logic
  4. Create the detailed sync dialog
  5. Update platform-specific implementations
  6. Add playlist-level sync preferences
  7. Implement global sync settings

  This design provides a comprehensive approach to playlist synchronization that addresses the real-world usage
  patterns you described, giving users full control over how their playlists are synchronized while maintaining a
  consistent user experience.
