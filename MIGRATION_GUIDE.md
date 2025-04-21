# Migration Guide: Unified Platform Architecture

This guide provides instructions for migrating the current playlist component code to the new unified platform architecture. The new architecture addresses issues with inconsistencies between platforms, caching problems, and code duplication.

## Overview of Changes

1. **New Base Interfaces**: Clear interfaces that all platforms must implement
2. **Unified Base Classes**: Common implementations for shared functionality
3. **Enhanced Caching**: More robust caching with proper invalidation
4. **Platform Registry**: Central management of platform providers
5. **Standardized Data Models**: Consistent models across platforms
6. **Capability-Based UI**: UI adapts based on platform capabilities
7. **Layered Architecture**: Separation between core platform logic (AbstractPlatform) and UI components (IPlatformClient)

## Migration Strategy

We recommend a phased approach to migration:

1. Add the new interfaces and base classes without disturbing existing code
2. Create the platform registry and initialize platforms
3. Implement the new Library provider as a reference
4. Gradually migrate each platform provider, one at a time
5. Update the main component to use the platform registry
6. Remove the old code once migration is complete

## Step-by-Step Migration

### Phase 1: Introducing New Interfaces

1. Add the new interface files:
   - `interfaces.py`: Core interfaces for platform providers and data models
   - `base_platform_provider.py`: Base implementation for platform providers
   - `base_items.py`: Base implementations for playlist and track items
   - `cache_manager.py`: Enhanced caching manager
   - `platform_registry.py`: Central platform registry
   - `platform_init.py`: Platform initialization utilities

2. Keep all existing code intact during this phase

### Phase 2: Implement Reference Provider

1. Create a new version of the Library provider:
   - `library/new_library_provider.py`: Implement the provider with new interfaces
   - Initially, this will exist alongside the current implementation

2. Test the new provider in isolation to ensure it works correctly

### Phase 3: Migrate Platform Providers

For each platform (Spotify, Rekordbox, Discogs, YouTube), follow these steps:

1. Create a new provider implementation that extends `BasePlatformDataProvider`
2. Create new playlist and track item implementations that extend base classes
3. Add capability declarations based on platform features
4. Register the provider with the platform registry
5. Test each provider individually before moving to the next

### Phase 4: Update the Main Component

1. Modify `playlist_component.py` to use the platform registry:

   ```python
   from selecta.ui.components.playlist.platform_registry import get_platform_registry

   registry = get_platform_registry()
   provider = registry.get_provider(platform_name)
   self.set_data_provider(provider)
   ```

2. Update any platform-specific code to use capabilities:

   ```python
   if PlatformCapability.IMPORT_PLAYLISTS in provider.get_capabilities():
       # Show import option
   ```

3. Handle platforms dynamically instead of hardcoding platform names

### Phase 5: Cleanup

1. Replace all uses of old providers with new ones
2. Remove deprecated code
3. Update tests to use the new architecture
4. Align Core Platform and UI Interfaces: Resolve the mismatch between `AbstractPlatform` and `IPlatformClient` interfaces by either:
   - Making `AbstractPlatform` implementations explicitly implement `IPlatformClient`
   - Creating proper adapter classes instead of using type casting
   - Consolidating the interfaces if appropriate

## Code Changes by File

### New Files

- `interfaces.py`: Core interfaces for the platform architecture
- `base_platform_provider.py`: Common implementation for all providers
- `base_items.py`: Base implementations for playlist and track items
- `cache_manager.py`: Enhanced caching system
- `platform_registry.py`: Central platform management
- `platform_init.py`: Platform initialization

### Modified Files

- `playlist_component.py`: Update to use platform registry
- Platform-specific provider files (create new versions)
- Platform-specific item files (create new versions)

### Files to Eventually Remove

- Original platform-specific provider implementations
- `abstract_playlist_data_provider.py` (replaced by `base_platform_provider.py`)
- Platform-specific folder structures (unified under new architecture)

## Benefits of Migration

1. **Consistency**: All platforms behave the same way
2. **Reduced Duplication**: Common code shared in base classes
3. **Better Caching**: Prevents unnecessary reloads
4. **Dynamic Behavior**: UI adapts based on platform capabilities
5. **Easier Maintenance**: Clear interfaces for future extensions
6. **Improved Performance**: Optimized refresh and loading
7. **Better Error Handling**: Standardized across platforms
8. **Clear Separation of Concerns**: Distinct interfaces for core platform logic (AbstractPlatform) and UI interactions (IPlatformClient)

## Testing Strategy

1. Test each provider in isolation first
2. Test interaction between providers via the registry
3. Test UI components with the new providers
4. Test caching behavior with realistic usage patterns
5. Test error handling and recovery
6. Test platform switching behavior
7. Test overall application performance

## Additional Resources

The code includes extensive documentation and examples. Refer to class docstrings for detailed usage information.
