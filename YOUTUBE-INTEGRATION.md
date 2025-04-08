# YouTube Platform Integration

This document outlines the process of integrating YouTube as a new platform in Selecta, following the same architecture patterns as the existing Spotify, Rekordbox, and Discogs integrations.

## Implementation Plan

### Core Components

1. **Authentication (auth.py)**
   - OAuth flow using Google API client libraries
   - Token storage in database via SettingsRepository
   - Token refresh mechanism
   - Authentication status verification

2. **Data Models (models.py)**
   - `YouTubeVideo` - Representation of a YouTube video (equivalent to tracks)
   - `YouTubePlaylist` - Representation of a YouTube playlist
   - `YouTubeChannel` - Optional representation of a YouTube channel
   - Type definitions with TypedDict for API responses

3. **API Client (client.py)**
   - Implementation of `AbstractPlatform` interface
   - Methods for playlist operations
   - Methods for video operations
   - Search functionality

4. **Synchronization (sync.py)**
   - Import YouTube playlists to local database
   - Export local playlists to YouTube
   - Link videos between platforms

5. **Platform Factory Update**
   - Register YouTube in PlatformFactory
   - Update platform creation logic

### UI Components (Future)

1. **YouTube Data Provider**
   - Implementation of `PlaylistDataProvider` for YouTube
   - Adapter between UI and platform client

2. **YouTube UI Components**
   - YouTube playlist item component
   - YouTube video item component
   - YouTube search panel

## Development Phases

### Phase 1: Core Authentication & Models

- [x] Create `auth.py` for YouTube authentication
  - [x] OAuth flow implementation
  - [x] Token storage in database
  - [x] Token refresh functionality
- [x] Create `models.py` with data structures
  - [x] YouTube API response TypedDict definitions
  - [x] YouTubeVideo model
  - [x] YouTubePlaylist model
- [x] Basic `client.py` implementation
  - [x] Authentication methods
  - [x] Get playlists
  - [x] Get videos from playlist

### Phase 2: Core Platform Integration

- [x] Complete `client.py` implementation
  - [x] Create playlists
  - [x] Add/remove videos
  - [x] Search functionality
- [x] Implement `sync.py`
  - [x] Import playlists to local database
  - [x] Export local playlists to YouTube
- [x] Update `platform_factory.py`
  - [x] Register YouTube platform
- [x] Create basic tests

### Phase 3: UI Integration

- [x] Create `youtube_playlist_data_provider.py`
- [x] Create UI components
  - [x] YouTubePlaylistItem
  - [x] YouTubeVideoItem
- [x] Update import/export dialogs to include YouTube
- [x] Add YouTube search panel
- [x] Add YouTube platform to authentication panel

## Technical Specifications

### Authentication & Token Storage

- Use Google OAuth 2.0 for authentication
- Store tokens in database using SettingsRepository
- **Persistence**: Store the credentials in the database to avoid re-authentication each session
- Use the same schema as other platforms for consistency:
  ```python
  creds_data = {
      "client_id": self.client_id,
      "client_secret": self.client_secret,
      "access_token": token_info.get("access_token"),
      "refresh_token": token_info.get("refresh_token"),
      "token_expiry": expires_datetime,
  }
  ```

### Data Models Structure

YouTubeVideo model (similar to SpotifyTrack):
```python
@dataclass
class YouTubeVideo:
    id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    publish_date: datetime | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    added_at: datetime | None = None
```

YouTubePlaylist model:
```python
@dataclass
class YouTubePlaylist:
    id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    video_count: int
    privacy_status: str
    thumbnail_url: str | None = None
    published_at: datetime | None = None
```

### API Requirements

- YouTube Data API v3
- Required scopes:
  - `https://www.googleapis.com/auth/youtube`
  - `https://www.googleapis.com/auth/youtube.readonly`
  - `https://www.googleapis.com/auth/youtube.force-ssl`

### Implementation Notes

1. **API Quotas**: YouTube API has strict quota limitations (10,000 units per day). Design with quota efficiency in mind.
2. **Pagination**: Handle pagination for large playlists or search results.
3. **Error Handling**: Implement robust error handling for API failures.
4. **Rate Limiting**: Implement backoff strategies for rate limiting.

## Comparison with Other Platforms

| Feature | Spotify | YouTube | Notes |
|---------|---------|---------|-------|
| Auth    | OAuth 2.0 | OAuth 2.0 | Similar implementation |
| "Tracks" | Songs | Videos | Different metadata structure |
| Playlists | User & Followed | User & Followed | Similar structure |
| API Limits | High limits | Strict quotas | Need optimization for YouTube |
| Media Types | Audio | Video | Different media handling |

## Future Enhancements

1. Channel subscription import
2. Video recommendations
3. Integration with YouTube Music API
4. Enhanced metadata extraction from videos
5. Cross-platform linking (match YouTube music videos with Spotify tracks)
