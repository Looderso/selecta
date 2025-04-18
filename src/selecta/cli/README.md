# CLI Module Documentation

## Overview
The Command Line Interface (CLI) module provides a set of commands for interacting with Selecta from the command line. It allows users to manage platform authentication, initialize the database, and perform various platform-specific operations without using the GUI.

## Key Components
- **Main CLI**: Entry point and command group organization
- **Platform Commands**: Spotify, Discogs, Rekordbox and YouTube integrations
- **Database Commands**: Database initialization and management
- **Development Tools**: Utilities for development and debugging

## Command Structure
Selecta CLI follows a hierarchical command structure using Click:
```
selecta [command_group] [command] [options]
```

Example: `selecta spotify auth`

## File Structure
- `__init__.py`: Module initialization
- `main.py`: Main CLI entry point and command registration
- `database.py`: Database management commands
- `spotify.py`: Spotify integration commands
- `discogs.py`: Discogs integration commands
- `rekordbox.py`: Rekordbox integration commands
- `env.py`: Environment information commands
- `dev/`: Development tools and utilities
  - `database.py`: Development database commands

## Command Groups

### Main Commands
- `selecta --version`: Display version information
- `selecta completion [shell]`: Print shell completion setup instructions

### Database Commands
- `selecta database init`: Initialize a new database
- `selecta database remove`: Remove the database

### Spotify Commands
- `selecta spotify setup`: Set up Spotify API credentials
- `selecta spotify auth`: Authenticate with Spotify
- `selecta spotify status`: Check Spotify authentication status

### Discogs Commands
- `selecta discogs setup`: Set up Discogs API credentials
- `selecta discogs auth`: Authenticate with Discogs
- `selecta discogs status`: Check Discogs authentication status

### Rekordbox Commands
- `selecta rekordbox setup`: Set up Rekordbox integration
- `selecta rekordbox scan`: Scan Rekordbox database
- `selecta rekordbox status`: Check Rekordbox integration status

### Environment Commands
- `selecta env info`: Display environment information

### Development Commands
- `selecta dev-database`: Development database utilities

## Dependencies
- Internal: Core platform modules, data repositories
- External: Click for CLI framework, loguru for logging

## Common Tasks
- **Adding a new command**: Create a function with `@click.command()` decorator and register it with the appropriate command group
- **Adding a new command group**: Create a function with `@click.group()` decorator and register it with the main CLI
- **Using options and arguments**: Use Click decorators like `@click.option()` and `@click.argument()`
- **Handling user input**: Use Click utilities like `click.prompt()`, `click.confirm()`, and `click.echo()`

## CLI Design Principles
- Each command should have a clear purpose and helpful documentation
- Commands should provide clear feedback on success or failure
- Dangerous operations should require confirmation
- Use color coding for status messages (green for success, yellow for warnings, red for errors)
- Credentials and sensitive information should be hidden during input

## Implementation Notes
- The CLI uses Click's command and group system for structure
- Platform authentication is handled through the appropriate platform auth managers
- Database operations use the core data module components
- User feedback is provided through Click's output utilities

## Usage Examples
```bash
# Initialize the database
selecta database init

# Set up Spotify integration
selecta spotify setup --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

# Authenticate with Spotify
selecta spotify auth

# Check Spotify status
selecta spotify status

# Get shell completion instructions
selecta completion zsh
```
