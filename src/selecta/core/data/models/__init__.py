"""Database models for Selecta."""

from selecta.core.data.models.album import Album
from selecta.core.data.models.credentials import PlatformCredentials
from selecta.core.data.models.genre import Genre
from selecta.core.data.models.playlist import Playlist, PlaylistTrack
from selecta.core.data.models.settings import UserSettings
from selecta.core.data.models.tag import PlaylistTag, Tag, TrackTag
from selecta.core.data.models.track import Track, TrackAttribute, TrackPlatformInfo
from selecta.core.data.models.vinyl import Vinyl

__all__ = [
    "Album",
    "Genre",
    "Playlist",
    "PlaylistTrack",
    "PlaylistTag",
    "PlatformCredentials",
    "Tag",
    "Track",
    "TrackAttribute",
    "TrackPlatformInfo",
    "TrackTag",
    "UserSettings",
    "Vinyl",
]
