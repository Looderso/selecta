# Data Module Documentation

## Overview
The data module handles all database operations, models, and data access in Selecta. It provides a clean abstraction over SQLAlchemy for working with music metadata, playlists, and platform-specific data. This module is the foundation of the application's data management, enabling cross-platform music library integration.

## Key Components
- **Database**: Core database configuration and connection management
- **Models**: SQLAlchemy model definitions for all application entities
- **Repositories**: Data access layer providing methods to work with models
- **Migrations**: Database migration scripts for schema evolution
- **Types**: Custom type definitions and base classes

## Database Architecture
Selecta uses SQLite as its database engine with SQLAlchemy as the ORM. The database architecture is designed to support:

1. **Cross-platform integration**: Storing platform-specific metadata while maintaining unified track/playlist representations
2. **Flexible metadata**: Supporting various tag and attribute systems across different music platforms
3. **Optimized performance**: Connection pooling, WAL journal mode, and tuned pragmas for SQLite
4. **Data integrity**: Foreign key constraints and transaction management

### Core Entities

#### Tracks and Metadata
- **Track**: Central entity representing a music track across all platforms
- **TrackPlatformInfo**: Platform-specific metadata for tracks (Spotify, Rekordbox, Discogs)
- **TrackAttribute**: Dynamic attributes for tracks (energy, danceability, etc.)
- **Album**: Album information associated with tracks
- **Genre/Tag**: Categorization entities that can be attached to tracks

#### Playlists and Organization
- **Playlist**: Represents a collection of tracks or nested folders
- **PlaylistTrack**: Ordered association between playlists and tracks
- **PlaylistPlatformInfo**: Platform-specific metadata for playlists

#### Other Entities
- **Image**: Storage for artwork in various sizes
- **VinylRecord**: Information specific to vinyl records (Discogs integration)
- **UserSettings**: Application settings and preferences
- **PlatformCredentials**: Securely stored authentication for external platforms

## File Structure
- `database.py`: Core database setup and connection handling
  - Connection management, session handling, SQLite optimizations
  - Thread-safe engine and session factories
- `init_db.py`: Database initialization and schema creation
- `types.py`: Custom data types and type definitions
  - Base repository class and type annotations
- `models/`: SQLAlchemy model definitions
  - `db.py`: Core model classes (Track, Playlist, etc.)
- `repositories/`: Repository pattern implementations for data access
  - `track_repository.py`: Methods for working with tracks
  - `playlist_repository.py`: Methods for working with playlists
  - `settings_repository.py`: Application settings storage
  - `image_repository.py`: Methods for track/album artwork
  - `vinyl_repository.py`: Vinyl record metadata handling
- `migrations/`: Alembic migration scripts
  - Version-controlled database schema changes

## Repository Pattern
The data module implements the Repository pattern to provide a clean, abstracted interface for data access:

1. **BaseRepository**: Generic base class with common CRUD operations
2. **Specialized Repositories**: Implement domain-specific logic for each entity type
3. **Session Management**: Repositories handle SQLAlchemy sessions and transaction boundaries
4. **Type Safety**: Strong typing for both inputs and outputs

### Repository Features
- **Eager Loading**: Configurable relationship loading for optimized queries
- **Search Capabilities**: Full-text search and filtering
- **Batch Operations**: Efficient handling of multiple entities
- **Platform Integration**: Methods for linking tracks/playlists across platforms
- **Transaction Safety**: Context managers for transaction boundaries

## Data Model Relationships
The database schema includes complex relationships that model music library organization:

- **One-to-Many**: Tracks belong to Albums, Images belong to Tracks
- **Many-to-Many**: Tracks in Playlists, Tracks with Genres/Tags
- **Self-Referential**: Playlists can contain other Playlists (folder structure)
- **Cross-Platform Links**: TrackPlatformInfo connects local tracks to platform-specific entities

## SQLAlchemy Usage
Selecta uses modern SQLAlchemy 2.0-style type hints and patterns:

- **Mapped Columns**: `Mapped[Type]` annotations for type safety
- **Relationship Loading**: Strategic use of eager loading with joinedload
- **Query Building**: Composable query construction
- **Session Management**: Context managers for transaction safety

## Migrations
Database schema evolution is managed through Alembic:

- **Version Control**: Sequentially numbered migration scripts
- **Upgrade/Downgrade**: Bidirectional migration support
- **Schema Checks**: Validation of database structure during initialization
- **Data Preservation**: Migration logic to ensure data continuity

## Dependencies
- **Internal**:
  - core.utils for path handling and type helpers
  - core.utils.type_helpers for type conversion and safety
- **External**:
  - SQLAlchemy for ORM and database access
  - Alembic for database migrations
  - Loguru for logging

## Common Tasks

### Adding a New Model
1. Define the model class in `models/db.py`
2. Add appropriate relationships to existing models
3. Create a migration script:
   ```bash
   alembic revision -m "add_new_model"
   ```
4. Implement the Repository class in `repositories/`

### Adding Fields to Existing Models
1. Update the model class in `models/db.py`
2. Create a migration script that alters the table
3. Update any affected repository methods
4. Update UI components that use the model

### Database Operations
```python
# Creating a track
track_repo = TrackRepository()
new_track = track_repo.create({
    "title": "Track Title",
    "artist": "Artist Name",
    "duration_ms": 240000
})

# Searching tracks
tracks, count = track_repo.search("query", limit=20, offset=0)

# Linking a track to a platform
track_repo.link_to_platform(track_id, "spotify", "spotify_track_id", metadata)
```

### Transaction Management
```python
# Using context manager for transaction safety
from selecta.core.data.database import session_scope

with session_scope() as session:
    # Operations within transaction
    track = Track(title="New Track", artist="New Artist")
    session.add(track)
    # Commit happens automatically if no exceptions
```

## Implementation Notes
- Uses SQLAlchemy 2.0 style with Mapped[] annotations
- SQLite-specific optimizations for better performance
- Follows repository pattern for data access
- Uses WAL journal mode for better concurrency
- Implements foreign key constraints for data integrity
- Uses eager loading for related entities to reduce queries

## Change History
- Initial schema implementation
- Added platform metadata fields with improved linking capabilities
- Added Image model for better artwork management
- Added Track quality fields for user ratings
- Optimized SQLite connection handling for better concurrency
- Enhanced repository pattern with generic base class and type safety
