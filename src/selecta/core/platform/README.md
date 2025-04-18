# Platform Module Documentation

## Overview

The platform module is the core integration layer that connects Selecta with external music services (Spotify, Rekordbox, Discogs, YouTube). It handles authentication, data synchronization, cross-platform track linking, and provides a unified interface for interacting with these disparate platforms. This module enables Selecta's key functionality of bridging different music ecosystems.

## Architecture

The platform module follows a layered architecture built around platform abstraction:

1. **Interface Layer**:
   - `AbstractPlatform` defines a generic interface for all platforms
   - Type parameters allow platform-specific model typing
   - Common operations are unified across platforms

2. **Platform Layer**:
   - Platform-specific implementations (`SpotifyClient`, `RekordboxClient`, etc.)
   - Each platform handles its own authentication, API communication, and data models
   - Adapts platform-specific concepts to Selecta's unified model

3. **Integration Layer**:
   - `PlatformSyncManager` handles synchronization between local and remote data
   - `LinkManager` creates relationships between tracks across platforms
   - `PlatformFactory` creates and manages platform client instances

4. **Platform-Specific Components**:
   - Authentication management
   - Model conversion
   - Platform-specific functionality
   - API client implementation

## Key Components

### AbstractPlatform

- **File**: `abstract_platform.py`
- **Purpose**: Defines the common interface that all platform clients implement
- **Features**:
  - Generic type parameters for platform-specific models
  - Authentication methods
  - Playlist and track operations
  - Search functionality
  - Import/export operations

```python
class AbstractPlatform(Generic[P, T]):
    """Abstract base class for platform clients.

    Type Parameters:
        P: Platform-specific playlist type
        T: Platform-specific track type
    """

    def is_authenticated(self) -> bool: ...
    def authenticate(self) -> bool: ...
    def get_all_playlists(self) -> list[P]: ...
    def get_playlist_tracks(self, playlist_id: str) -> list[T]: ...
    def search_tracks(self, query: str, limit: int = 10) -> list[T]: ...
    # Plus many more methods...
```

### PlatformFactory

- **File**: `platform_factory.py`
- **Purpose**: Creates appropriate platform client instances
- **Features**:
  - Factory pattern implementation
  - Platform client instantiation with dependencies
  - Singleton-like client management
  - Supports all integrated platforms

```python
# Example usage
client = PlatformFactory.create("spotify", settings_repo)
```

### SyncManager

- **File**: `sync_manager.py`
- **Purpose**: Handles synchronization between local database and external platforms
- **Features**:
  - Bidirectional synchronization (local ↔ platform)
  - Track and playlist import/export
  - Platform-specific metadata preservation
  - Conflict resolution
  - Change tracking

### LinkManager

- **File**: `link_manager.py`
- **Purpose**: Manages relationships between tracks across different platforms
- **Features**:
  - Track matching algorithms
  - Metadata-based linking
  - Link persistence
  - Link quality assessment
  - Cross-platform identity management

## Platform Implementations

### Spotify

- **Directory**: `spotify/`
- **Components**:
  - `client.py`: SpotifyClient implementation of AbstractPlatform with synchronization logic
  - `auth.py`: OAuth2 authentication handling
  - `models.py`: Spotify-specific data models
- **Features**:
  - Playlist import/export
  - Track search
  - Track metadata retrieval
  - Album artwork integration

### Rekordbox

- **Directory**: `rekordbox/`
- **Components**:
  - `client.py`: RekordboxClient implementation of AbstractPlatform with synchronization logic
  - `auth.py`: Local database authentication
  - `models.py`: Rekordbox-specific data models
- **Features**:
  - Local database access
  - Playlist synchronization
  - DJ metadata integration
  - Track organization

### Discogs

- **Directory**: `discogs/`
- **Components**:
  - `client.py`: DiscogsClient implementation of AbstractPlatform with synchronization and matching logic
  - `api_client.py`: Low-level API client with rate limiting
  - `auth.py`: OAuth1 authentication handling
  - `models.py`: Discogs-specific data models
- **Features**:
  - Collection and wantlist integration
  - Vinyl metadata
  - Release information
  - Artist/label details
  - Vinyl record matching

### YouTube

- **Directory**: `youtube/`
- **Components**:
  - `client.py`: YouTubeClient implementation of AbstractPlatform
  - `auth.py`: OAuth2 authentication handling
  - `models.py`: YouTube-specific data models
  - `sync.py`: YouTube synchronization logic
- **Features**:
  - Playlist integration
  - Video metadata
  - Music video linking
  - Channel integration

## Usage Patterns

### Authentication Flow

```python
# Get client instance
spotify_client = PlatformFactory.create("spotify", settings_repo)

# Check authentication status
if not spotify_client.is_authenticated():
    # Authenticate (may trigger OAuth redirect in UI)
    success = spotify_client.authenticate()
    if not success:
        # Handle authentication failure
        pass
```

### Platform Operations

```python
# Get all playlists
playlists = spotify_client.get_all_playlists()

# Get tracks for a playlist
tracks = spotify_client.get_playlist_tracks(playlist_id)

# Search for tracks
results = spotify_client.search_tracks("artist name", limit=10)

# Create a new playlist
new_playlist = spotify_client.create_playlist("My Playlist", "Description")
```

### Synchronization

```python
# Create sync manager
sync_manager = PlatformSyncManager()

# Import a playlist from Spotify to local database
playlist, tracks = sync_manager.import_playlist(
    platform="spotify",
    platform_playlist_id="spotify_playlist_id"
)

# Export a local playlist to Rekordbox
platform_id = sync_manager.export_playlist(
    local_playlist_id=123,
    target_platform="rekordbox"
)

# Sync a playlist bidirectionally
added, removed = sync_manager.sync_playlist(local_playlist_id=123)
```

### Track Linking

```python
# Link tracks across platforms
link_manager = LinkManager()

# Link a local track to a Spotify track
success = link_manager.link_tracks(
    local_track_id=123,
    platform="spotify",
    platform_track_id="spotify_track_id",
    metadata=spotify_metadata
)

# Find possible matches
matches = link_manager.find_possible_matches(
    local_track_id=123,
    platform="discogs"
)
```

## Dependencies

- **Internal**:
  - `core.data`: Models and repositories for database operations
  - `core.utils`: Type helpers, caching, and other utilities
- **External**:
  - `spotipy`: Spotify API client library
  - `pyrekordbox`: Rekordbox database access library
  - `discogs_client`: Discogs API client
  - `google-auth-oauthlib`: YouTube authentication

## Extension Points

The platform module is designed for extensibility:

1. **New Platforms**: Add a new directory with client, auth, models, and sync components
2. **Enhanced Matching**: Extend LinkManager with improved matching algorithms
3. **Additional Operations**: Add methods to AbstractPlatform interface
4. **Custom Sync Logic**: Extend PlatformSyncManager for special synchronization needs

## Implementation Notes

- **Generic Types**: AbstractPlatform uses generic type parameters for type safety
- **Interface Consistency**: All platforms implement the same interface with consistent behavior
- **Error Handling**: Platform-specific errors are translated into consistent application errors
- **Caching**: Appropriate caching is used to reduce API calls and improve performance
- **Authentication State**: Platforms manage their own authentication state persistence
- **Lazy Loading**: Data is loaded on demand to minimize API usage
- **Pagination**: Large result sets are handled with pagination where appropriate

## Best Practices

- Use PlatformFactory to create platform clients rather than instantiating directly
- Check authentication status before performing operations
- Handle platform-specific rate limits and API constraints
- Prefer high-level sync operations over direct platform operations when possible
- Use type annotations for better IDE support
- Implement proper error handling for platform API failures

## Change History

- Initial implementation of platform abstraction with Spotify, Rekordbox and Discogs
- Added YouTube integration with playlist support
- Refactored linking system to improve cross-platform track matching
- Enhanced sync manager for better metadata preservation
- Improved authentication flows for better user experience
- Added caching for better performance
