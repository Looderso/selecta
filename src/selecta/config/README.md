# Configuration Module Documentation

## Overview

The configuration module handles loading and managing application settings, particularly API credentials for external platforms like Spotify, Discogs, Rekordbox, and YouTube. It provides a consistent interface for accessing configuration values from environment variables or .env files.

## Key Components

- **ConfigManager**: Provides methods for loading platform-specific credentials
- **Environment Variable Management**: Handles retrieval of settings from environment variables or .env files

## File Structure

- `__init__.py`: Module initialization
- `config_manager.py`: Configuration loading and management functionality

## Configuration Sources

The module looks for configuration in the following locations (in order):

1. `.env` file in the current directory
2. `.env` file in `~/.selecta/`
3. `.env` file in `~/.config/selecta/`
4. Environment variables directly

## Platform Credential Management

The module is designed to handle credentials for multiple platforms:

- **Spotify**: Client ID and secret for Spotify API access
- **Discogs**: Consumer key and secret for Discogs API access
- **Rekordbox**: Client ID and secret for Rekordbox API access
- **YouTube**: Client ID and secret for YouTube API access

## Environment Variable Naming

The module expects environment variables with the following naming convention:

- Spotify: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- Discogs: `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`
- Rekordbox: `REKORDBOX_CLIENT_ID`, `REKORDBOX_CLIENT_SECRET`
- YouTube: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`

## Dependencies

- Internal: None
- External: python-dotenv for .env file loading, loguru for logging

## Common Tasks

- **Loading platform credentials**:

  ```python
  from selecta.config.config_manager import load_platform_credentials

  # Get Spotify credentials
  spotify_credentials = load_platform_credentials("spotify")
  client_id = spotify_credentials.get("client_id")
  client_secret = spotify_credentials.get("client_secret")
  ```

- **Adding support for a new platform**:
  1. Update the `env_mappings` dictionary in `config_manager.py`
  2. Add appropriate environment variables to your .env file

## Implementation Notes

- The configuration module is intentionally simple, focusing on credential management
- Other application settings are managed through the settings repository in the data module
- Credentials are never stored in the database for security reasons
- The module logs which .env file was loaded to assist with debugging

## Security Considerations

- API credentials should never be committed to the repository
- The .env file should be added to .gitignore
- For development, create a local .env file with required credentials
- For production, use environment variables or a secure .env file

## Future Improvements

- Add support for configuration profiles (development, testing, production)
- Implement encrypted storage for sensitive credentials
- Add validation for required configuration values
- Create a unified configuration interface that combines environment variables and database settings
