"""Data management module for Selecta."""

from selecta.core.data.database import get_engine, get_session, init_database
from selecta.core.data.init_db import initialize_database
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.tag_repository import TagRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.data.repositories.vinyl_repository import VinylRepository

__all__ = [
    "get_engine",
    "get_session",
    "init_database",
    "initialize_database",
    "PlaylistRepository",
    "TrackRepository",
    "VinylRepository",
    "TagRepository",
    "SettingsRepository",
]
