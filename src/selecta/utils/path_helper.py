"""Utilities for working with file paths."""

import sys
from pathlib import Path

import appdirs


def get_app_data_path() -> Path:
    """Get the application data directory path.

    Creates the directory if it doesn't exist.

    Returns:
        Path: The application data directory path
    """
    app_data_dir = Path(appdirs.user_data_dir("selecta", "looderso"))

    # Create the directory if it doesn't exist
    app_data_dir.mkdir(parents=True, exist_ok=True)

    return app_data_dir


def get_app_config_path() -> Path:
    """Get the application config directory path.

    Creates the directory if it doesn't exist.

    Returns:
        Path: The application config directory path
    """
    app_config_dir = Path(appdirs.user_config_dir("selecta", "looderso"))

    # Create the directory if it doesn't exist
    app_config_dir.mkdir(parents=True, exist_ok=True)

    return app_config_dir


def get_app_cache_path() -> Path:
    """Get the application cache directory path.

    Creates the directory if it doesn't exist.

    Returns:
        Path: The application cache directory path
    """
    app_cache_dir = Path(appdirs.user_cache_dir("selecta", "looderso"))

    # Create the directory if it doesn't exist
    app_cache_dir.mkdir(parents=True, exist_ok=True)

    return app_cache_dir


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path: The project root directory
    """
    # Check if we're in a PyInstaller bundle
    if getattr(sys, "frozen", False):
        # We're running in a bundle
        return Path(sys._MEIPASS)  # type: ignore

    # We're running in a normal Python environment
    # Walk up from the current file until we find the project root
    current_path = Path(__file__).resolve()
    while current_path.name != "src" and current_path != current_path.parent:
        current_path = current_path.parent

    if current_path.name == "src":
        return current_path.parent

    # Fallback to current directory
    return Path.cwd()


def get_resource_path(relative_path: str) -> Path:
    """Get the path to a resource file.

    Args:
        relative_path: Path relative to the resources directory

    Returns:
        Path: The absolute path to the resource
    """
    root = get_project_root()

    # First, check if running as a package (resources inside package)
    if (root / "src" / "selecta" / "resources").exists():
        return root / "src" / "selecta" / "resources" / relative_path

    # Then check for resources at the project root level
    if (root / "resources").exists():
        return root / "resources" / relative_path

    # Finally, check relative to the executable
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "resources" / relative_path

    # Fallback
    return Path(relative_path)
