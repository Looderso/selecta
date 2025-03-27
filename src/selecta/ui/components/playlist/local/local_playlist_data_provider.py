# src/selecta/ui/components/playlist/local_playlist_data_provider.py
from typing import Any

from sqlalchemy.orm import Session

from selecta.core.data.database import get_session
from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.utils.type_helpers import column_to_bool, column_to_int, column_to_str
from selecta.ui.components.playlist.local.local_playlist_item import LocalPlaylistItem
from selecta.ui.components.playlist.local.local_track_item import LocalTrackItem
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class LocalPlaylistDataProvider(PlaylistDataProvider):
    """Data provider for local database playlists."""

    def __init__(self, session: Session | None = None):
        """Initialize the local playlist data provider.

        Args:
            session: Database session (optional)
        """
        self.session = session or get_session()
        self.playlist_repo = PlaylistRepository(self.session)
        self.track_repo = TrackRepository(self.session)

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all playlists from the local database.

        Returns:
            List of playlist items
        """
        db_playlists = self.playlist_repo.get_all()
        playlist_items = []

        for pl in db_playlists:
            # Get the track count
            track_count = len(pl.tracks) if pl.tracks is not None else 0

            playlist_items.append(
                LocalPlaylistItem(
                    name=column_to_str(pl.name),
                    item_id=pl.id,
                    parent_id=pl.parent_id,
                    is_folder_flag=column_to_bool(pl.is_folder),
                    description=column_to_str(pl.description),
                    track_count=track_count,
                )
            )

        return playlist_items

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of track items
        """
        tracks = self.playlist_repo.get_playlist_tracks(playlist_id)
        track_items = []

        for track in tracks:
            # Find the corresponding playlist track to get added_at date
            playlist = self.playlist_repo.get_by_id(playlist_id)
            added_at = None
            if playlist and playlist.tracks:
                for pt in playlist.tracks:
                    if pt.track_id == track.id:
                        added_at = pt.added_at
                        break

            # Extract album name if available
            album_name = track.album.title if track.album else None

            # Get first genre if available
            genre = None
            if track.genres and len(track.genres) > 0:
                genre = track.genres[0].name

            # Get attribute for BPM if available
            bpm = None
            tags = []
            if track.attributes:
                for attr in track.attributes:
                    if attr.name == "bpm":
                        bpm = attr.value
                    elif attr.name == "tag":
                        tags.append(attr.value)

            # Get platform info
            platform_info = []
            track_platform_info = self.track_repo.get_all_platform_info(column_to_int(track.id))

            for info in track_platform_info:
                platform_data = {
                    "platform": column_to_str(info.platform),
                    "platform_id": column_to_str(info.platform_id),
                    "uri": column_to_str(info.uri) if column_to_str(info.uri) else None,
                }

                # Add additional platform-specific data if available
                if column_to_str(info.platform_data):
                    import json

                    try:
                        additional_data = json.loads(column_to_str(info.platform_data))
                        platform_data.update(additional_data)
                    except (json.JSONDecodeError, TypeError):
                        pass

                platform_info.append(platform_data)

            track_items.append(
                LocalTrackItem(
                    track_id=track.id,
                    title=column_to_str(track.title),
                    artist=column_to_str(track.artist),
                    duration_ms=column_to_int(track.duration_ms),
                    album=album_name,
                    added_at=added_at,
                    local_path=column_to_str(track.local_path),
                    genre=genre,
                    bpm=bpm,
                    tags=tags,
                    platform_info=platform_info,
                )
            )

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Local Database"
