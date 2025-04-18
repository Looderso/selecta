# Discogs Platform Integration Documentation

## Overview
The Discogs integration connects Selecta with the Discogs music database and marketplace, focusing on vinyl record collections and wantlists. Unlike other music platform integrations, Discogs is primarily oriented towards physical media catalogs rather than digital streaming services, providing unique metadata about physical releases, pressings, and vinyl-specific information.

## Architecture
The Discogs integration follows a layered architecture:

1. **API Client Layer**:
   - `DiscogsApiClient` handles direct communication with Discogs API
   - Implements rate limiting and pagination
   - Manages request authentication and signing

2. **Authentication Layer**:
   - `DiscogsAuth` handles OAuth1 authentication flow
   - Manages token storage and refresh
   - Provides authentication validation

3. **Client Layer**:
   - `DiscogsClient` implements the AbstractPlatform interface
   - Adapts Discogs concepts (collection, wantlist) to Selecta's playlist model
   - Provides search and metadata access

4. **Model Layer**:
   - `DiscogsModels` defines data structures for Discogs entities
   - Converts between Discogs API responses and local models
   - Handles vinyl-specific metadata

5. **Matching Layer**:
   - `VinylMatcher` provides specialized matching algorithms for vinyl records
   - Links digital tracks to their vinyl counterparts
   - Uses release metadata for accurate matching

## Components

### DiscogsApiClient
- **File**: `api_client.py`
- **Purpose**: Low-level client for Discogs API
- **Features**:
  - HTTP request handling with OAuth1 authentication
  - Rate limit management and throttling
  - Response parsing and error handling
  - Pagination for large result sets

### DiscogsAuth
- **File**: `auth.py`
- **Purpose**: Manages OAuth1 authentication with Discogs
- **Features**:
  - OAuth1 authentication flow
  - Token storage and retrieval
  - Authentication status validation
  - Credential management

### DiscogsClient
- **File**: `client.py`
- **Purpose**: Core client implementing AbstractPlatform for Discogs
- **Features**:
  - High-level operations for collection and wantlist
  - Search functionality for releases and masters
  - User profile information access
  - Adaptation of Discogs concepts to Selecta's model
  - Vinyl record matching algorithms
  - Collection and wantlist synchronization
  - Release metadata import
  - Vinyl-specific metadata preservation
  - Artwork and label information handling

### DiscogsModels
- **File**: `models.py`
- **Purpose**: Data models for Discogs entities
- **Key Models**:
  - `DiscogsRelease`: Represents a physical release
  - `DiscogsTrack`: Represents a track on a release
  - `DiscogsArtist`: Represents an artist
  - `DiscogsLabel`: Represents a record label
  - Conversion methods to/from local database models

## Discogs Data Model Adaptation

### Collection as Playlist
The Discogs user collection is represented as a virtual playlist in Selecta:
- Collection items become tracks in the playlist
- Release metadata is preserved with vinyl-specific details
- Album artwork is imported from release images

### Wantlist as Playlist
The Discogs wantlist is represented as another virtual playlist:
- Wanted items appear as tracks with special status
- Used for tracking desired vinyl releases
- Can be used to create shopping lists

### Release Structure
Discogs organizes music differently than digital platforms:
- **Release**: Physical product (specific pressing of an album)
- **Master**: Abstract release (the album itself, regardless of pressing)
- **Artist**: Creator of the music
- **Label**: Company that released the music
- **Track**: Individual song on a release

## API Integration

### Discogs API Endpoints
The integration uses several Discogs API endpoints:
- `/users/{username}/collection`: User's collection items
- `/users/{username}/wants`: User's wantlist items
- `/database/search`: Search for releases, masters, artists
- `/releases/{id}`: Get detailed release information
- `/masters/{id}`: Get master release information
- `/artists/{id}`: Get artist information

### Authentication Scopes
The OAuth1 authentication requires these permissions:
- `collection_read`: Access to user's collection
- `collection_write`: Ability to modify collection (add/remove items)
- `wantlist_read`: Access to user's wantlist
- `wantlist_write`: Ability to modify wantlist

### Rate Limiting
Discogs API has strict rate limits:
- 60 requests per minute for authenticated requests
- 25 requests per minute for unauthenticated requests
- The integration implements automatic throttling and retry

## Data Flow

### Importing Collection as Playlist
1. `DiscogsClient.get_all_playlists()` includes collection as virtual playlist
2. When user imports this playlist, `import_playlist_to_local()` is called
3. Client fetches all collection items from Discogs API
4. Release information is converted to tracks
5. Vinyl-specific metadata is preserved
6. Collection items are stored in local database as a playlist

### Searching for Vinyl
1. `DiscogsClient.search_tracks()` is called with query string
2. Client sends search request to Discogs API
3. Results are fetched with pagination if needed
4. Release information is converted to track format
5. Results are returned for display or matching

### Matching Digital to Vinyl
1. `VinylMatcher.find_matches()` is called with digital track info
2. Matcher generates search queries based on track metadata
3. Search results are scored based on multiple criteria
4. Best matches are returned with confidence scores
5. User can select correct match for linking

## Implementation Details

### Throttling and Rate Limiting
- Built-in rate limiter respects Discogs API constraints
- Implements adaptive throttling based on response headers
- Exponential backoff for retry on 429 errors
- Batching of requests to optimize within limits

### OAuth1 Authentication
- Uses OAuth1 protocol with request signing
- Handles token exchange and verification
- Stores credentials securely in database
- Implements proper token refresh and validation

### Vinyl-Specific Metadata
- Catalog numbers and release codes
- Pressing information and release country
- Matrix/runout etchings
- Format details (vinyl size, weight, color)
- Release date and pressing variants

## Dependencies
- **Internal**:
  - `core.data.repositories`: For storing vinyl metadata
  - `core.utils.cache_manager`: For API response caching
- **External**:
  - `requests_oauthlib`: For OAuth1 request handling
  - `requests`: For HTTP operations
  - `fuzzywuzzy`: For fuzzy string matching

## Usage Examples

### Authentication
```python
# Create auth manager
auth_manager = DiscogsAuth(settings_repo)

# Start the authentication flow (will open browser for OAuth)
success = auth_manager.start_auth_flow()

# Use the client with authentication
client = DiscogsClient(auth_manager)
if client.is_authenticated():
    # Authenticated operations...
```

### Collection and Wantlist
```python
# Get user's collection and wantlist (as playlist representations)
playlists = client.get_all_playlists()

# Get collection items
collection = next(p for p in playlists if p.name == "Collection")
collection_items = client.get_playlist_tracks(collection.id)

# Add item to collection
client.add_to_collection(release_id=1234567)

# Add item to wantlist
client.add_to_wantlist(release_id=7654321)
```

### Search Operations
```python
# Search for releases
results = client.search_tracks("artist name album title", limit=20)

# Get detailed release information
release = client.get_release(release_id=1234567)

# Search with vinyl-specific filters
vinyl_results = client.search_tracks(
    "artist name",
    format_filter="Vinyl",
    year=1978
)
```

### Vinyl Matching
```python
# Create vinyl matcher
matcher = VinylMatcher(discogs_client)

# Find vinyl matches for a digital track
matches = matcher.find_matches(
    artist="Artist Name",
    title="Track Title",
    album="Album Name",
    year=1984
)

# Match with catalog number (more precise)
catalog_matches = matcher.find_by_catalog_number("ABC-123-45")
```

## Troubleshooting

### Common Issues
1. **Authentication failures**:
   - OAuth1 token expiration or invalidation
   - Insufficient permissions requested during auth flow
   - API key/secret configuration issues

2. **Rate limiting**:
   - Too many requests in short time period
   - Not respecting Discogs rate limit headers
   - Inefficient API usage patterns

3. **Match quality issues**:
   - Limited metadata affecting match confidence
   - Multiple release variants causing ambiguity
   - Inconsistent naming conventions between platforms

## Best Practices
- Always check authentication before performing operations
- Respect Discogs API rate limits to avoid throttling
- Cache search results and release metadata when possible
- Use catalog numbers for more precise vinyl matching
- Handle pagination properly for large collections
- Preserve vinyl-specific metadata during synchronization

## Extending the Discogs Integration
- Adding marketplace integration: Price tracking and purchase history
- Improving matching algorithms: More sophisticated fuzzy matching
- Supporting community features: Reviews, contributions, submissions
- Enhancing metadata: Label and artist detailed information
