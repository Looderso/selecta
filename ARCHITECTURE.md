# Selecta Architecture

## Overview

Selecta is a unified music library manager that integrates multiple platforms into a single interface, allowing users to seamlessly work with playlists across:

- Rekordbox (DJ library)
- Spotify (streaming playlists)
- Discogs (vinyl collection)
- YouTube (playback and music discovery)
- Local Library (Selecta's own database)

This document focuses on the architecture of the playlist component and its current refactoring to a more modular, capability-based design.

## Playlist Component Architecture

### Before Refactoring: Fragmented Approach

The original playlist component architecture had several limitations:

1. **Platform-Specific Implementations**: Each platform had its own isolated implementation with duplicated code
2. **Inconsistent Interfaces**: Different platforms implemented similar features in different ways
3. **Limited Caching**: Issues with unnecessary reloads when switching between platforms
4. **Tightly Coupled Components**: Platform-specific code scattered across UI components
5. **Hardcoded Platform Logic**: Limited ability to add new platforms or features

This approach resulted in a fragmented codebase that was difficult to maintain and extend:

```
src/selecta/ui/components/playlist/
├── spotify/
│   ├── spotify_playlist_data_provider.py  (Spotify-specific implementation)
│   ├── spotify_playlist_item.py
│   └── spotify_track_item.py
├── rekordbox/
│   ├── rekordbox_playlist_data_provider.py  (Rekordbox-specific implementation)
│   ├── rekordbox_playlist_item.py
│   └── rekordbox_track_item.py
├── discogs/...  (Similar pattern for Discogs)
├── youtube/...  (Similar pattern for YouTube)
├── library/...  (Local library implementation)
└── abstract_playlist_data_provider.py  (Incomplete abstraction)
```

Each platform had its own version of:

- Playlist data providers (managing platform data)
- Playlist items (representing playlists)
- Track items (representing tracks)

This led to code duplication, inconsistent behavior across platforms, and difficulty in adding new features.

### After Refactoring: Unified Platform Architecture

The new architecture introduces a clear separation of concerns with well-defined interfaces, base implementations, and a central registry:

```
src/selecta/ui/components/playlist/
├── interfaces.py  (Core interfaces/protocols for all platforms)
├── base_items.py  (Base implementation of playlist/track items)
├── base_platform_provider.py  (Common provider implementation)
├── cache_manager.py  (Enhanced caching with persistence)
├── platform_registry.py  (Central registry for all platforms)
├── platform_init.py  (Platform initialization)
├── spotify/
│   ├── spotify_playlist_data_provider.py  (Extends BasePlatformDataProvider)
│   ├── spotify_playlist_item.py  (Extends BasePlaylistItem)
│   └── spotify_track_item.py  (Extends BaseTrackItem)
├── rekordbox/...  (Similar pattern using base classes)
├── discogs/...  (Similar pattern using base classes)
├── youtube/...  (Similar pattern using base classes)
└── library/
    └── library_provider.py  (Reference implementation)
```

#### Key Components

1. **Interfaces** (`interfaces.py`)
   - `IPlatformDataProvider`: Core interface for all platform data providers
   - `IPlaylistItem`: Protocol for playlist items across platforms
   - `ITrackItem`: Protocol for track items across platforms
   - `IPlatformClient`: Interface for platform clients
   - `ICacheManager`: Interface for cache managers
   - `ISyncManager`: Interface for synchronization
   - `PlatformCapability`: Enum of supported capabilities

2. **Base Implementations**
   - `BasePlatformDataProvider`: Common implementation for data providers
   - `BasePlaylistItem`: Standard implementation for playlist items
   - `BaseTrackItem`: Standard implementation for track items

3. **Platform Registry**
   - Central registry for all platform providers
   - Singleton pattern for access across the application
   - Lazy initialization of platform clients and providers
   - Capability-based feature detection

4. **Enhanced Caching**
   - More robust caching with proper invalidation
   - Optional disk persistence for improved performance
   - Background refresh to prevent UI blocking

### Library as a Special Platform

The Library is treated as a platform in the new architecture, but with some special considerations:

1. **No External Client**: Unlike other platforms that connect to external services, the Library connects directly to Selecta's database
2. **Central Collection**: The Library manages the "Collection" playlist that contains all tracks in the system
3. **Target for Imports**: The Library serves as the destination for imports from other platforms
4. **Source for Exports**: The Library is the source for exports to other platforms

The `LibraryDataProvider` provides a reference implementation of the new architecture, demonstrating how to implement:

- Playlist and track operations
- Context menus
- Sync operations
- Platform capability reporting

## Comparing Old and New Library Implementations

### Old Implementation

The old implementation of the Library data provider had several limitations:

1. **Inheritance-Based Approach**: Extended the `AbstractPlaylistDataProvider`, which itself extended `PlaylistDataProvider`
2. **Direct Platform Client References**: Directly referenced other platform clients (Spotify, Rekordbox, Discogs)
3. **Hardcoded Platform Logic**: Explicit checks for each platform with hardcoded platform names
4. **Limited Error Handling**: Inconsistent error handling across different operations
5. **Basic Caching**: Simple caching with limited invalidation strategies

Key characteristics:

```python
class LibraryPlaylistDataProvider(AbstractPlaylistDataProvider):
    # Direct references to other platform clients
    self._spotify_client = None
    self._rekordbox_client = None
    self._discogs_client = None

    # Hardcoded platform checks
    if self._is_exported_to_spotify(playlist.id) and "spotify" not in synced_platforms:
        synced_platforms.append("spotify")

    if self._is_exported_to_rekordbox(playlist.id) and "rekordbox" not in synced_platforms:
        synced_platforms.append("rekordbox")

    # Similar checks for other platforms...
```

The old implementation split the functionality into three files:
- `library_playlist_data_provider.py`: Main provider implementation
- `library_playlist_item.py`: Playlist item implementation
- `library_track_item.py`: Track item implementation

### New Implementation

The new implementation (`LibraryDataProvider`) offers several improvements:

1. **Protocol-Based Design**: Implements well-defined protocols from `interfaces.py`
2. **Capability Declaration**: Explicitly declares supported features
3. **Base Class Extension**: Extends common `BasePlatformDataProvider`
4. **Platform Registry**: Uses the platform registry instead of direct client references
5. **Enhanced Caching**: Better caching with in-memory and optional disk persistence
6. **Improved Error Handling**: Consistent error handling throughout

Key improvements:

```python
class LibraryDataProvider(BasePlatformDataProvider):
    # Explicit capability declaration
    def get_capabilities(self) -> list[PlatformCapability]:
        return [
            PlatformCapability.IMPORT_PLAYLISTS,
            PlatformCapability.EXPORT_PLAYLISTS,
            PlatformCapability.SYNC_PLAYLISTS,
            # Other capabilities...
        ]

    # Dynamic platform handling via registry
    registry = get_platform_registry()
    search_platforms = registry.get_platforms_with_capability(PlatformCapability.SEARCH)

    # Better handling of sync relationships
    if (hasattr(playlist_item, "is_imported") and
        callable(playlist_item.is_imported) and
        playlist_item.is_imported()):
        # Handle imported playlist...
```

Currently, the new implementation contains all components in a single file:
- `new_libary_provider.py`: Contains `LibraryDataProvider`, `LibraryPlaylistItem`, and `LibraryTrackItem`

### Splitting Components for Better Maintainability

To improve readability and maintainability, we should split the new implementation into separate files:

1. **`library_data_provider.py`**: Contains only the `LibraryDataProvider` class
   - Main provider implementation
   - Platform capability declaration
   - Caching and refresh logic
   - UI interactions (context menus, etc.)

2. **`library_playlist_item.py`**: Contains only the `LibraryPlaylistItem` class
   - Extends `BasePlaylistItem`
   - Playlist-specific properties and methods
   - Icon handling and display logic

3. **`library_track_item.py`**: Contains only the `LibraryTrackItem` class
   - Extends `BaseTrackItem`
   - Track-specific properties and methods
   - Formatting and display logic

This separation of concerns will make the code easier to read, understand, and maintain, while also facilitating parallel development by different team members.

## Capability-Based Feature Activation

One of the key improvements in the new architecture is the capability-based approach to feature activation:

```python
# Platform declares its capabilities
def get_capabilities(self) -> list[PlatformCapability]:
    return [
        PlatformCapability.IMPORT_PLAYLISTS,
        PlatformCapability.EXPORT_PLAYLISTS,
        PlatformCapability.SYNC_PLAYLISTS,
        # Other capabilities...
    ]

# UI adapts based on capabilities
if PlatformCapability.IMPORT_PLAYLISTS in provider.get_capabilities():
    # Show import option in UI
```

This allows:

1. Each platform to declare what it can and cannot do
2. The UI to adapt dynamically based on available features
3. New capabilities to be added without modifying existing code
4. Clear documentation of platform limitations

## Implementation Status

The refactoring is following a phased approach:

1. ✅ Core interfaces and base classes have been created
2. ✅ Platform registry and initialization utilities are in place
3. ✅ Library provider (reference implementation) has been created
4. 🔄 Migration of other platform providers is in progress
   - Spotify: Not started
   - Rekordbox: Not started
   - Discogs: Not started
   - YouTube: Not started
5. 🔄 Update of main component to use registry is pending
6. 🔄 Removal of legacy code is pending

## Next Steps

To complete the migration:

1. Implement platform-specific providers for each platform
   - Create playlist items extending the base classes
   - Create track items extending the base classes
   - Implement the data provider with appropriate capabilities

2. Update the main playlist component to use the platform registry
   - Replace direct provider instantiation with registry lookups
   - Implement capability-based UI adaptation

3. Test thoroughly
   - Each provider in isolation
   - Interactions between providers
   - UI behavior with the new providers

4. Complete the transition by removing legacy code
   - Remove original platform-specific implementations
   - Remove `abstract_playlist_data_provider.py`

## Benefits of the New Architecture

The unified platform architecture provides several benefits:

1. **Consistency**: All platforms behave predictably with the same interface
2. **Reduced Code Duplication**: Common functionality shared in base classes
3. **Improved Caching**: Better performance with smarter caching
4. **Dynamic Feature Adaptation**: UI adapts based on platform capabilities
5. **Easier Maintenance**: Clear interfaces for future extensions
6. **Better Error Handling**: Standardized error handling across platforms
7. **Simpler Testing**: Consistent interface makes testing more straightforward

## Challenges

Implementing this architecture presents some challenges:

1. **Backward Compatibility**: Maintaining existing functionality during migration
2. **Platform Peculiarities**: Handling platform-specific edge cases
3. **Testing Complexity**: Ensuring all platforms work correctly with the new architecture
4. **Performance Optimization**: Balancing caching with fresh data
