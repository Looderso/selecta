# Database Models Documentation

## Overview
This directory contains SQLAlchemy model definitions that represent the core data entities in Selecta. These models map to database tables and define the relationships between different entities, forming the foundation of the application's data structure.

## Model Architecture
Selecta models follow SQLAlchemy 2.0's modern style with:
- Type annotations using `Mapped[Type]` for better type safety
- Relationship definitions with full type hinting
- Clear separation of model attributes and relationships
- Descriptive docstrings and method documentation

## Core Models

### Track-Related Models
- **Track**: Central entity representing a music track
  - Properties: title, artist, duration, year, bpm, quality rating
  - Relationships: album, platform_info, playlists, genres, tags, images
  - Methods: get_artwork, get_platform_metadata, update_from_platform

- **TrackPlatformInfo**: Platform-specific information for tracks
  - Links local tracks to their representation on Spotify, Rekordbox, Discogs, etc.
  - Stores platform-specific metadata as JSON
  - Tracks synchronization timing and update requirements

- **TrackAttribute**: Flexible storage for track attributes
  - Stores arbitrary key-value attributes for tracks
  - Used for properties like "energy", "danceability", etc.
  - Tracks source of attributes for provenance

### Organizational Models
- **Playlist**: Collection of tracks or other playlists (folders)
  - Supports hierarchical structure through parent/child relationships
  - Can represent both local playlists and imported platform playlists
  - Tracks ordering and display information

- **PlaylistTrack**: Association between playlists and tracks
  - Maintains track order within playlists
  - Stores playlist-specific track metadata

- **Album**: Represents music albums
  - Groups related tracks
  - Stores album metadata (artwork, year, etc.)

### Categorization Models
- **Genre**: Music genres for tracks
  - Many-to-many relationship with tracks
  - Tracks source of genre information

- **Tag**: User-defined or platform-specific tags
  - Many-to-many relationship with tracks and playlists
  - Flexible tagging system for organization

### Media and Metadata Models
- **Image**: Artwork for tracks and albums
  - Stores images in multiple sizes (thumbnail, small, medium, large)
  - Links to tracks or albums
  - Tracks image source

- **VinylRecord**: Discogs-specific vinyl information
  - Properties: catalog number, release date, format, etc.
  - Links to tracks for unified library integration

### Configuration Models
- **UserSettings**: Application settings and preferences
  - Key-value store for user configuration
  - Typed access to settings

- **PlatformCredentials**: Authentication for external platforms
  - Secure storage for API tokens and credentials
  - Platform-specific authentication data

## Relationship Types
The models use several types of SQLAlchemy relationships:

1. **One-to-Many**:
   - Album to Tracks
   - Track to Images

2. **Many-to-Many**:
   - Tracks to Genres (through track_genres)
   - Tracks to Tags (through track_tags)
   - Tracks to Playlists (through playlist_tracks)

3. **One-to-One**:
   - VinylRecord to Track

4. **Self-Referential**:
   - Playlist to child Playlists (for folders)

## Implementation Notes
- The `db.py` file contains all model definitions for easier imports
- SQLAlchemy relationship definitions include cascade behaviors
- Models use modern class attributes for fields and relationships
- UTC datetime used consistently for timestamps
- Complex models provide helper methods for common operations
- Many-to-many relationships use association tables

## Usage Examples

### Creating and Relating Models
```python
# Create an album
album = Album(name="Album Title", artist="Artist Name", year=2023)
session.add(album)

# Create a track related to the album
track = Track(
    title="Track Title",
    artist="Artist Name",
    album=album,
    duration_ms=240000
)
session.add(track)

# Add genre to track
genre = Genre(name="Electronic")
track.genres.append(genre)
session.add(genre)

# Link track to platform
platform_info = TrackPlatformInfo(
    track=track,
    platform="spotify",
    platform_id="spotify_track_id",
    platform_data=json.dumps({"uri": "spotify:track:123"})
)
session.add(platform_info)
```

### Working with Relationships
```python
# Get all tracks for an album
tracks = album.tracks

# Get all platforms a track exists on
platforms = [info.platform for info in track.platform_info]

# Check if track has a specific platform
has_spotify = any(info.platform == "spotify" for info in track.platform_info)

# Get all tracks in a genre
electronic_tracks = genre.tracks
```

## Best Practices
- Access models through repositories rather than directly
- Use SQLAlchemy's relationship loading strategies appropriately
- Define clear relationship cascades for proper deletion behavior
- Keep model methods focused on behavior directly related to the entity
- Use type annotations consistently for better IDE support
