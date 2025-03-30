"""Discogs playlist data provider implementation."""

from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.ui.components.playlist.abstract_playlist_data_provider import (
    AbstractPlaylistDataProvider,
)
from selecta.ui.components.playlist.discogs.discogs_playlist_item import DiscogsPlaylistItem
from selecta.ui.components.playlist.discogs.discogs_track_item import DiscogsTrackItem
from selecta.ui.components.playlist.playlist_item import PlaylistItem
from selecta.ui.components.playlist.track_item import TrackItem


class DiscogsPlaylistDataProvider(AbstractPlaylistDataProvider):
    """Data provider for Discogs collection and wantlist."""

    def __init__(self, client: DiscogsClient | None = None, cache_timeout: float = 300.0):
        """Initialize the Discogs playlist data provider.

        Args:
            client: Optional DiscogsClient instance
            cache_timeout: Cache timeout in seconds (default: 5 minutes)
        """
        # Create or use the provided Discogs client
        if client is None:
            settings_repo = SettingsRepository()
            client_instance = PlatformFactory.create("discogs", settings_repo)
            if not isinstance(client_instance, DiscogsClient):
                raise ValueError("Could not create Discogs client")
            self.client = client_instance
        else:
            self.client = client

        # Initialize the abstract provider
        super().__init__(self.client, cache_timeout)

        # Additional cache keys specific to Discogs
        self._collection_cache_key = "discogs_collection"
        self._wantlist_cache_key = "discogs_wantlist"

    def _fetch_playlists(self) -> list[PlaylistItem]:
        """Fetch 'playlists' from Discogs (collection and wantlist).

        Returns:
            List of playlist items
        """
        # Always create a fresh list of playlist items
        playlist_items = []

        # Create root folder
        root_folder = DiscogsPlaylistItem(
            name="Discogs",
            item_id="discogs_root",
            is_folder_flag=True,
            track_count=0,
        )
        playlist_items.append(root_folder)

        # Check authentication only once
        if not self._ensure_authenticated():
            # Still return the root folder even when not authenticated
            return playlist_items

        # Get collection count from cache or API
        collection_count = 0
        try:
            if self.cache.has_valid(self._collection_cache_key):
                collection = self.cache.get(self._collection_cache_key, [])
                collection_count = len(collection)
            else:
                collection = self.client.get_collection()
                collection_count = len(collection)
                # Cache the collection data
                self.cache.set(self._collection_cache_key, collection)

            collection_item = DiscogsPlaylistItem(
                name=f"Collection ({collection_count} items)",
                item_id="collection",
                parent_id="discogs_root",
                is_folder_flag=False,
                track_count=collection_count,
                list_type="collection",
            )
            playlist_items.append(collection_item)
        except Exception as e:
            logger.error(f"Error getting Discogs collection: {e}")
            # Add an empty collection placeholder
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Collection (error)",
                    item_id="collection",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="collection",
                )
            )

        # Get wantlist count from cache or API
        wantlist_count = 0
        try:
            if self.cache.has_valid(self._wantlist_cache_key):
                wantlist = self.cache.get(self._wantlist_cache_key, [])
                wantlist_count = len(wantlist)
            else:
                wantlist = self.client.get_wantlist()
                wantlist_count = len(wantlist)
                # Cache the wantlist data
                self.cache.set(self._wantlist_cache_key, wantlist)

            wantlist_item = DiscogsPlaylistItem(
                name=f"Wantlist ({wantlist_count} items)",
                item_id="wantlist",
                parent_id="discogs_root",
                is_folder_flag=False,
                track_count=wantlist_count,
                list_type="wantlist",
            )
            playlist_items.append(wantlist_item)
        except Exception as e:
            logger.error(f"Error getting Discogs wantlist: {e}")
            # Add an empty wantlist placeholder
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Wantlist (error)",
                    item_id="wantlist",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="wantlist",
                )
            )

        return playlist_items

    def _fetch_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Fetch tracks for a 'playlist' (collection or wantlist).

        Args:
            playlist_id: ID of the 'playlist' ('collection' or 'wantlist')

        Returns:
            List of track items
        """
        # Root folder has no tracks
        if playlist_id == "discogs_root":
            return []

        if not self._ensure_authenticated():
            return []

        track_items = []

        try:
            # Get tracks based on playlist type
            if playlist_id == "collection":
                # Get collection items from cache or API
                collection = self.cache.get_or_set(
                    self._collection_cache_key, lambda: self.client.get_collection()
                )

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
                # Get wantlist items from cache or API
                wantlist = self.cache.get_or_set(
                    self._wantlist_cache_key, lambda: self.client.get_wantlist()
                )

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
        except Exception as e:
            logger.exception(f"Error getting tracks for playlist {playlist_id}: {e}")

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Discogs"
