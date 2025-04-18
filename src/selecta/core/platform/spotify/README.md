# Spotify Platform Integration Documentation

## Overview
The Spotify integration connects Selecta with the Spotify Web API, allowing users to import playlists, search for tracks, and synchronize their Spotify library with the local database. It implements the AbstractPlatform interface to provide a standardized way of interacting with Spotify within the application.

## Architecture
The Spotify integration follows a layered architecture:

1. **Authentication Layer**:
   - `SpotifyAuthManager` handles OAuth2 flow and token management
   - Securely stores and refreshes access tokens
   - Manages authorization scopes

2. **API Client Layer**:
   - `SpotifyClient` implements the AbstractPlatform interface
   - Handles API communication via the spotipy library
   - Converts between Spotify API objects and local models

3. **Model Layer**:
   - `SpotifyModels` defines Spotify-specific data structures
   - Provides conversion methods to/from local database models
   - Standardizes Spotify API responses

4. **Synchronization Layer**:
   - `SpotifySync` contains logic for importing/exporting playlists and tracks
   - Handles playlist and track mapping between Spotify and local database
   - Manages metadata synchronization

## Components

### SpotifyAuthManager
- **File**: `auth.py`
- **Purpose**: Manages OAuth2 authentication with Spotify
- **Features**:
  - OAuth2 authorization code flow
  - Token refresh management
  - Authorization scope configuration
  - Credential storage and retrieval
  - Validation of authentication status

### SpotifyClient
- **File**: `client.py`
- **Purpose**: Core client implementing AbstractPlatform for Spotify
- **Features**:
  - Authentication status checking
  - Playlist operations (create, modify, list)
  - Track operations (search, get details)
  - User profile information
  - Playlist import/export for synchronization
  - Synchronization logic for playlists and tracks

### SpotifyModels
- **File**: `models.py`
- **Purpose**: Data models for Spotify entities
- **Key Models**:
  - `SpotifyTrack`: Represents a Spotify track with all metadata
  - `SpotifyPlaylist`: Represents a Spotify playlist with metadata
  - `SpotifyAlbum`: Represents album information from Spotify
  - Conversion methods to/from local database models

## API Scope and Capabilities

### Authentication Scopes
The Spotify integration requires the following OAuth scopes:
- `playlist-read-private`: Read access to user's private playlists
- `playlist-read-collaborative`: Read access to collaborative playlists
- `playlist-modify-public`: Write access to public playlists
- `playlist-modify-private`: Write access to private playlists
- `user-library-read`: Read access to user's saved tracks/albums
- `user-read-email`: Access to user's email for identification

### Supported Features
1. **Playlist Management**:
   - List all user playlists (including private and collaborative)
   - Create new playlists
   - Add/remove tracks from playlists
   - Modify playlist details

2. **Track Operations**:
   - Search for tracks by various criteria
   - Get detailed track information
   - Get track audio features (tempo, key, etc.)
   - Get related album details

3. **Synchronization**:
   - Import Spotify playlists to local database
   - Export local playlists to Spotify
   - Link local tracks to Spotify tracks
   - Update metadata bidirectionally

4. **Artwork and Images**:
   - Get track/album artwork in various sizes
   - Import artwork to local database

## Data Flow

### Importing a Spotify Playlist
1. `SpotifyClient.import_playlist_to_local()` is called
2. Client fetches playlist metadata and tracks from Spotify API
3. Playlist details are converted to local model format
4. Tracks are converted to local model format
5. Platform-specific IDs and URIs are preserved for future syncing
6. All data is passed to PlatformSyncManager for database storage
7. Track and album artwork is fetched and stored

### Searching for Tracks
1. `SpotifyClient.search_tracks()` is called with query string
2. Client sends search request to Spotify API
3. Results are converted to SpotifyTrack objects
4. Metadata is extracted and standardized
5. Results are returned for display or further processing

## Implementation Details

### Connection Management
- Uses spotipy as the underlying Spotify API client library
- Implements proper error handling for API failures and rate limits
- Handles token refresh automatically when needed
- Uses connection pooling for efficient API usage

### Token Storage
- Authentication tokens are stored securely in the database
- Refresh tokens are used to obtain new access tokens when expired
- Token encryption can be implemented for additional security

### Error Handling
- Translation of Spotify API errors to application-level errors
- Retry logic for transient failures
- Graceful handling of authentication issues

### Optimization
- Intelligent caching of API responses to reduce calls
- Batch operations where possible (e.g., adding multiple tracks to a playlist)
- Pagination handling for large datasets

## Dependencies
- **Internal**:
  - `core.data.repositories`: For storing credentials and linked tracks
  - `core.utils.caching`: For API response caching
- **External**:
  - `spotipy`: Python client library for Spotify Web API
  - `requests`: For direct HTTP operations (when needed)

## Usage Examples

### Authentication
```python
# Create authentication manager
auth_manager = SpotifyAuthManager(settings_repo)

# Start the authentication flow (will open browser for OAuth)
success = auth_manager.start_auth_flow()

# Use the client with authentication
client = SpotifyClient(settings_repo)
if client.is_authenticated():
    # Authenticated operations...
```

### Playlist Operations
```python
# Get all user playlists
playlists = client.get_all_playlists()

# Get tracks for a specific playlist
tracks = client.get_playlist_tracks("playlist_id")

# Create a new playlist
new_playlist = client.create_playlist(
    name="My New Playlist",
    description="Created with Selecta"
)

# Add tracks to a playlist
client.add_tracks_to_playlist(
    playlist_id="playlist_id",
    track_ids=["spotify:track:id1", "spotify:track:id2"]
)
```

### Search and Track Information
```python
# Search for tracks
results = client.search_tracks("artist name song title", limit=20)

# Get detailed track information
track = client.get_track_by_id("track_id")

# Get audio features
features = client.get_audio_features("track_id")
```

### Import/Export
```python
# Import a playlist from Spotify to local database
playlist, tracks = client.import_playlist_to_local("playlist_id")

# Export a local playlist to Spotify
spotify_id = client.export_tracks_to_playlist(
    playlist_name="Exported Playlist",
    track_ids=local_track_ids
)
```

## Troubleshooting

### Common Issues
1. **Authentication failures**:
   - Check that client ID and secret are correct
   - Verify that required scopes are approved
   - Check for expired tokens and refresh issues

2. **API rate limiting**:
   - Implement exponential backoff for retries
   - Use caching to reduce API calls
   - Batch operations where possible

3. **Data consistency**:
   - Handle track availability differences between regions
   - Account for Spotify content restrictions
   - Manage playlist ownership permissions

## Best Practices
- Always check authentication status before performing operations
- Handle token expiration gracefully
- Cache results when making repeated API calls
- Use batch operations for efficiency
- Implement proper error handling for all API operations
- Preserve Spotify IDs and URIs for future syncing

## Extending the Spotify Integration
- Adding new API endpoints: Extend SpotifyClient with new methods
- Supporting new metadata: Update SpotifyModels with new fields
- Enhancing synchronization: Modify SpotifySync with additional logic
- Improving search: Add specialized search methods for different criteria
