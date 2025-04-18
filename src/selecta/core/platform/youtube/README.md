# YouTube Platform Integration Documentation

## Overview

The YouTube integration connects Selecta with YouTube's API, allowing users to access music videos, create playlists, and synchronize YouTube content with the local music library. This integration enables visualization of music through videos and provides an alternative platform for music discovery and organization.

## Architecture

The YouTube integration follows a layered architecture:

1. **Authentication Layer**:
   - `YouTubeAuth` handles OAuth2 authentication with Google API
   - Manages token storage, refresh, and validation
   - Configures required API scopes

2. **API Client Layer**:
   - `YouTubeClient` implements the AbstractPlatform interface
   - Handles API communication using Google API client libraries
   - Performs video search, playlist management, and content access

3. **Model Layer**:
   - `YouTubeModels` defines data structures for YouTube entities
   - Converts between YouTube API responses and local models
   - Handles video-specific metadata

4. **Synchronization Layer**:
   - `YouTubeSync` specializes in synchronizing YouTube playlists with local database
   - Handles metadata extraction from videos
   - Manages the relationship between music tracks and videos

## Components

### YouTubeAuth

- **File**: `auth.py`
- **Purpose**: Manages OAuth2 authentication with Google API
- **Features**:
  - OAuth2 authorization flow with Google
  - Token storage and automatic refresh
  - API scope configuration
  - Credential validation and verification

### YouTubeClient

- **File**: `client.py`
- **Purpose**: Core client implementing AbstractPlatform for YouTube
- **Features**:
  - Video search and retrieval
  - Playlist management (create, read, update, delete)
  - Channel interaction
  - Adaptation of YouTube concepts to Selecta's model

### YouTubeModels

- **File**: `models.py`
- **Purpose**: Data models for YouTube entities
- **Key Models**:
  - `YouTubeVideo`: Represents a video with music metadata
  - `YouTubePlaylist`: Represents a YouTube playlist
  - `YouTubeChannel`: Represents a channel (artist/label equivalent)
  - Conversion methods to/from local database models

### YouTubeSync

- **File**: `sync.py`
- **Purpose**: Specialized synchronization logic for YouTube
- **Features**:
  - Playlist import/export between YouTube and local database
  - Metadata extraction from video titles and descriptions
  - Thumbnail and preview image handling
  - Handling of YouTube-specific content restrictions

## YouTube Data Model Adaptation

### Videos as Tracks

YouTube videos are represented as tracks in Selecta:

- Video metadata is mapped to track attributes
- Thumbnails are used as track artwork
- Duration and other properties are preserved
- Video IDs and URLs are stored for direct access

### YouTube Playlists

YouTube playlists are represented natively:

- Playlist metadata (title, description) is preserved
- Video ordering within playlists is maintained
- Public/private/unlisted status is respected
- Playlist thumbnails are imported as artwork

## API Integration

### YouTube API Endpoints

The integration primarily uses YouTube Data API v3:

- `/search`: Find videos, channels, playlists
- `/playlists`: Manage playlists
- `/playlistItems`: Manage videos within playlists
- `/videos`: Get detailed video information
- `/channels`: Get channel information

### Authentication Scopes

The OAuth2 authentication requires these scopes:

- `youtube.readonly`: Read access to YouTube data
- `youtube`: Full access to manage YouTube account
- `youtube.force-ssl`: Secure access to YouTube API

### Quota Management

YouTube API has strict quota limitations:

- Daily quota allocation is limited (typically 10,000 units)
- Different operations consume different quota amounts
- The integration implements quota-aware operations and caching

## Data Flow

### Importing a YouTube Playlist

1. `YouTubeClient.import_playlist_to_local()` is called
2. Client fetches playlist metadata from YouTube API
3. Client fetches all videos in the playlist (with pagination)
4. Video metadata is extracted and converted to track format
5. Thumbnails are downloaded and stored as artwork
6. Playlist and videos are saved to local database with YouTube IDs

### Searching for Music Videos

1. `YouTubeClient.search_tracks()` is called with query string
2. Client sends search request to YouTube API with music category filter
3. Results are fetched with pagination if needed
4. Video information is converted to track format
5. Results are returned for display or further processing

### Creating YouTube Playlist

1. `YouTubeClient.create_playlist()` is called with playlist details
2. Client creates new playlist via YouTube API
3. If specified, videos are added to the playlist
4. Playlist metadata is returned for synchronization
5. Local reference is created for future updates

## Implementation Details

### Metadata Extraction

- Intelligent parsing of video titles to extract artist and track info
- Utilization of video description for additional metadata
- Category and tag analysis for genre identification
- Duration and publication date extraction

### Quota Optimization

- Strategic caching of responses to reduce API calls
- Batch operations for playlist management
- Partial resource requests (fields parameter) to minimize quota usage
- Pagination handling with appropriate page sizes

### Content Restrictions

- Handling region-restricted videos
- Age restriction detection and management
- Copyright claim and muted content identification
- Alternative video suggestion for restricted content

## Dependencies

- **Internal**:
  - `core.data.repositories`: For storing YouTube metadata
  - `core.utils.cache_manager`: For API response caching
- **External**:
  - `google-api-python-client`: Official Google API client
  - `google-auth-oauthlib`: For OAuth flow
  - `google-auth-httplib2`: For authenticated HTTP

## Usage Examples

### Authentication

```python
# Create auth manager
auth_manager = YouTubeAuth(settings_repo)

# Start the authentication flow (will open browser for OAuth)
success = auth_manager.start_auth_flow()

# Use the client with authentication
client = YouTubeClient(settings_repo)
if client.is_authenticated():
    # Authenticated operations...
```

### Playlist Operations

```python
# Get all user playlists
playlists = client.get_all_playlists()

# Get videos for a specific playlist
videos = client.get_playlist_tracks(playlist_id)

# Create a new playlist
new_playlist = client.create_playlist(
    name="My Music Videos",
    description="Created with Selecta",
    privacy_status="private"
)

# Add videos to a playlist
client.add_tracks_to_playlist(
    playlist_id=playlist_id,
    track_ids=["youtube_video_id1", "youtube_video_id2"]
)
```

### Search Operations

```python
# Search for music videos
results = client.search_tracks("artist name song title", limit=20)

# Search with additional filters
filtered_results = client.search_tracks(
    "artist name",
    video_category="Music",
    order="viewCount",
    limit=10
)

# Get video details
video = client.get_track_by_id(video_id)
```

### Import/Export

```python
# Import a YouTube playlist to local database
playlist, tracks = client.import_playlist_to_local(playlist_id)

# Export a local playlist to YouTube
youtube_id = client.export_tracks_to_playlist(
    playlist_name="Exported from Selecta",
    track_ids=local_track_ids,
    description="Music playlist exported from Selecta"
)
```

## Troubleshooting

### Common Issues

1. **Authentication failures**:
   - OAuth2 token expiration or revocation
   - Insufficient permissions/scopes requested
   - Google API project configuration issues

2. **Quota limitations**:
   - Daily quota exceeded
   - Too many requests in short time period
   - High-cost operations depleting quota

3. **Content availability**:
   - Region-restricted videos not available
   - Copyright blocked or removed content
   - Age-restricted content requiring additional authentication

4. **Metadata quality**:
   - Inconsistent video titles affecting parsing
   - Missing or incorrect information in video details
   - User-generated content with non-standard formatting

## Best Practices

- Always check authentication before performing operations
- Monitor quota usage and implement adaptive throttling
- Cache search results and video metadata when possible
- Batch operations for playlist management
- Handle pagination properly for large playlists
- Implement fallback strategies for restricted content
- Use music-specific search parameters for better results

## Extending the YouTube Integration

- Adding channel subscriptions: Follow artists and labels
- Implementing live stream support: For music performances
- Enhancing metadata extraction: More sophisticated title parsing
- Supporting user engagement: Comments, likes, and watch history
- Adding upload capabilities: For creating music videos
