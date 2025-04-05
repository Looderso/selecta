# Database Management Guide for Selecta

This document explains how to manage the database for the Selecta application, particularly
in development environments.

## Changes in This Release

We've implemented several improvements to handle database schema management and prevent the
"no such column: track_platform_info.last_synced" error:

1. **New Database Management Scripts**:
   - `upgrade_db.py`: Detects and fixes schema issues by recreating tables with correct columns
   - `recreate_db.py`: Creates a fresh database with correct schema and test data

2. **Automated Schema Verification**:
   - All database initialization now includes schema verification
   - The app automatically detects missing columns and attempts to fix them

3. **Improved Development Workflow**:
   - Unified command interface through `dev_run.sh`
   - Clear error messages pointing to the right solution
   - Better documentation for future development

## Quick Start

The application provides commands to manage the database:

```bash
# Show available commands
selecta database --help

# Initialize database with sample data
selecta database init

# Upgrade existing database to fix schema issues
selecta database upgrade

# Verify database contents
selecta database verify
```

## Database Location

By default, the database is located in your user application data directory:
```
# macOS
~/Library/Application Support/selecta/selecta.db

# Linux
~/.local/share/selecta/selecta.db

# Windows
C:\Users\<username>\AppData\Local\looderso\selecta\selecta.db
```

This location is managed automatically by the application.

## Schema Mismatch Issues

If you encounter errors like:
- `no such column: track_platform_info.last_synced`
- `no such column: track_platform_info.needs_update`

These are schema mismatch errors between the code models and the database schema.

### How to Fix

1. **Run upgrade command** (recommended approach):
   ```bash
   selecta database upgrade
   ```

2. **Recreate the database** (if upgrade doesn't work):
   ```bash
   selecta database init --force
   ```

## Understanding the Database Upgrade Process

The upgrade script (`upgrade_db.py`) performs the following:

1. Connects to the SQLite database directly
2. Checks for missing columns in the `track_platform_info` table
3. Creates a new table with the correct schema
4. Copies all data from the old table
5. Replaces the old table with the new one
6. Verifies the changes were successful

Due to SQLite limitations, we cannot simply add a column with a non-constant default value. Instead,
we recreate the table with all needed columns and copy the data.

## Database Model Information

Key models in the system:

- **Track**: Central entity for all music tracks
- **TrackPlatformInfo**: Links tracks to platform-specific data (Spotify, Rekordbox, etc.)
- **Playlist**: Contains tracks and can be organized in folders
- **PlaylistTrack**: Join table connecting playlists and tracks with position info

The TrackPlatformInfo model requires these fields:
- `id`: Primary key
- `track_id`: Foreign key to the Track table
- `platform`: Platform name ('spotify', 'rekordbox', 'discogs')
- `platform_id`: ID of the track in the platform's system
- `uri`: URI/URL to the track in the platform (optional)
- `platform_data`: JSON string with platform-specific metadata
- `last_synced`: When the platform data was last synchronized
- `needs_update`: Whether this platform info needs to be updated

## Troubleshooting

If you encounter issues:

1. Check error message to identify which column or table is missing
2. Try running `./dev_run.sh upgrade` to fix schema issues
3. If that doesn't work, try `./dev_run.sh recreate` to create a fresh database
4. For persistent issues, delete the database file and run `./dev_run.sh recreate`

## Development Tips

- Always use TrackPlatformInfo with all required fields when creating new platform associations
- After making model changes, update or add migration scripts
- When implementing new features, verify database schema compatibility
- Use the `verify` command to check database contents:
  ```bash
  ./dev_run.sh verify
  ```

### Creating TrackPlatformInfo Objects Correctly

When creating new TrackPlatformInfo objects, always include all required fields:

```python
from datetime import UTC, datetime
from selecta.core.data.models.db import TrackPlatformInfo

# Correct way to create a TrackPlatformInfo object
platform_info = TrackPlatformInfo(
    track_id=track.id,               # Required: ID of the track
    platform="spotify",              # Required: Platform name
    platform_id=spotify_id,          # Required: ID in the platform
    uri=spotify_uri,                 # Optional: URI on the platform
    platform_data=platform_data,     # Optional: JSON string with metadata
    last_synced=datetime.now(UTC),   # Required: Current timestamp
    needs_update=False               # Required: Update flag
)
```

Missing the `last_synced` or `needs_update` fields will lead to the schema mismatch errors this guide addresses.

The most common locations where TrackPlatformInfo objects are created:

1. In playlist data providers like:
   - `spotify_playlist_data_provider.py`
   - `rekordbox_playlist_data_provider.py`
   - `local_playlist_data_provider.py`

2. In repository code like:
   - `track_repository.py` (particularly in `add_platform_info` method)

3. In search panels like:
   - `spotify_search_panel.py`
