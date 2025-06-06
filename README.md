# Selecta

A unified music library manager for Rekordbox, Spotify, and Discogs that helps you organize your music collection across platforms.

## Overview

Selecta synchronizes your music libraries and playlists between:

- **Rekordbox**: Your local DJ library
- **Spotify**: Your streaming playlists
- **Discogs**: Your vinyl collection

## Quick Start

```bash
# Run the application
selecta-gui

# Initialize database
selecta database init --force

# Show available commands
selecta --help
```

### Database Management

The application includes utilities to help manage the database:

```bash
# Database commands
selecta database init    # Initialize a new database
selecta database remove  # Remove the database
```

Advanced operations with development tools:

```bash
# Development database commands (with sample data)
selecta database dev init      # Initialize database with sample data
selecta database dev verify    # Verify database contents
selecta database dev add-quality-column  # Add quality column to tracks
```

The database is stored in your user application data directory by default.

For detailed documentation on database management, schema issues, and troubleshooting, see [DATABASE.md](DATABASE.md).

Key features:

- Cross-platform playlist management and synchronization
- Intelligent track matching between different platforms
- Vinyl collection tracking with Discogs integration
- Modern, user-friendly interface built with PyQt6

## Requirements

- Python 3.11+
- macOS, Linux, or Windows
- Spotify account (for Spotify integration)
- Discogs account (for Discogs integration)
- Rekordbox installed (for Rekordbox integration)

## Installation

### Option 1: Quick Start (Recommended)

Selecta includes a setup script that handles everything for you:

```bash
# Clone the repository
git clone https://github.com/Looderso/selecta.git
cd selecta

# Run the setup script
bash scripts/dev_setup.sh
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/Looderso/selecta.git
cd selecta

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Shell Completion

Set up shell completion to make using the command line easier:

```bash
# Generate and install shell completion for your shell (bash, zsh, or fish)
bash scripts/generate_completion.sh zsh  # Replace with your shell

# Alternatively, print completion instructions
selecta completion zsh  # Replace with your shell
```

## Environment Management

Selecta provides convenient CLI commands to manage your development environment:

```bash
# Reinstall environment from scratch
selecta env reinstall

# Print activation command for your shell
selecta env activate
```

## Usage

### GUI Mode

```bash
# Start the Selecta GUI application
selecta-gui
```

### CLI Mode

```bash
# Show available commands
selecta --help

# Platform-specific commands
selecta spotify --help
selecta discogs --help
selecta rekordbox --help

# Environment management
selecta env --help
```

## Project Structure

```
selecta/
├── pyproject.toml           # Project metadata and dependencies
├── README.md                # Project documentation
├── src/
│   ├── selecta/             # Main package
│   │   ├── app.py           # Main application class
│   │   ├── cli/             # Command-line interface
│   │   ├── config/          # Configuration management
│   │   ├── gui/             # GUI components
│   │   ├── platform/        # Platform-specific integrations
│   │   │   ├── rekordbox/   # Rekordbox integration
│   │   │   ├── spotify/     # Spotify API client
│   │   │   └── discogs/     # Discogs API client
│   │   ├── library/         # Core unified library management
│   │   ├── utils/           # Utility functions
│   │   └── data/            # Data persistence
│   └── tests/               # Test directory
├── scripts/                 # Build and development scripts
└── resources/               # Application resources
```

## Development

### Setting Up the Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test groups
pytest -m rekordbox
pytest -m spotify
pytest -m discogs
```

### Code Quality

```bash
# Run linters and type checking
ruff check src
```

### Type Safety

The project uses several approaches to ensure type safety:

1. **Protocol classes** for structural typing
2. **TypeGuard functions** for type narrowing with attribute checks
3. **TypedDict** for dictionary-like objects
4. **Type-safe dictionary access** utilities

Type helper utilities are in `src/selecta/core/utils/type_helpers.py`. See `TYPING_PLAN.md` for more details on our typing strategy.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - Qt bindings for Python
- [Spotipy](https://spotipy.readthedocs.io/) - Spotify API client for Python
- [python3-discogs-client](https://github.com/discogs/discogs_client) - Discogs API client for Python
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
