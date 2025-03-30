# src/selecta/ui/components/playlist/discogs/discogs_playlist_data_provider.py
from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.ui.components.playlist.discogs.discogs_playlist_item import DiscogsPlaylistItem
from selecta.ui.components.playlist.discogs.discogs_track_item import DiscogsTrackItem
from selecta.ui.components.playlist.playlist_data_provider import PlaylistDataProvider
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class DiscogsPlaylistDataProvider(PlaylistDataProvider):
    """Data provider for Discogs collection and wantlist."""

    def __init__(self, client: DiscogsClient | None = None):
        """Initialize the Discogs playlist data provider.

        Args:
            client: Optional DiscogsClient instance
        """
        # Create or use the provided Discogs client
        if client is None:
            settings_repo = SettingsRepository()
            self.client = PlatformFactory.create("discogs", settings_repo)
            if not isinstance(self.client, DiscogsClient):
                raise ValueError("Could not create Discogs client")
        else:
            self.client = client

        # Check authentication
        if not self.client.is_authenticated():
            logger.warning("Discogs client is not authenticated")

    def get_all_playlists(self) -> list[PlaylistItem]:
        """Get all 'playlists' from Discogs (collection and wantlist).

        Returns:
            List of playlist items
        """
        if not self.client.is_authenticated():
            logger.error("Discogs client is not authenticated")
            return []

        try:
            playlist_items = []

            # Create root folder
            root_folder = DiscogsPlaylistItem(
                name="Discogs",
                item_id="discogs_root",
                is_folder_flag=True,
                track_count=0,
            )
            playlist_items.append(root_folder)

            # Add Collection as a "playlist"
            try:
                collection = self.client.get_collection()
                collection_item = DiscogsPlaylistItem(
                    name="Collection",
                    item_id="collection",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=len(collection),
                    list_type="collection",
                )
                playlist_items.append(collection_item)
            except Exception as e:
                logger.error(f"Error getting Discogs collection: {e}")

            # Add Wantlist as a "playlist"
            try:
                wantlist = self.client.get_wantlist()
                wantlist_item = DiscogsPlaylistItem(
                    name="Wantlist",
                    item_id="wantlist",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=len(wantlist),
                    list_type="wantlist",
                )
                playlist_items.append(wantlist_item)
            except Exception as e:
                logger.error(f"Error getting Discogs wantlist: {e}")

            return playlist_items

        except Exception as e:
            logger.exception(f"Error getting Discogs playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a 'playlist' (collection or wantlist).

        Args:
            playlist_id: ID of the 'playlist' ('collection' or 'wantlist')

        Returns:
            List of track items
        """
        if not self.client.is_authenticated():
            logger.error("Discogs client is not authenticated")
            return []

        # Root folder has no tracks
        if playlist_id == "discogs_root":
            return []

        try:
            track_items = []

            # Get tracks based on playlist type
            if playlist_id == "collection":
                # Get collection items
                collection = self.client.get_collection()
                for i, vinyl in enumerate(collection):
                    release = vinyl.release
                    track_items.append(
                        DiscogsTrackItem(
                            track_id=f"collection_{release.id}_{i}",  # Create unique ID
                            title=release.title,
                            artist=release.artist,
                            album=release.title,  # Discogs releases are albums
                            year=release.year,
                            genre=release.genre[0] if release.genre else None,
                            format=", ".join(release.format) if release.format else None,
                            label=release.label,
                            catno=release.catno,
                            country=release.country,
                            added_at=vinyl.date_added,
                            discogs_id=release.id,
                            discogs_uri=release.uri,
                            thumb_url=release.thumb_url,
                            cover_url=release.cover_url,
                            is_owned=True,
                            notes=vinyl.notes,
                        )
                    )
            elif playlist_id == "wantlist":
                # Get wantlist items
                wantlist = self.client.get_wantlist()
                for i, vinyl in enumerate(wantlist):
                    release = vinyl.release
                    track_items.append(
                        DiscogsTrackItem(
                            track_id=f"wantlist_{release.id}_{i}",  # Create unique ID
                            title=release.title,
                            artist=release.artist,
                            album=release.title,  # Discogs releases are albums
                            year=release.year,
                            genre=release.genre[0] if release.genre else None,
                            format=", ".join(release.format) if release.format else None,
                            label=release.label,
                            catno=release.catno,
                            country=release.country,
                            added_at=vinyl.date_added,
                            discogs_id=release.id,
                            discogs_uri=release.uri,
                            thumb_url=release.thumb_url,
                            cover_url=release.cover_url,
                            is_wanted=True,
                            notes=vinyl.notes,
                        )
                    )

            return track_items

        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")
            return []

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Discogs"
