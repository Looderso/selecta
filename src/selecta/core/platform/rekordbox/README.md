# Rekordbox Platform Integration Documentation

## Overview

The Rekordbox integration connects Selecta with Pioneer DJ's Rekordbox library, allowing users to import playlists, access track metadata, and synchronize their DJ collection with the local database. Unlike other integrations that connect to web APIs, the Rekordbox integration directly accesses the local Rekordbox database.

## Architecture

The Rekordbox integration follows a layered approach:

1. **Database Access Layer**:
   - Direct access to Rekordbox's SQLite database
   - Read-only operations to preserve Rekordbox data integrity
   - Schema-aware queries for different Rekordbox versions

2. **Authentication Layer**:
   - Simple authentication based on database path verification
   - Path management for different Rekordbox versions and locations
   - Non-OAuth method appropriate for local software

3. **Client Layer**:
   - `RekordboxClient` implements the AbstractPlatform interface
   - Provides playlist and track access methods
   - Handles DJ-specific metadata

4. **Synchronization Layer**:
   - `RekordboxSync` handles import/export between Rekordbox and local database
   - Preserves DJ-specific metadata (cue points, BPM, key, etc.)
   - Handles file path resolution for local audio files

## Components

### RekordboxClient

- **File**: `client.py`
- **Purpose**: Core client implementing AbstractPlatform for Rekordbox
- **Features**:
  - Rekordbox database connection management
  - Playlist and collection browsing
  - DJ metadata extraction
  - Track and playlist import functionality
  - Synchronization logic for playlists and tracks
  - File path resolution and validation
  - DJ-specific metadata preservation

### RekordboxAuth

- **File**: `auth.py`
- **Purpose**: Handles authentication via database path
- **Features**:
  - Automatic Rekordbox database discovery
  - Database validation and version detection
  - Path management for different OS environments

### RekordboxModels

- **File**: `models.py`
- **Purpose**: Data models for Rekordbox entities
- **Key Models**:
  - `RekordboxTrack`: Represents a Rekordbox track with DJ metadata
  - `RekordboxPlaylist`: Represents a Rekordbox playlist
  - `RekordboxFolder`: Represents a playlist folder structure
  - Conversion methods to/from local database models

## Database Integration

### Rekordbox Database Structure

The integration works with Rekordbox's SQLite database, focusing on these key tables:

- `djmdContent`: Main track information
- `djmdPlaylist`: Playlist definitions
- `djmdPlaylistContent`: Playlist-track associations
- `djmdProperty`: Track properties and analysis data
- `djmdSongPlaylist`: Smart playlist definitions
- `djmdCue`: Cue points and loop information

### Schema Compatibility

The integration handles different Rekordbox versions:

- Rekordbox 5.x: Legacy database schema
- Rekordbox 6.x: Current database schema with expanded metadata

### Access Patterns

- Read-only access to preserve Rekordbox data integrity
- Periodic reconnection to handle database locking
- Direct SQL queries optimized for performance
- SQLAlchemy integration for type safety and query building

## DJ-Specific Metadata

### Track Metadata

The integration preserves DJ-specific metadata in local tracks:

- Beat grid information (BPM, grid offset)
- Musical key detection
- Energy level and track color
- Track rating and comments
- Play count and date last played

### Performance Data

- Hot cue points and their names/colors
- Memory points for track navigation
- Loop points and saved loops
- Beat jump settings

## Data Flow

### Importing a Rekordbox Playlist

1. `RekordboxClient.import_playlist_to_local()` is called
2. Client queries Rekordbox database for playlist metadata and tracks
3. Playlist details are converted to local model format
4. Tracks are converted to local model format, preserving DJ metadata
5. Local audio files are located and verified
6. All data is passed to PlatformSyncManager for database storage

### Rekordbox Database Discovery

1. `RekordboxAuth.find_rekordbox_database()` searches standard locations
2. Validates database files by checking schema
3. Returns valid database path for client connection

## Implementation Details

### Connection Management

- Uses SQLAlchemy for type-safe database access
- Implements connection pooling for efficient database usage
- Handles database locking scenarios (when Rekordbox is running)
- Automatically reconnects if connection is lost

### File Path Resolution

- Maps Rekordbox file paths to local file system
- Handles different path formats between platforms
- Verifies file existence and accessibility
- Enables proper file linking for playback

### Schema Version Detection

- Detects Rekordbox database version from schema
- Adapts queries to match specific schema version
- Provides consistent data model regardless of version

## Dependencies

- **Internal**:
  - `core.data.repositories`: For storing track and playlist data
  - `core.utils.path_helper`: For file path resolution
- **External**:
  - `sqlalchemy`: For database access
  - `pyrekordbox`: Python library for Rekordbox database access (optional)

## Usage Examples

### Authentication

```python
# Initialize auth manager
auth_manager = RekordboxAuth()

# Find Rekordbox database (auto-discovery)
db_path = auth_manager.find_rekordbox_database()

# Or set specific path
auth_manager.set_database_path("/path/to/rekordbox.db")

# Create client with authentication
client = RekordboxClient(auth_manager)
```

### Playlist Operations

```python
# Get all playlists
playlists = client.get_all_playlists()

# Get tracks for a specific playlist
tracks = client.get_playlist_tracks("playlist_id")

# Import a playlist to local database
playlist, tracks = client.import_playlist_to_local("playlist_id")
```

### Track Operations

```python
# Get track details
track = client.get_track("track_id")

# Get DJ-specific metadata
cue_points = client.get_track_cue_points("track_id")
beat_grid = client.get_track_beat_grid("track_id")

# Search for tracks
results = client.search_tracks("track title", limit=20)
```

## Troubleshooting

### Common Issues

1. **Database access errors**:
   - Check if Rekordbox is currently running (may lock database)
   - Verify database path is correct
   - Check user permissions for database file

2. **File path resolution failures**:
   - Verify audio files exist at expected locations
   - Check for drive letter/mount point differences
   - Ensure consistent path formatting

3. **Version compatibility**:
   - Different Rekordbox versions have schema differences
   - Check for schema version detection and query adaptation

## Best Practices

- Always check authentication before performing operations
- Handle database locking scenarios gracefully (Rekordbox running)
- Perform read-only operations to preserve Rekordbox database integrity
- Cache results when possible to reduce database load
- Use the sync manager for complex operations instead of direct client usage

## Extending the Rekordbox Integration

- Adding support for new Rekordbox versions: Update schema detection
- Supporting additional metadata: Extend models and queries
- Improving performance: Optimize database queries and caching
- Adding export capabilities: Implement playlist/track export to Rekordbox
