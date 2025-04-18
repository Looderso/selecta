# Selecta Application Documentation

## Overview

Selecta is a unified music library manager that integrates multiple music platforms (Spotify, Rekordbox, Discogs, YouTube) into a single application. It allows users to organize, browse, and synchronize their music collection across these platforms.

## Architecture

Selecta follows a modular architecture with clear separation of concerns:

1. **Application Layer**: Entry point and initialization
2. **UI Layer**: PyQt6-based user interface
3. **Core Layer**:
   - **Data Module**: Database models and repositories
   - **Platform Module**: External platform integrations
   - **Utils Module**: Shared utilities and helpers
4. **CLI Layer**: Command-line interface

## Module Structure

- `app.py`: Main application entry point
- `config/`: Configuration and settings management
- `core/`: Core application functionality
  - `data/`: Database models and repositories
  - `platform/`: Platform integrations (Spotify, Rekordbox, etc.)
  - `utils/`: Utility functions and helpers
- `cli/`: Command-line interface components
- `ui/`: User interface components

Application resources (icons, etc.) are stored in the top-level `resources/` directory.

## Entry Points

Selecta provides multiple entry points:

1. **GUI Application**:
   - Entry point: `app.py:run_app()`
   - Starts the PyQt6 user interface

2. **CLI Tool**:
   - Entry point: `cli/main.py:cli()`
   - Provides command-line functionality

## Dependencies

Selecta depends on several key libraries:

- **PyQt6**: UI framework
- **SQLAlchemy**: Database ORM
- **Click**: CLI framework
- **Loguru**: Logging
- **Platform-specific libraries**:
  - spotipy (Spotify)
  - pyrekordbox (Rekordbox)
  - discogs-client (Discogs)
  - google-api-python-client (YouTube)

## Application Flow

### Startup Sequence

1. Application entry point (`app.py:run_app`)
2. Database initialization
3. UI initialization (`ui/app.py:run_app`)
4. PyQt application main loop

### Platform Authentication

1. User selects platform in UI
2. Authentication status is checked
3. If not authenticated, OAuth flow is initiated
4. Platform client is initialized with authentication tokens

### Data Synchronization

1. User selects playlist to import/export
2. PlatformSyncManager handles the operation
3. Data is converted between platform and local models
4. Changes are persisted to database and/or platform

## Module Documentation

Each module has detailed documentation in its own README.md file:

- **UI Module**: `ui/README.md`
- **Core Data Module**: `core/data/README.md`
- **Platform Module**: `core/platform/README.md`
- **Utilities Module**: `core/utils/README.md`
- **CLI Module**: `cli/README.md`
- **Config Module**: `config/README.md`

## Key Files

### Application Entry

- `app.py`: Main GUI application entry point

### Core Components

- `core/platform/abstract_platform.py`: Platform integration interface
- `core/platform/sync_manager.py`: Cross-platform synchronization
- `core/data/models/db.py`: Database model definitions
- `core/data/database.py`: Database connection and management

### User Interface

- `ui/app.py`: PyQt application implementation
- `ui/components/main_content.py`: Main UI layout
- `ui/components/playlist/playlist_component.py`: Playlist view

### CLI Commands

- `cli/main.py`: CLI entry point and command registration

## Extending Selecta

Selecta is designed for extensibility:

1. **Adding a new platform**:
   - Create a new platform integration in `core/platform/`
   - Implement the AbstractPlatform interface
   - Add platform-specific UI components

2. **Enhancing the UI**:
   - Add new components to `ui/components/`
   - Update existing views to include new functionality

3. **Adding database models**:
   - Define models in `core/data/models/db.py`
   - Create migration scripts
   - Add repositories for data access

## Configuration

Selecta uses multiple configuration mechanisms:

1. **Environment variables**: Platform API credentials
2. **Database settings**: User preferences and platform tokens
3. **Command-line options**: Runtime behavior

## Logging

Selecta uses Loguru for logging, with logs directed to:

- Console (during development)
- Log files (in production)

## Error Handling

Selecta implements several error handling strategies:

- Global exception handling for UI
- Transaction-based error recovery for database operations
- Graceful degradation for platform API failures

## Design Patterns

Selecta employs several design patterns:

- **Repository Pattern**: For database access
- **Factory Pattern**: For platform client creation
- **Strategy Pattern**: For platform-specific implementations
- **Observer Pattern**: For UI updates via signals/slots
