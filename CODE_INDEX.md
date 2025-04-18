# CODE_INDEX.md

This file serves as a quick reference guide for common features and their implementations in the Selecta codebase. When working with this project, check this index first to identify the relevant files to edit.

## Application Overview
- Main Application Documentation: `src/selecta/README.md`

## Core Components

### Platform Integration
- AbstractPlatform: `src/selecta/core/platform/abstract_platform.py`
- PlatformSyncManager: `src/selecta/core/platform/sync_manager.py`
- PlatformFactory: `src/selecta/core/platform/platform_factory.py`
- LinkManager: `src/selecta/core/platform/link_manager.py`

### Data Module
- Main Documentation: `src/selecta/core/data/README.md`
- Models Documentation: `src/selecta/core/data/models/README.md`
- Repositories Documentation: `src/selecta/core/data/repositories/README.md`
- Migrations Documentation: `src/selecta/core/data/migrations/README.md`

### Data Models
- Database Models: `src/selecta/core/data/models/db.py`
- Data Types: `src/selecta/core/data/types.py`
- Database Schema: `src/selecta/core/data/database.py` and `src/selecta/core/data/init_db.py`

### Repositories
- Track Repository: `src/selecta/core/data/repositories/track_repository.py`
- Playlist Repository: `src/selecta/core/data/repositories/playlist_repository.py`
- Settings Repository: `src/selecta/core/data/repositories/settings_repository.py`
- Image Repository: `src/selecta/core/data/repositories/image_repository.py`
- Vinyl Repository: `src/selecta/core/data/repositories/vinyl_repository.py`

## Platform Integrations

### Platform Module
- Platform Module Documentation: `src/selecta/core/platform/README.md`

### Spotify
- Spotify Module Documentation: `src/selecta/core/platform/spotify/README.md`
- Client: `src/selecta/core/platform/spotify/client.py`
- Auth: `src/selecta/core/platform/spotify/auth.py`
- Models: `src/selecta/core/platform/spotify/models.py`
- UI Components: `src/selecta/ui/components/spotify/`

### Rekordbox
- Rekordbox Module Documentation: `src/selecta/core/platform/rekordbox/README.md`
- Client: `src/selecta/core/platform/rekordbox/client.py`
- Auth: `src/selecta/core/platform/rekordbox/auth.py`
- Models: `src/selecta/core/platform/rekordbox/models.py`
- UI Components: `src/selecta/ui/components/playlist/rekordbox/`

### Discogs
- Discogs Module Documentation: `src/selecta/core/platform/discogs/README.md`
- Client: `src/selecta/core/platform/discogs/client.py`
- API Client: `src/selecta/core/platform/discogs/api_client.py`
- Auth: `src/selecta/core/platform/discogs/auth.py`
- Models: `src/selecta/core/platform/discogs/models.py`
- UI Components: `src/selecta/ui/components/discogs/`

### YouTube
- YouTube Module Documentation: `src/selecta/core/platform/youtube/README.md`
- Client: `src/selecta/core/platform/youtube/client.py`
- Auth: `src/selecta/core/platform/youtube/auth.py`
- Models: `src/selecta/core/platform/youtube/models.py`
- Sync: `src/selecta/core/platform/youtube/sync.py`
- UI Components: `src/selecta/ui/components/youtube/`

## UI Components

### Module Documentation
- UI Module: `src/selecta/ui/README.md`
- Components Module: `src/selecta/ui/components/README.md`
- Playlist Components: `src/selecta/ui/components/playlist/README.md`
- Themes Module: `src/selecta/ui/themes/README.md`
- Widgets Module: `src/selecta/ui/widgets/README.md`
- Dialogs: `src/selecta/ui/dialogs/README.md`

### Playlist Components
- Playlist Component: `src/selecta/ui/components/playlist/playlist_component.py`
- PlaylistDataProvider: `src/selecta/ui/components/playlist/playlist_data_provider.py`
- Playlist Tree Model: `src/selecta/ui/components/playlist/playlist_tree_model.py`
- Tracks Table Model: `src/selecta/ui/components/playlist/tracks_table_model.py`
- Track Details Panel: `src/selecta/ui/components/playlist/track_details_panel.py` (includes metadata editing with platform integration)

### Player Components
- Audio Player: `src/selecta/ui/components/player/audio_player_component.py`
- Audio Player Backend: `src/selecta/core/utils/audio_player.py`

### Main UI Structure
- App: `src/selecta/ui/app.py`
- Main Content: `src/selecta/ui/components/main_content.py`
- Navigation Bar: `src/selecta/ui/components/navigation_bar.py`
- Side Drawer: `src/selecta/ui/components/side_drawer.py`
- Dynamic Content: `src/selecta/ui/components/dynamic_content.py`
- Theme Management: `src/selecta/ui/themes/`

### Dialogs
- Create Playlist: `src/selecta/ui/create_playlist_dialog.py`
- Import Rekordbox: `src/selecta/ui/import_rekordbox_dialog.py`
- Import Covers: `src/selecta/ui/import_covers_dialog.py`
- Import/Export Playlist: `src/selecta/ui/import_export_playlist_dialog.py`

## Utilities

### Module Documentation
- Utils Module: `src/selecta/core/utils/README.md`

### Utility Components
- Path Helper: `src/selecta/core/utils/path_helper.py`
- Worker: `src/selecta/core/utils/worker.py`
- Loading: `src/selecta/core/utils/loading.py`
- Metadata Extractor: `src/selecta/core/utils/metadata_extractor.py`
- Cache Manager: `src/selecta/core/utils/cache_manager.py`
- Type Helpers: `src/selecta/core/utils/type_helpers.py`
- Audio Player: `src/selecta/core/utils/audio_player.py`
- Folder Scanner: `src/selecta/core/utils/folder_scanner.py`

## CLI Commands
- Main CLI: `src/selecta/cli/main.py`
- Database CLI: `src/selecta/cli/database.py`
- Discogs CLI: `src/selecta/cli/discogs.py`
- Spotify CLI: `src/selecta/cli/spotify.py`
- Rekordbox CLI: `src/selecta/cli/rekordbox.py`

## Feature Areas

### Track Linking
- Platform Links: `src/selecta/core/platform/link_manager.py`
- Sync Manager: `src/selecta/core/platform/sync_manager.py`

### Playlist Management
- Playlist Repository: `src/selecta/core/data/repositories/playlist_repository.py`
- Playlist Data Providers: `src/selecta/ui/components/playlist/*/`

### Configuration
- Config Module Documentation: `src/selecta/config/README.md`
- Config Manager: `src/selecta/config/config_manager.py`
- Settings Repository: `src/selecta/core/data/repositories/settings_repository.py`

### Resources
- Resources Documentation: `resources/README.md`
- Icons and Assets: `resources/icons/`
- Application Fonts: `resources/fonts/`

### CLI
- CLI Module Documentation: `src/selecta/cli/README.md`
- Main CLI: `src/selecta/cli/main.py`
- Database CLI: `src/selecta/cli/database.py`
- Spotify CLI: `src/selecta/cli/spotify.py`
- Discogs CLI: `src/selecta/cli/discogs.py`
- Rekordbox CLI: `src/selecta/cli/rekordbox.py`
- Environment CLI: `src/selecta/cli/env.py`

### Search Functionality
- Platform Search Panels: `src/selecta/ui/components/*/`
- Search Bar: `src/selecta/ui/components/search_bar.py`
