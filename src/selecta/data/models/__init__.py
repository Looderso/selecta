"""Database models for Selecta."""

from selecta.data.models.album import Album
from selecta.data.models.credentials import PlatformCredentials
from selecta.data.models.genre import Genre
from selecta.data.models.playlist import Playlist, PlaylistTrack
from selecta.data.models.settings import UserSettings
from selecta.data.models.tag import PlaylistTag, Tag, TrackTag
from selecta.data.models.track import Track, TrackAttribute, TrackPlatformInfo
from selecta.data.models.vinyl import Vinyl

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
