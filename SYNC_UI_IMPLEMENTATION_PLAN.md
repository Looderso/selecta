# Sync UI Implementation Plan

## Overview
This document outlines the implementation plan for making cross-platform sync more intuitive in Selecta, focusing on user-controlled operations and efficient API usage.

## Core Design Principles
1. **User-controlled sync status updates** - Only refresh when user requests it (no automatic polling)
2. **Clear sync preview** - Show exactly what will change before any sync operation
3. **Efficient API usage** - Batch operations and avoid unnecessary requests
4. **Keep existing successful patterns** - Maintain import/export in context menus
5. **Progressive enhancement** - Build on existing components without breaking workflows

## Implementation Components

### 1. Sync Center Component

**Location**: `src/selecta/ui/components/sync/sync_center.py`

**Purpose**: Central dashboard for managing all synchronized playlists across platforms

**Features**:
- **Platform Tabs**: Similar to current navbar (Spotify, Rekordbox, YouTube, Local Library)
- **Synced Playlist Overview**: List of all playlists that have cross-platform links
- **Manual Refresh**: Button to update sync status (triggers API calls only when needed)
- **Bulk Operations**: Select multiple playlists for batch sync operations
- **Sync Queue**: Show ongoing sync operations with progress

**UI Layout**:
```
┌─ Sync Center ────────────────────────────────────────────┐
│ 📊 Overview                    [🔄 Refresh Status]       │
│ • 15 synced playlists • Last check: 2 hours ago          │
│                                                          │
│ 📱 Platform Tabs: [Spotify] [Rekordbox] [YouTube] [All] │
│                                                          │
│ 📋 Synced Playlists                     [☑️ Select All] │
│ ┌────────────────────────────────────────────────────┐   │
│ │ ☑️ 🎵 My Favorites     Spotify ↔ Rekordbox        │   │
│ │    Last sync: 1 hour ago • 25 tracks • ✅ In sync │   │
│ │                                                    │   │
│ │ ☑️ 💿 DJ Mix 2024      Rekordbox → YouTube         │   │
│ │    Last sync: 3 days ago • 18 tracks • ⚠️ Outdated│   │
│ │                                                    │   │
│ │ ☐ 📺 Workout Videos    YouTube → Spotify           │   │
│ │    Last sync: 1 week ago • 12 tracks • ❌ Failed  │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ 🔄 Bulk Actions: [Sync Selected] [Preview Changes]      │
└──────────────────────────────────────────────────────────┘
```

**Data Structure**:
```python
@dataclass
class SyncedPlaylistInfo:
    local_playlist_id: int
    platform_playlist_id: str
    platform_name: str
    sync_direction: str  # "bidirectional", "import_only", "export_only"
    last_sync_time: datetime | None
    sync_status: str  # "in_sync", "outdated", "failed", "unknown"
    track_count_local: int
    track_count_platform: int
    sync_conflicts: list[str]  # List of conflict descriptions
```

### 2. Enhanced Context Menus

**Location**: Update existing `BasePlatformDataProvider.show_playlist_context_menu()`

**Current Structure**:
```
Right-click playlist →
├── Import to Library
├── Sync with Library
├── Refresh
```

**New Structure**:
```
Right-click playlist →
├── 📥 Import to Library
├── 📤 Export to Platform...
│   ├── Export to Spotify
│   ├── Export to Rekordbox
│   └── Export to YouTube
├── 🔄 Sync with Library
├── 🔍 Search...
│   ├── Search on Spotify
│   ├── Search on Discogs
│   └── Search on YouTube
├── ⚙️ Sync Settings...
└── 🔄 Refresh
```

**Implementation**:
- Create `SyncContextMenu` component
- Use QMenu with nested submenus for platforms
- Add icons for visual hierarchy
- Maintain existing functionality while adding new options

### 3. Sync Preview Dialog

**Location**: `src/selecta/ui/dialogs/sync_preview_dialog.py`

**Purpose**: Show detailed preview of what will change during sync operation

**Features**:
- **Side-by-side comparison** of local vs platform playlist
- **Track-by-track diff** showing additions, removals, conflicts
- **Selective sync options** - checkboxes to include/exclude specific changes
- **Conflict resolution** - choose which version to keep for conflicting tracks
- **Preview mode** - no changes until user confirms

**UI Layout**:
```
┌─ Sync Preview: "My Favorites" (Spotify ↔ Rekordbox) ────┐
│                                                         │
│ 📊 Summary                                              │
│ • Will add 3 tracks to Rekordbox                       │
│ • Will remove 1 track from Spotify                     │
│ • 2 conflicts need resolution                          │
│                                                         │
│ 📋 Changes                          [☑️ Select All]     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✅ ADD TO REKORDBOX (3 tracks)                      │ │
│ │ ☑️ Song A - Artist 1                              │ │
│ │ ☑️ Song B - Artist 2                              │ │
│ │ ☑️ Song C - Artist 3                              │ │
│ │                                                   │ │
│ │ ❌ REMOVE FROM SPOTIFY (1 track)                   │ │
│ │ ☑️ Old Song - Old Artist                          │ │
│ │                                                   │ │
│ │ ⚠️ CONFLICTS (2 tracks)                           │ │
│ │ ☑️ Song D - Different metadata                    │ │
│ │    Spotify: "Song D" by "Artist X"               │ │
│ │    Rekordbox: "Song D (Remix)" by "Artist X"     │ │
│ │    Keep: [● Spotify] [○ Rekordbox] [○ Skip]      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [📋 Export Report] [❌ Cancel] [⚡ Apply Changes]       │
└─────────────────────────────────────────────────────────┘
```

**Data Structure**:
```python
@dataclass
class SyncChange:
    action: str  # "add", "remove", "conflict", "update"
    track_info: TrackInfo
    source_platform: str
    target_platform: str
    conflict_details: dict | None = None
    user_selected: bool = True

@dataclass
class SyncPreview:
    playlist_name: str
    source_platform: str
    target_platform: str
    changes: list[SyncChange]
    total_additions: int
    total_removals: int
    total_conflicts: int
```

### 4. Sync Center Integration

**Navigation Integration**:
- Add "Sync" tab to dynamic content navigation bar (alongside "Details" and "Search")
- Route to `SyncCenter` component when selected
- Show sync center when no specific playlist is selected but sync tab is active

**Dynamic Content Updates**:
```python
# In dynamic_content.py
def _update_content_for_sync_tab(self):
    """Show sync center in dynamic content area."""
    if self.sync_center is None:
        self.sync_center = SyncCenter(parent=self)

    # Clear other content
    self._clear_content()

    # Show sync center
    self.layout().addWidget(self.sync_center)
    self.sync_center.refresh_sync_status()  # Only when explicitly shown
```

### 5. Data Management and API Efficiency

**Sync Status Caching**:
```python
@dataclass
class SyncStatusCache:
    playlist_info: dict[str, SyncedPlaylistInfo]
    last_refresh: datetime
    cache_ttl: timedelta = timedelta(hours=1)

    def is_expired(self) -> bool:
        return datetime.now() - self.last_refresh > self.cache_ttl

    def refresh_if_needed(self, force: bool = False) -> bool:
        if force or self.is_expired():
            # Trigger API calls to refresh status
            return True
        return False
```

**Efficient API Usage**:
- **Batch playlist info requests** when refreshing status
- **Cache sync status** to avoid repeated API calls
- **Only refresh on user action** (refresh button, sync center open)
- **Progressive loading** - load platform by platform
- **Cancellable operations** - allow user to stop long-running operations

### 6. Implementation Phases

#### Phase 1: Core Sync Center (Week 1-2)
1. Create `SyncCenter` component with basic layout
2. Implement platform tabs and playlist listing
3. Add manual refresh functionality
4. Integrate with existing dynamic content system

#### Phase 2: Enhanced Context Menus (Week 2-3)
1. Restructure context menus with nested platform options
2. Update all platform data providers
3. Add search submenu organization
4. Test across all platforms

#### Phase 3: Sync Preview Dialog (Week 3-4)
1. Create comprehensive preview dialog
2. Implement track comparison logic
3. Add conflict resolution interface
4. Connect to existing sync operations

#### Phase 4: Status Management (Week 4-5)
1. Implement sync status caching
2. Add batch operations for selected playlists
3. Create progress tracking for bulk operations
4. Add sync queue management

#### Phase 5: Polish and Integration (Week 5-6)
1. Add comprehensive error handling
2. Implement progress notifications
3. Add sync history tracking
4. Performance optimization and testing

## Technical Implementation Notes

### Component Hierarchy
```
SyncCenter
├── SyncOverviewWidget (stats, refresh button)
├── PlatformTabWidget (tab selection)
├── SyncedPlaylistListWidget (main list)
├── BulkActionsWidget (selection actions)
└── SyncProgressWidget (active operations)
```

### Data Flow
1. **User opens Sync Center** → Load cached sync status
2. **User clicks refresh** → Trigger API calls per platform
3. **User selects playlists** → Enable bulk actions
4. **User clicks sync** → Open preview dialog
5. **User confirms changes** → Execute sync operations
6. **Sync completes** → Update cache and UI

### Integration Points
- **Platform Data Providers**: Add sync status methods
- **Sync Manager**: Enhance with preview and batch operations
- **Dynamic Content**: Add sync tab routing
- **Context Menus**: Restructure with nested options
- **Playlist Repository**: Add sync metadata storage

### File Structure
```
src/selecta/ui/components/sync/
├── __init__.py
├── sync_center.py                 # Main sync center component
├── sync_overview_widget.py        # Stats and refresh controls
├── synced_playlist_list_widget.py # Playlist list with selection
├── sync_progress_widget.py        # Progress tracking
└── bulk_actions_widget.py         # Batch operation controls

src/selecta/ui/dialogs/
├── sync_preview_dialog.py         # Preview and confirmation dialog
└── sync_settings_dialog.py        # Sync configuration options

src/selecta/ui/components/common/
└── sync_status_cache.py           # Caching and data management
```

## Success Metrics

1. **Discoverability**: Users can easily find sync operations
2. **Transparency**: Clear preview of what will change before sync
3. **Efficiency**: Minimal API calls, fast UI responsiveness
4. **Control**: Users can selectively apply sync changes
5. **Feedback**: Clear progress and status information
6. **Recovery**: Easy to understand and fix sync conflicts

## Future Enhancements (Post-MVP)

1. **Automatic sync scheduling** with user-configurable intervals
2. **Sync templates** for common sync patterns
3. **Advanced conflict resolution** with metadata comparison
4. **Sync analytics** showing sync history and patterns
5. **Cross-platform playlist recommendations** based on content similarity
6. **Sync rules engine** for automated decision making

---

This implementation plan provides a comprehensive roadmap for making sync operations intuitive while maintaining efficiency and user control. The phased approach allows for iterative development and testing of each component.
