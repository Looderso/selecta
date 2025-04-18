# Core Utilities Module Documentation

## Overview

The core utilities module provides essential functionality that's used throughout the Selecta application. These utilities include file system operations, audio playback, metadata extraction, caching, threading, and type helpers.

## Key Components

### Path Management

- **PathHelper**: Provides standardized paths for application data, configuration, and resources
- Functions for resolving file paths across different runtime environments (dev, packaged app)

### Type Helpers

- **Type Conversion**: Functions to safely convert between types (especially for SQLAlchemy objects)
- **TypeGuard Functions**: Type narrowing functions for protocol/interface checking
- **Protocols**: Runtime-checkable interfaces for component capabilities (HasX)
- **TypedDict**: Structured dictionary types for data exchange

### Audio Utilities

- **AudioPlayer**: Audio playback components with platform-specific implementations
- **MetadataExtractor**: Extracts metadata and album artwork from audio files

### Performance Utilities

- **CacheManager**: Generic caching system for expensive operations
- **ThreadManager**: Background threading utilities for UI responsiveness
- **Worker**: Task execution in background threads with signal integration

### UI Utilities

- **LoadingManager**: Manages loading overlays for long-running operations

### File System Utilities

- **FolderScanner**: Scans music folders and reconciles with the database

## File Structure

- `path_helper.py`: Standardized application paths and resource location
- `type_helpers.py`: Type conversion and TypeGuard functions
- `audio_player.py`: Audio playback implementation
- `metadata_extractor.py`: Audio file metadata extraction
- `cache_manager.py`: Generic caching system
- `worker.py`: Background thread management
- `loading.py`: Loading indicators for UI operations
- `folder_scanner.py`: Music folder scanning and importing

## Dependencies

- Internal: core.data for database operations
- External: PyQt6 for UI integration, mutagen for audio metadata

## Common Tasks

### Working with Paths

- **Getting app data paths**: Use `get_app_data_path()`, `get_app_config_path()`, etc.
- **Resolving resources**: Use `get_resource_path(relative_path)` for consistent resource access

### Thread Management

- **Running background tasks**: Use `ThreadManager().run_task(function, *args, **kwargs)`
- **Handling task completion**: Connect to worker signals (`finished`, `result`, etc.)

### Audio Playback

- **Creating a player**: Use `AudioPlayerFactory.create_player(platform)`
- **Playback control**: Use `player.play()`, `player.pause()`, etc.
- **Track loading**: Use `player.load_track(track)` with appropriate track object

### Type Safety

- **Protocol checking**: Use functions like `has_artist_and_title(obj)` for runtime type checking
- **Safe type conversion**: Use `ensure_type(value, target_type)` for consistent conversions
- **Dictionary access**: Use helper functions like `dict_int(data, key, default)` for type-safe access

### Caching

- **Basic caching**: Use `cache.set(key, data)` and `cache.get(key)`
- **Advanced caching**: Use `cache.get_or_set(key, data_getter_function)`
- **Invalidation**: Use `cache.invalidate(key)` or `cache.clear()`

### UI Loading Indicators

- **Showing loading overlay**: `LoadingManager.show_loading(parent_widget, message)`
- **Hiding loading overlay**: `LoadingManager.hide_loading(parent_widget)`

### Folder Scanning

- **Scanning music folders**: Use `LocalFolderScanner(folder_path).scan_folder()`
- **Importing music**: Use `scanner.import_untracked_files()`

## Implementation Notes

- Utility modules are designed to be independent and reusable
- Many utilities follow singleton patterns for resource efficiency
- Type helpers provide runtime type safety where static typing is insufficient
- Path utilities handle differences between development and production environments
- Threading utilities integrate with PyQt's signal/slot mechanism

## Change History

- Initial implementation of core utilities
- Added audio playback and metadata extraction
- Added thread management for background tasks
- Added loading indicators for improved UI experience
- Enhanced type helpers for better type safety
