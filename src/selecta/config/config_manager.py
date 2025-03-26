"""Simple configuration management using .env."""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


def load_platform_credentials(platform: str) -> dict[str, str]:
    """Load credentials for a specific platform from .env file.

    Args:
        platform: Platform name (spotify, discogs, rekordbox)

    Returns:
        Dictionary of credentials
    """
    # Locate and load .env file
    possible_paths = [
        Path(".env"),
        Path(os.path.expanduser("~/.selecta/.env")),
        Path(os.path.expanduser("~/.config/selecta/.env")),
    ]

    # Try to load .env file
    for path in possible_paths:
        if path.exists():
            load_dotenv(path)
            logger.info(f"Loaded .env file from {path}")
            break
    else:
        logger.warning("No .env file found")

    # Mapping of environment variable prefixes
    env_mappings = {
        "spotify": {"client_id": "SPOTIFY_CLIENT_ID", "client_secret": "SPOTIFY_CLIENT_SECRET"},
        "discogs": {
            "client_id": "DISCOGS_CONSUMER_KEY",
            "client_secret": "DISCOGS_CONSUMER_SECRET",
        },
        "rekordbox": {
            "client_id": "REKORDBOX_CLIENT_ID",
            "client_secret": "REKORDBOX_CLIENT_SECRET",
        },
    }

    # Collect credentials
    credentials = {}
    for key in ["client_id", "client_secret"]:
        env_key = env_mappings[platform][key]
        value = os.getenv(env_key)
        if value:
            credentials[key] = value

    return credentials
