# Selecta Architecture Guide

This document outlines the architectural patterns and design principles for the Selecta music library management application.

## System Overview

Selecta is a unified music library manager that integrates multiple music platforms:
- Rekordbox (DJ library)
- Spotify (streaming service)
- Discogs (vinyl collection)
- Local music files

The application provides a cohesive interface to manage music across these platforms, enabling seamless synchronization and organization of playlists and tracks.

**Recent Architecture Updates:**
- Enhanced platform client implementations to consistently follow the AbstractPlatform interface
- Completed implementation of the PlatformSyncManager for centralized synchronization logic
- Standardized PlaylistDataProvider implementations for all platforms
- Added comprehensive support for Discogs import/export operations

## Key Concepts

- **Syncing**: Bidirectional process of transferring playlists and tracks between platforms
- **Linking**: Creating connections between representations of the same track across different platforms
- **Import/Export**: Moving playlists and tracks between platforms and the local database

## Architecture

### Core Components

1. **Platform Clients**: Responsible for direct communication with external services
2. **Data Repositories**: Handle database operations and persistence
3. **Sync Manager**: Coordinates synchronization between platforms
4. **Data Providers**: Supply UI components with data from various sources
5. **UI Components**: Present data and capture user interactions

### Component Relationships

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   UI Components   │◄───►│ Data Providers    │────►│ Repositories      │
└─────────┬─────────┘     └────────┬──────────┘     └─────────┬─────────┘
          │                        │                          │
          │                        ▼                          ▼
          │              ┌───────────────────┐     ┌───────────────────┐
          └─────────────►   PlatformSync    │────►│     Database       │
                         │     Manager      │     └───────────────────┘
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌───────────────────┐
                         │  Platform Clients  │
                         └───────────────────┘
```

## Platform Integration Architecture

### AbstractPlatform (Interface)

The base class for all platform integrations, defining a standard interface for:
- Authentication
- Playlist and track operations
- Synchronization primitives

```python
class AbstractPlatform(ABC, Generic[T, P]):
    @abstractmethod
    def is_authenticated(self) -> bool: ...

    @abstractmethod
    def authenticate(self) -> bool: ...

    @abstractmethod
    def get_all_playlists(self) -> list[P]: ...

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> list[T]: ...

    @abstractmethod
    def search_tracks(self, query: str, limit: int = 10) -> list[T]: ...

    @abstractmethod
    def create_playlist(self, name: str, description: str = "") -> P: ...

    @abstractmethod
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool: ...

    @abstractmethod
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool: ...

    @abstractmethod
    def import_playlist_to_local(self, platform_playlist_id: str) -> tuple[list[T], P]: ...

    @abstractmethod
    def export_tracks_to_playlist(
        self,
        playlist_name: str,
        track_ids: list[str],
        existing_playlist_id: str | None = None
    ) -> str: ...
```

### PlatformSyncManager

Centralizes synchronization logic between the local database and external platforms:
- Handles conversion between platform-specific and local data models
- Manages the linking of tracks across platforms
- Provides a consistent interface for import/export operations

```python
class PlatformSyncManager:
    def __init__(self, platform_client: AbstractPlatform, ...): ...

    def import_track(self, platform_track: Any) -> Track: ...
    def import_playlist(self, platform_playlist_id: str) -> tuple[Playlist, list[Track]]: ...
    def export_playlist(self, local_playlist_id: int, platform_playlist_id: str = None) -> str: ...
    def sync_playlist(self, local_playlist_id: int) -> tuple[int, int]: ...
    def link_tracks(self, local_track_id: int, platform_track: Any) -> bool: ...
```

### PlaylistDataProvider (Interface)

Provides a consistent interface for the UI to access and manipulate playlist data:
- Methods for retrieving playlists and tracks
- Handles caching of remote data
- Provides UI-specific operations like context menus
- Delegates synchronization to PlatformSyncManager

```python
class PlaylistDataProvider(ABC):
    @abstractmethod
    def get_all_playlists(self) -> list[PlaylistItem]: ...

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]: ...

    @abstractmethod
    def get_platform_name(self) -> str: ...

    @abstractmethod
    def show_playlist_context_menu(self, tree_view: QTreeView, position: Any) -> None: ...

    @abstractmethod
    def refresh(self) -> None: ...

    def refresh_playlist(self, playlist_id: Any) -> None: ...
    def import_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool: ...
    def export_playlist(self, playlist_id: Any, target_platform: str, parent: QWidget | None = None) -> bool: ...
    def sync_playlist(self, playlist_id: Any, parent: QWidget | None = None) -> bool: ...
    def create_new_playlist(self, parent: QWidget | None = None) -> bool: ...
```

## Data Flow

### Importing a Playlist

1. User initiates playlist import from UI
2. PlaylistDataProvider calls PlatformSyncManager.import_playlist()
3. PlatformSyncManager:
   - Uses platform client to fetch playlist data
   - Creates local database records
   - Handles track matching and linking
   - Returns the newly created playlist
4. PlaylistDataProvider refreshes the UI

### Exporting a Playlist

1. User selects a playlist to export
2. PlaylistDataProvider calls PlatformSyncManager.export_playlist()
3. PlatformSyncManager:
   - Retrieves tracks from local database
   - Filters tracks that have metadata for the target platform
   - Uses platform client to create/update playlist
   - Updates local playlist with platform identifier
4. PlaylistDataProvider refreshes the UI

### Synchronizing a Playlist

1. User initiates playlist sync
2. PlaylistDataProvider calls PlatformSyncManager.sync_playlist()
3. PlatformSyncManager:
   - Imports new tracks from platform
   - Exports new local tracks to platform
   - Updates metadata for existing tracks
   - Handles conflict resolution
4. PlaylistDataProvider refreshes the UI

## Implementation Guidelines

1. **Separation of Concerns**
   - Platform clients should only handle API communication
   - Repositories should only handle database operations
   - SyncManager should handle conversion between platforms
   - UI components should only handle presentation and user interaction

2. **Error Handling**
   - Platform clients should handle API-specific errors
   - SyncManager should handle synchronization conflicts
   - All components should provide meaningful error messages

3. **Type Safety**
   - Use generic types for platform-specific models
   - Use type hints consistently
   - Use TypedDict and Protocol for structural typing

4. **Consistency**
   - Follow the same patterns across all platform integrations
   - Use the same method names and signatures for similar operations
   - Handle errors in a consistent way

## Platform-Specific Considerations

### Spotify
- Uses OAuth2 authentication
- Has well-defined API with rate limits
- Requires refresh token management
- Supports full playlist synchronization

### Rekordbox
- Uses local database access
- Limited API, primarily read operations
- Requires careful handling of file paths
- Supports playlist import/export

### Discogs
- Uses OAuth for authentication
- Has strict rate limiting
- Primarily for collection/wantlist management, not playlists
- Focus on metadata enrichment rather than playback

## Database Model

### Core Entities

- **Track**: Central entity representing a music track
- **Playlist**: Collection of tracks with ordering
- **TrackPlatformInfo**: Links tracks to their platform-specific representations
- **Settings**: Application configuration and platform credentials

### Key Relationships

- A Track can have multiple TrackPlatformInfo records (one per platform)
- A Playlist can contain multiple Tracks (through PlaylistTrack)
- A Playlist can be linked to a platform-specific playlist via platform_id

## Future Development

1. **Enhanced Synchronization**
   - Conflict resolution improvements
   - Smarter track matching across platforms
   - Selective synchronization

2. **Platform Expansion**
   - Support for additional music platforms
   - More comprehensive metadata integration
   - Improved local file management

3. **User Experience**
   - Improved sync progress reporting
   - Better visualization of cross-platform relationships
   - Advanced playlist management features
