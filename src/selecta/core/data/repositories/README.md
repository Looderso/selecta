# Repositories Documentation

## Overview
This directory contains repository classes that provide a clean, abstracted interface for database operations in Selecta. Each repository encapsulates the data access logic for a specific domain entity, following the Repository pattern.

## Repository Pattern
The Repository pattern provides several benefits in Selecta:
1. **Abstraction**: Shields application code from database implementation details
2. **Centralized Data Logic**: Keeps query and transaction logic in one place
3. **Testability**: Makes data access code easier to mock and test
4. **Type Safety**: Provides strongly typed interfaces for database operations

## Core Repositories

### TrackRepository
- **File**: `track_repository.py`
- **Purpose**: Manages track data and relationships
- **Key Features**:
  - CRUD operations for tracks
  - Search functionality with filtering
  - Platform linking and synchronization
  - Metadata and attribute management
  - Genre and tag association

### PlaylistRepository
- **File**: `playlist_repository.py`
- **Purpose**: Manages playlists and track collections
- **Key Features**:
  - Playlist creation and management
  - Hierarchical playlist structure (folders)
  - Track ordering within playlists
  - Platform synchronization for playlists
  - Export/import functionality

### SettingsRepository
- **File**: `settings_repository.py`
- **Purpose**: Manages application settings and platform credentials
- **Key Features**:
  - Typed access to application settings
  - Secure credential storage
  - Default values and validation
  - Configuration persistence

### ImageRepository
- **File**: `image_repository.py`
- **Purpose**: Manages artwork for tracks and albums
- **Key Features**:
  - Image storage and retrieval
  - Image resizing for different display contexts
  - Binary data management
  - Platform image synchronization

### VinylRepository
- **File**: `vinyl_repository.py`
- **Purpose**: Manages vinyl record metadata (Discogs integration)
- **Key Features**:
  - Vinyl record data management
  - Discogs-specific metadata
  - Track-to-vinyl linking

## Common Repository Patterns

### CRUD Operations
All repositories implement standard Create, Read, Update, Delete operations:
```python
# Create
entity = repo.create(entity_data)

# Read
entity = repo.get_by_id(entity_id)
entities = repo.get_all()

# Update
updated_entity = repo.update(entity_id, updated_data)

# Delete
repo.delete(entity_id)
```

### Search and Filter
Repositories provide methods for searching and filtering entities:
```python
# Basic search
results, count = repo.search(query, limit=20, offset=0)

# Advanced filtering
results = repo.filter_by(
    artist="Artist Name",
    year=2023,
    genre_ids=[1, 2, 3]
)
```

### Relationship Management
Repositories handle relationship operations:
```python
# Adding associations
repo.add_genre(track_id, genre_id)
repo.add_to_playlist(playlist_id, track_id, position=None)

# Managing platform links
repo.link_to_platform(track_id, platform, platform_id, platform_data)
```

### Batch Operations
Repositories support efficient batch operations:
```python
# Bulk creation
repo.create_many(entity_data_list)

# Bulk updates
repo.update_many(update_criteria, update_data)

# Bulk deletion
repo.delete_many(delete_criteria)
```

## Implementation Details

### Base Repository
Most repositories inherit from `BaseRepository[T]` which provides:
- Generic type parameters for model classes
- Common CRUD operations
- Session management and transaction boundaries
- Error handling and logging

### Session Management
Repositories implement two session management approaches:
1. **Internal session**: Repository creates and manages its own session
2. **External session**: Repository accepts a session from the caller

### Query Construction
Repositories use SQLAlchemy's query builder patterns:
- Composable filter conditions
- Eager loading configuration
- Ordering and pagination
- Result transformation

### Transaction Safety
Repositories handle transaction boundaries:
- Automatic commits on successful operations
- Rollback on exceptions
- Context managers for multi-operation transactions

## Usage Examples

### Basic Repository Usage
```python
# Creating a track
track_repo = TrackRepository()
new_track = track_repo.create({
    "title": "Track Title",
    "artist": "Artist Name",
    "duration_ms": 240000
})

# Updating a track
updated_track = track_repo.update(
    track_id,
    {"title": "Updated Title"}
)

# Searching for tracks
tracks, count = track_repo.search("electronic", limit=20, offset=0)
```

### Advanced Usage
```python
# Using transaction context
from selecta.core.data.database import session_scope

with session_scope() as session:
    # Create repositories with shared session
    track_repo = TrackRepository(session)
    playlist_repo = PlaylistRepository(session)

    # Operations within a single transaction
    track = track_repo.create(track_data)
    playlist = playlist_repo.create(playlist_data)
    playlist_repo.add_track(playlist.id, track.id)
    # Commit happens automatically at end of context
```

## Best Practices
- Use repositories instead of direct SQLAlchemy queries
- Prefer batch operations for better performance
- Use appropriate eager loading to prevent N+1 query problems
- Keep repository methods focused on a single responsibility
- Use typed returns and parameters for better IDE support
- Handle errors appropriately with context-specific messages
