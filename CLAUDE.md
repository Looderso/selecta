# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Selecta is a unified music library manager integrating:
- Rekordbox (DJ library)
- Spotify (streaming playlists)
- Discogs (vinyl collection)

Key features:
- Cross-platform playlist synchronization
- Track matching between platforms
- Music library organization
- Modern PyQt6-based UI

## Platform Synchronization Strategy
Selecta follows a consistent approach for platform integration:

### Key Concepts
- **Syncing**: The bi-directional process of importing and exporting tracks/playlists between platforms
- **Linking**: Creating connections between tracks across platforms by storing platform-specific metadata

### Core Goals
- Import playlists from any platform into the local database
- Export local playlists to external platforms
- Sync changes bidirectionally (update both local and platform data)
- Store platform IDs for each synchronized entity to maintain relationships
- Enable cross-platform workflow (e.g., import from Spotify, add tracks, export to Rekordbox)

### Platform-Specific Notes
- **Rekordbox & Spotify**: Full playlist import/export/sync functionality
- **Discogs**: Limited to wantlist/collection integration (not traditional playlists)
  - Use wantlist/collection to mark tracks owned or wanted
  - Still add Discogs metadata to tracks for linking

## Platform Integration Architecture

### Key Components

1. **AbstractPlatform**
   - Base class for all platform clients
   - Defines standard interface for authentication and platform operations
   - Contains methods for playlist management and track operations
   - Used by: SpotifyClient, RekordboxClient, DiscogsClient
   - Uses generic type parameters for platform-specific models

2. **PlatformSyncManager**
   - Centralizes sync operations between local database and platforms
   - Handles importing/exporting tracks and playlists
   - Manages linking tracks between platforms
   - Ensures consistent sync behavior across all platforms
   - Converts between platform-specific and local data models

3. **PlaylistDataProvider**
   - Interface for providing playlist data to UI components
   - Methods for accessing playlists and tracks with caching
   - Platform-specific implementations handle UI interactions
   - Leverages PlatformSyncManager for sync operations
   - Provides consistent UI experience across platforms

### Component Relationships

```
┌─────────────────────┐     ┌─────────────────────┐
│   UI Components     │◄────┤ PlaylistDataProvider│
└─────────────────────┘     └────────────┬────────┘
                                         │
                                         ▼
┌─────────────────────┐     ┌─────────────────────┐
│   PlatformFactory   │─────►  PlatformSyncManager│
└─────────────────────┘     └────────────┬────────┘
                                         │
                                         ▼
┌─────────────────────┐     ┌─────────────────────┐
│  AbstractPlatform   │◄────┤ Platform Clients    │
└─────────────────────┘     └─────────────────────┘
```

### Implementation Details

1. **AbstractPlatform Interface**
   - Standard methods for all platforms: authentication, playlist/track operations
   - Clear separation between platform-specific and common functionality
   - Generic type parameters for better type safety
   - Example methods:
     - `is_authenticated() -> bool`
     - `authenticate() -> bool`
     - `get_all_playlists() -> list[P]`
     - `get_playlist_tracks(playlist_id: str) -> list[T]`
     - `search_tracks(query: str, limit: int = 10) -> list[T]`
     - `create_playlist(name: str, description: str = "") -> P`
     - `add_tracks_to_playlist(playlist_id: str, track_ids: list[str]) -> bool`
     - `remove_tracks_from_playlist(playlist_id: str, track_ids: list[str]) -> bool`
     - `import_playlist_to_local(platform_playlist_id: str) -> tuple[list[T], P]`
     - `export_tracks_to_playlist(playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None) -> str`

2. **PlatformSyncManager**
   - Methods for importing/exporting tracks and playlists
   - Track linking between platforms
   - Handles complex synchronization logic
   - Example methods:
     - `import_track(platform_track: Any) -> Track`
     - `import_playlist(platform_playlist_id: str) -> tuple[Playlist, list[Track]]`
     - `export_playlist(local_playlist_id: int, platform_playlist_id: str | None = None) -> str`
     - `sync_playlist(local_playlist_id: int) -> tuple[int, int]`
     - `link_tracks(local_track_id: int, platform_track: Any) -> bool`

3. **PlaylistDataProvider Interface**
   - Standard methods for UI data access
   - Consistent sync methods across all platforms
   - Example methods:
     - `get_all_playlists() -> list[PlaylistItem]`
     - `get_playlist_tracks(playlist_id: Any) -> list[TrackItem]`
     - `get_platform_name() -> str`
     - `show_playlist_context_menu(tree_view: QTreeView, position: Any) -> None`
     - `refresh() -> None`
     - `refresh_playlist(playlist_id: Any) -> None`
     - `import_playlist(playlist_id: Any, parent: QWidget | None = None) -> bool`
     - `export_playlist(playlist_id: Any, target_platform: str, parent: QWidget | None = None) -> bool`
     - `sync_playlist(playlist_id: Any, parent: QWidget | None = None) -> bool`
     - `create_new_playlist(parent: QWidget | None = None) -> bool`

### Platform Client Implementation Notes

#### SpotifyClient
- Uses `spotipy` library for API access
- Handles OAuth authentication flow via SpotifyAuthManager
- Manages token refresh and persistence
- Handles pagination of API responses
- Converts Spotify API responses to application models

#### RekordboxClient
- Uses `pyrekordbox` library to access Rekordbox database
- Implements a singleton pattern for database connection
- Includes special handling for when Rekordbox is running
- Handles local file operations and path management
- Converts Rekordbox database entries to application models

#### DiscogsClient
- Uses custom DiscogsApiClient for API access
- Handles OAuth authentication flow
- Treats collection and wantlist as "playlists"
- Focuses on vinyl/release metadata
- Converts Discogs API responses to application models

## Data Flow Examples

### Importing a Spotify Playlist
1. User selects a Spotify playlist in UI
2. UI calls `SpotifyPlaylistDataProvider.import_playlist()`
3. Provider uses PlatformSyncManager to handle the import
4. Manager calls `SpotifyClient.import_playlist_to_local()`
5. Client fetches playlist data from Spotify API
6. Manager converts Spotify tracks to local database models
7. Tracks and playlist are saved to database with platform links
8. UI is refreshed to show the new local playlist

### Exporting to Rekordbox
1. User selects a local playlist to export to Rekordbox
2. UI calls `LocalPlaylistDataProvider.export_playlist()`
3. Provider uses PlatformSyncManager to handle the export
4. Manager fetches tracks from local database
5. Local files without Rekordbox metadata are added to Rekordbox
6. Manager creates a new playlist in Rekordbox via client
7. Playlist is updated in local database with Rekordbox ID
8. UI is refreshed to reflect changes

## Build/Run/Test Commands
- Run app: `selecta-gui`
- Reset database: `selecta database init --force`
- Linting/type checking: `ruff check src`
- Run all tests: `pytest`
- Run specific test: `pytest -m [rekordbox|spotify|discogs]`

## Code Style Guidelines
- Python 3.11+ with strict typing
- Line length: 100 characters
- Use Google docstring style
- Imports: group by stdlib, third-party, first-party
- Types: Union syntax (`Type | None` vs `Optional[Type]`), Protocol for interfaces
- Name private methods/attributes with leading underscore
- Follow SQLAlchemy 2.0 type hints with `Mapped[Type]`
- Handle errors with contextual error messages
- Type all function parameters and return values
- Create TypeGuard functions for type narrowing with attribute checks

For detailed typing guidelines, see TYPING_GUIDELINES.md

## Documentation System and Token Optimization

### Documentation Hierarchy
Selecta implements a comprehensive documentation system to optimize token usage and speed up development:

1. **Top-Level Documentation**
   - **CLAUDE.md** (this file): Project overview and architectural guidance
   - **CODE_INDEX.md**: Quick reference for locating features and files
   - **SESSION_RULES.md**: Configuration for the current session

2. **Module-Level Documentation**
   - Each major module contains a **README.md** with module-specific details:
     - Module purpose and architecture
     - Component relationships
     - File structure and responsibilities
     - Usage patterns and examples

3. **Sub-Module Documentation**
   - Complex modules have additional READMEs in subdirectories
   - Platform integrations each have their own detailed documentation
   - UI component groups have specialized guides

### Documentation Content
Each README follows a consistent format:
- **Overview**: High-level description of the module's purpose
- **Architecture**: Component structure and relationships
- **File Structure**: Detailed listing of files and their purposes
- **Common Tasks**: How to accomplish typical development tasks
- **Implementation Notes**: Key design patterns and approaches
- **Dependencies**: Internal and external dependencies
- **Usage Examples**: Code examples demonstrating common operations
- **Change History**: Record of significant updates

### Token Optimization Strategy

#### Navigation Process
Follow this sequence to minimize token usage:

1. **Start with CODE_INDEX.md**
   - Locate the general area you need to work with
   - Find references to specific module documentation

2. **Read Module README.md**
   - Understand the module's architecture and patterns
   - Identify specific files relevant to your task

3. **Read Sub-Module README.md** (if applicable)
   - Get detailed information about specific components
   - Find exact file locations for your changes

4. **Examine Specific Files**
   - Only after understanding the context through documentation
   - Focus on relevant sections rather than entire files

5. **Make Targeted Changes**
   - With full understanding of the architecture and file purposes
   - Following established patterns from the documentation

#### Searching Strategy
- **Avoid broad searches** (e.g., "find all occurrences of X")
- **Use targeted searches** guided by documentation
- **Follow the documentation path** to locate functionality
- **Use CODE_INDEX.md** as your primary navigation tool

### Documentation Update Process
Maintaining documentation is crucial for continued token optimization:

1. **Update README.md** when making significant changes to a module
2. **Update CODE_INDEX.md** when adding new files or changing structure
3. **Add new README.md files** for new modules or significant components
4. **Follow the template format** for consistency across documentation
5. **Document changes** in the Change History section of affected READMEs

### Documentation Usage Examples

#### Finding and Modifying Platform Integration Code
```
1. Check CODE_INDEX.md → Platform Integrations → Spotify
2. Read src/selecta/core/platform/spotify/README.md
3. Identify the specific component (Auth, Client, Models, Sync)
4. Navigate to the specific file
5. Make changes following established patterns
6. Update documentation if necessary
```

#### Adding a New UI Feature
```
1. Check CODE_INDEX.md → UI Components
2. Read src/selecta/ui/README.md for overall UI architecture
3. Locate relevant component area (Playlist, Player, etc.)
4. Read component-specific README.md
5. Create new component following established patterns
6. Update documentation to include the new component
```

### Navigation Workflow Summary
1. Start with top-level documentation
2. Find relevant module in CODE_INDEX.md
3. Read module README.md for architecture understanding
4. Check sub-module README.md for component details
5. Only then read and modify specific code files
6. Update documentation to reflect your changes
