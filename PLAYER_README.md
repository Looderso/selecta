# Audio Player Enhancements

This document provides an overview of the enhancements made to the Selecta audio player component to support multiple platforms.

## Overview

The audio player system was redesigned to provide dedicated playback experiences for different content types:
- Local files are played directly in the application using the embedded audio player
- YouTube videos are played in a separate window with an embedded web player

This architecture provides a better user experience by using the appropriate player for each content type.

## Key Components Updated

### 1. Core Backend (`audio_player.py`)
- Maintained `AbstractAudioPlayer` as the base class for all audio players
- Enhanced the `LocalAudioPlayer` implementation for local files
- Removed the YouTube audio-only implementation in favor of a dedicated video player
- Simplified the `AudioPlayerFactory` to focus on audio-only playback
- Established clear separation between audio-only and video content

### 2. UI Components
- **Audio Player** (`audio_player_component.py`)
  - Updated to detect YouTube content and launch the dedicated YouTube player
  - Maintained platform label in the UI to indicate content type (LOCAL, YOUTUBE)
  - Improved error handling and user feedback
  - Added YouTube content detection with multiple fallback methods

- **YouTube Player** (`youtube_player.py`)
  - New dedicated window for YouTube video playback
  - Uses embedded YouTube player via WebEngine
  - Provides full video experience rather than audio-only
  - Launches in a separate window when YouTube content is selected

### 3. Dependencies
- Added `PyQt6-WebEngine` dependency for the YouTube embedded player
- Updated imports to ensure WebEngine is properly initialized

## Usage

The player automatically detects the appropriate playback method based on the track's properties:

1. **Local Files**: For tracks with a `local_path` attribute, content plays in the embedded audio player
2. **YouTube Videos**: For tracks with a `youtube_id` attribute or YouTube-specific metadata, a dedicated YouTube player window opens

Example usage remains the same - simply call the `load_track()` method with any supported track object:

```python
# Local track
player.load_track(local_track)  # Will use LocalAudioPlayer

# YouTube track
player.load_track(youtube_track)  # Will open YouTube player window
```

## Technical Implementation Details

### YouTube Player Window

The YouTube player uses PyQt6's WebEngine to embed an iframe with the YouTube player:

```python
# Create the YouTube player window
youtube_window = create_youtube_player_window(video_id, parent_window)
```

The player uses the YouTube iframe API with the following features:
- Autoplay enabled for immediate playback when opened
- Clean shutdown when the window is closed
- Proper icon and window title with the video ID

### Content Type Detection

Multiple methods are used to identify YouTube content:
- Direct properties like `video_id` or `youtube_id`
- Platform-specific metadata via `platform_info`
- Dynamic attribute inspection as a fallback

## Future Enhancements

1. **Spotify Integration**: Add a Spotify Web Player window for premium users
2. **Playback Controls**: Add custom controls for the YouTube player window (pause, volume, etc.)
3. **Window Management**: Remember window position and size between sessions
4. **Quality Selection**: Add UI controls for selecting YouTube video quality
5. **Playlist Navigation**: Add previous/next track controls for playlist navigation

## Dependencies

The YouTube player requires the PyQt6 WebEngine:

```
pip install PyQt6-WebEngine
```

Or update your project dependencies with:

```
pip install -e .
```

## Handling YouTube Embedding Restrictions

Some YouTube videos have embedding restrictions and cannot be played directly in the application. The player handles this situation in the following ways:

1. **Error Detection**:
   - Multiple error detection methods check for embedding restrictions
   - JavaScript console errors are monitored
   - Page content is analyzed for error messages
   - Load status is tracked with proper error handling

2. **User Feedback**:
   - Toast notification appears when embedding is restricted
   - The toast includes a clickable link to watch the video on YouTube
   - The application UI updates to show the embedding restriction
   - The YouTube player window automatically closes after showing the error

3. **Direct YouTube Option**:
   - Clicking the toast notification opens the video directly on YouTube
   - Uses the system's default browser for maximum compatibility
   - The direct YouTube URL includes the specific video ID for immediate playback

## Known Issues

- The WebEngine module must be properly initialized before creating a QApplication instance
- Some YouTube videos might not be playable due to embedding restrictions, but the user is provided with alternatives
- YouTube's embedding policies change over time, requiring periodic updates to the error detection logic
