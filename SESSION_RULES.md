# SESSION_RULES.md

This file contains session-specific rules and instructions for Claude Code to follow when working on the Selecta project.

## Current Session Focus

Fix and enhance the audio player to work with local files and other platforms. The audio player should be able to play:

1. Local tracks via file paths when available
2. YouTube tracks via streaming
3. Spotify tracks when supported

## Token Optimization Rules

1. **Documentation-First Approach**
   - Always consult documentation before reading code files
   - Follow the documentation hierarchy (top-level → module → component)
   - Use CODE_INDEX.md as your primary navigation tool
   - Only read code files after understanding their context through documentation

2. **Search Optimization**
   - Avoid broad searches across the entire codebase
   - Use targeted searches based on documentation guidance
   - Search within specific files or directories identified by documentation
   - Prefer navigating through documentation links over search operations

3. **File Reading Strategy**
   - Read only the files necessary for your task
   - Focus on relevant sections rather than entire files
   - Use documentation to identify the specific components you need
   - Scan file structure and imports before reading the entire content

4. **Batch Operations**
   - Use BatchTool to run multiple operations in parallel
   - Group related file reads to minimize context switching
   - Combine related edits into a single message when possible
   - Make multiple small, focused changes rather than large, sweeping ones

5. **Code Comprehension**
   - Understand the architecture through documentation first
   - Look for patterns and conventions in similar code
   - Focus on interfaces and public APIs before implementation details
   - Use documentation to understand component relationships

## Documentation and File Access Workflow

1. Start by consulting these top-level guides:
   - CLAUDE.md: General project information and token optimization strategy
   - CODE_INDEX.md: Quick reference to find key files and documentation
   - SESSION_RULES.md (this file): Session-specific rules

2. Once you identify the relevant module, check the module documentation:
   - Each module has a README.md file with detailed information
   - Module READMEs help locate specific files for particular functionality
   - Read module documentation completely before examining any code

3. File access sequence:
   - Use CODE_INDEX.md to locate the relevant module
   - Check module README.md for architecture and component understanding
   - Review sub-module README.md for specific component details
   - Only then start reading and modifying actual code files
   - Use precise, targeted searches based on documentation guidance

4. After making changes, update documentation:
   - Update any affected module README.md files when component functionality changes
   - Update CODE_INDEX.md if new files or major structural changes are made
   - Document significant changes in the Change History section of relevant README.md files
   - Ensure your changes are consistent with the documented architecture and patterns

## Session-Specific Rules

### Audio Player Enhancement Plan

1. **✅ Fix Current Local Audio Player**
   - ✅ Debug and fix any issues with the current implementation
   - ✅ Ensure it correctly plays local files when they exist
   - ✅ Implement proper error handling for missing files

2. **✅ Implement YouTube Audio Player**
   - ✅ Create a YouTubePlayer opening in a standalone window
   - ✅ Use YouTube iframe API to play videos
   - ✅ Handle authentication and proper error states

3. **✅ Add Factory Pattern Improvements**
   - ✅ Enhance AudioPlayerFactory to detect the correct player for a track
   - ✅ Update player switching based on track platform
   - ✅ Add proper type annotations and error handling

4. **✅ Improve UI Integration**
   - ✅ Update AudioPlayerComponent to handle different player types
   - ✅ Add visual indicators for track source (LOCAL, YOUTUBE, SPOTIFY)
   - ✅ Implement seamless switching between player backends

5. **✅ Implement Platform Integration for Tracks**
   - ✅ Create SpotifyAudioPlayer for playing preview URLs with QMediaPlayer
   - ✅ Add "Open in Platform" button to launch native apps
   - ✅ Play local files when available, otherwise open in native app
   - ✅ Handle track detection and platform URL generation

6. **Platform-Specific Features**
   - Add platform-specific controls where appropriate
   - Implement caching for YouTube streams if possible
   - Support quality selection where applicable

## Code Style Rules

- Follow Python type hints strictly
- Maintain consistent error handling patterns
- Use SQLAlchemy 2.0 style for database operations

## Testing Requirements

- Visually verify audio playback functionality
- Test with various track sources (local, YouTube)
- Ensure proper error handling for edge cases

## Implementation Strategy

1. ✅ Debug and fix the local audio player
2. ✅ Implement YouTube player in a standalone window
3. ✅ Update the factory pattern to support multiple player types
4. ✅ Enhance the UI component to work with all player types
5. ✅ Implement platform integration for tracks:
   - ✅ QMediaPlayer for preview URLs and local files
   - ✅ Open in native app (Spotify, YouTube) for full tracks
   - ✅ Auto-detect track type and handle appropriately
6. Add remaining platform-specific features as needed
