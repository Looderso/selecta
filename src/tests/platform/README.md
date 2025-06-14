# Platform Testing Suite

This directory contains comprehensive tests for platform client interchangeability and compliance with the AbstractPlatform interface.

## Overview

The platform testing suite ensures that all platform implementations (Spotify, Rekordbox, YouTube, Discogs) work interchangeably while maintaining their platform-specific features and quirks.

## Test Architecture

### 1. Abstract Base Test Class (`base_platform_test.py`)

The `BasePlatformTest` class provides a common testing framework that all platform-specific tests inherit from. It ensures:

- **Interface Compliance**: All platforms implement the AbstractPlatform interface correctly
- **Method Signatures**: Method signatures match the abstract base class
- **Return Type Consistency**: Methods return consistent types across platforms
- **Error Handling**: Platforms handle errors consistently
- **Authentication Patterns**: Authentication flows work similarly

### 2. Platform-Specific Compliance Tests

Each platform has its own compliance test that inherits from `BasePlatformTest`:

- **`spotify/test_spotify_compliance.py`**: Tests Spotify-specific features while ensuring interface compliance
- **`rekordbox/test_rekordbox_compliance.py`**: Tests Rekordbox database integration and DJ-specific features
- **`youtube/test_youtube_compliance.py`**: Tests YouTube API integration and video-specific features
- **`discogs/test_discogs_compliance.py`**: Tests Discogs marketplace and vinyl collection features

### 3. Interchangeability Tests (`test_platform_interchangeability.py`)

Tests that platforms can be swapped without breaking functionality:

- **Cross-Platform Workflows**: Import from one platform, export to another
- **Sync Manager Compatibility**: PlatformSyncManager works with all platforms
- **Data Model Consistency**: Platform-specific data converts to common formats
- **Operation Equivalency**: Same operations work across all platforms

### 4. Authentication Consistency Tests (`test_authentication_consistency.py`)

Tests that authentication works consistently across all platforms:

- **Authentication State Management**: All platforms handle auth states the same way
- **Error Handling**: Authentication failures are handled consistently
- **Settings Integration**: All platforms integrate with SettingsRepository similarly
- **Authentication Independence**: Platform auth states don't interfere with each other

### 5. Comprehensive Test Runner (`test_all_platforms.py`)

Runs all tests together and provides additional cross-platform validation:

- **Interface Verification**: Ensures all platforms implement the same interface
- **Type Consistency**: Verifies return types are consistent
- **Error Consistency**: Validates error handling patterns
- **Integration Testing**: Tests platforms working together

## Running the Tests

### Run All Platform Tests
```bash
cd src/tests/platform
python test_all_platforms.py
```

### Run Specific Test Categories

**Platform Compliance Tests:**
```bash
pytest tests/platform/spotify/test_spotify_compliance.py -v
pytest tests/platform/rekordbox/test_rekordbox_compliance.py -v
pytest tests/platform/youtube/test_youtube_compliance.py -v
pytest tests/platform/discogs/test_discogs_compliance.py -v
```

**Interchangeability Tests:**
```bash
pytest tests/platform/test_platform_interchangeability.py -v
```

**Authentication Tests:**
```bash
pytest tests/platform/test_authentication_consistency.py -v
```

**All Platform Tests:**
```bash
pytest tests/platform/ -v
```

### Run Tests by Platform

**Spotify Only:**
```bash
pytest tests/platform/ -k spotify -v
```

**Rekordbox Only:**
```bash
pytest tests/platform/ -k rekordbox -v
```

**YouTube Only:**
```bash
pytest tests/platform/ -k youtube -v
```

**Discogs Only:**
```bash
pytest tests/platform/ -k discogs -v
```

## Test Coverage

### Core Interface Methods Tested
- `is_authenticated()` - Authentication status checking
- `authenticate()` - Authentication flow execution
- `get_all_playlists()` - Playlist retrieval
- `get_playlist_tracks(playlist_id)` - Track retrieval from playlists
- `search_tracks(query, limit)` - Track searching
- `create_playlist(name, description)` - Playlist creation
- `add_tracks_to_playlist(playlist_id, track_ids)` - Adding tracks to playlists
- `remove_tracks_from_playlist(playlist_id, track_ids)` - Removing tracks from playlists
- `import_playlist_to_local(playlist_id)` - Importing platform playlists
- `export_tracks_to_playlist(name, track_ids, existing_id)` - Exporting to platform playlists

### Platform-Specific Features Tested

**Spotify:**
- OAuth authentication flow
- Audio features integration
- Pagination handling
- Token refresh mechanism
- Rate limiting handling

**Rekordbox:**
- Database connection management
- File path handling
- BPM and key data
- Cue point information
- Audio quality metadata
- Database locking behavior

**YouTube:**
- Video details and duration parsing
- Thumbnail handling
- Playlist privacy settings
- Channel information
- API pagination
- Quota management

**Discogs:**
- Release details and vinyl formats
- Label and catalog information
- Tracklist handling
- Collection vs wantlist distinction
- Marketplace integration
- Image/artwork handling

### Cross-Platform Features Tested
- Playlist creation/syncing/importing across platforms
- Track matching between platforms
- Data model consistency
- Error handling uniformity
- Authentication independence
- Sync manager compatibility

## Test Data and Mocking

### Mock Data Structure
Each platform test provides realistic mock data that represents the platform's actual API responses:

- **Playlists**: Platform-specific playlist objects with required fields
- **Tracks**: Platform-specific track objects with metadata
- **Authentication**: Platform-specific auth tokens and credentials

### Authentication Mocking
Tests mock authentication at multiple levels:
- Platform API clients (spotipy, YouTube API, etc.)
- Custom authentication managers
- Database connections (for Rekordbox)
- Token storage and refresh

### API Mocking
All external API calls are mocked to ensure:
- Tests run offline
- Consistent test data
- No API rate limiting
- Reproducible results

## Adding New Platforms

To add tests for a new platform:

1. **Create Platform Directory**: `mkdir tests/platform/newplatform/`

2. **Create Compliance Test**: Inherit from `BasePlatformTest`:
```python
from tests.platform.base_platform_test import BasePlatformTest

class TestNewPlatformCompliance(BasePlatformTest):
    def get_platform_class(self):
        return NewPlatformClient

    def get_mock_settings(self):
        return {"newplatform_api_key": "test_key"}

    # Implement other required methods...
```

3. **Update Test Configurations**: Add platform to `PLATFORM_CONFIGS` in interchangeability tests

4. **Update Authentication Tests**: Add platform to `PLATFORM_AUTH_CONFIGS`

5. **Update Comprehensive Runner**: Add platform to `PLATFORM_TEST_CLASSES`

## Benefits of This Testing Strategy

### 1. **Interchangeability Assurance**
- Platforms can be swapped without breaking functionality
- Common interface ensures consistent behavior
- Cross-platform workflows are guaranteed to work

### 2. **Platform-Specific Feature Validation**
- Each platform's unique features are properly tested
- Quirks and special behaviors are validated
- Platform-specific optimizations are preserved

### 3. **Regression Prevention**
- Changes to one platform don't break others
- Interface changes are caught immediately
- Authentication changes are validated across all platforms

### 4. **Development Confidence**
- Developers can confidently modify platform code
- New platforms can be added with confidence
- Refactoring is safer with comprehensive test coverage

### 5. **Documentation Through Tests**
- Tests serve as documentation for platform behavior
- Expected data formats are clearly defined
- Authentication patterns are documented

## Maintenance

### When to Update Tests
- **New Platform Methods**: Add tests for new AbstractPlatform methods
- **Platform API Changes**: Update mock data to match new API responses
- **Authentication Changes**: Update authentication mocks and flows
- **New Platform Addition**: Follow the "Adding New Platforms" guide

### Test Maintenance Guidelines
- Keep mock data realistic and up-to-date with actual API responses
- Ensure all platforms are tested equally (same number of test cases)
- Update test configurations when adding new platforms
- Maintain consistent error handling expectations across platforms
