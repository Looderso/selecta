# src/selecta/ui/components/playlist/discogs/discogs_playlist_data_provider.py
import time
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

    # Add class-level cache for playlist data
    _cached_collection = None
    _collection_timestamp = 0
    _cached_wantlist = None
    _wantlist_timestamp = 0
    _cached_tracks = {}
    _cache_timestamp = 0
    _cache_timeout = 300  # 5 minutes

    def __init__(self, client: DiscogsClient | None = None):
        """Initialize the Discogs playlist data provider.

        Args:
            client: Optional DiscogsClient instance
        """
        # Initialize cache variables if they don't exist yet
        if not hasattr(self.__class__, "_cache_timeout"):
            self.__class__._cache_timeout = 300  # 5 minutes

        if not hasattr(self.__class__, "_cached_collection"):
            self.__class__._cached_collection = None
            self.__class__._collection_timestamp = 0

        if not hasattr(self.__class__, "_cached_wantlist"):
            self.__class__._cached_wantlist = None
            self.__class__._wantlist_timestamp = 0

        if not hasattr(self.__class__, "_cached_tracks"):
            self.__class__._cached_tracks = {}

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

        # Use cached data for playlist contents, but not for playlist structure
        current_time = time.time()

        # Check authentication only once
        is_authenticated = False
        try:
            is_authenticated = self.client and self.client.is_authenticated()
        except Exception as e:
            logger.error(f"Error checking Discogs authentication: {e}")

        if not is_authenticated:
            logger.warning("Discogs client is not authenticated")
            # Still return the root folder even when not authenticated
            return playlist_items

        # Get user identity and fetch collection/wantlist
        try:
            # user_profile = self.client.get_user_profile()

            # Add Collection as a "playlist"
            collection_count = 0
            try:
                # Use cached collection if available
                if (
                    hasattr(self.__class__, "_cached_collection")
                    and self.__class__._cached_collection is not None
                    and (current_time - self.__class__._collection_timestamp)
                    < self.__class__._cache_timeout
                ):
                    collection_count = len(self.__class__._cached_collection)
                else:
                    collection = self.client.get_collection()
                    collection_count = len(collection)
                    # Cache the collection data
                    self.__class__._cached_collection = collection
                    self.__class__._collection_timestamp = current_time

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

            # Add Wantlist as a "playlist"
            wantlist_count = 0
            try:
                # Use cached wantlist if available
                if (
                    hasattr(self.__class__, "_cached_wantlist")
                    and self.__class__._cached_wantlist is not None
                    and (current_time - self.__class__._wantlist_timestamp)
                    < self.__class__._cache_timeout
                ):
                    wantlist_count = len(self.__class__._cached_wantlist)
                else:
                    wantlist = self.client.get_wantlist()
                    wantlist_count = len(wantlist)
                    # Cache the wantlist data
                    self.__class__._cached_wantlist = wantlist
                    self.__class__._wantlist_timestamp = current_time

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

        except Exception as e:
            logger.exception(f"Error getting Discogs user profile: {e}")
            # Add placeholders if we can't get user profile
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Collection (not available)",
                    item_id="collection",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="collection",
                )
            )
            playlist_items.append(
                DiscogsPlaylistItem(
                    name="Wantlist (not available)",
                    item_id="wantlist",
                    parent_id="discogs_root",
                    is_folder_flag=False,
                    track_count=0,
                    list_type="wantlist",
                )
            )

        return playlist_items

    def get_playlist_tracks(self, playlist_id: Any) -> list[TrackItem]:
        """Get all tracks in a 'playlist' (collection or wantlist).

        Args:
            playlist_id: ID of the 'playlist' ('collection' or 'wantlist')

        Returns:
            List of track items
        """
        # Check if cache is initialized
        if not hasattr(self.__class__, "_cached_tracks"):
            self.__class__._cached_tracks = {}

        # Check cache first
        current_time = time.time()
        if (
            playlist_id in self.__class__._cached_tracks
            and (current_time - self.__class__._cached_tracks[playlist_id]["timestamp"])
            < self.__class__._cache_timeout
        ):
            logger.debug(f"Using cached tracks for playlist {playlist_id}")
            return self.__class__._cached_tracks[playlist_id]["tracks"]

        # Root folder has no tracks
        if playlist_id == "discogs_root":
            empty_tracks = []
            self.__class__._cached_tracks[playlist_id] = {
                "tracks": empty_tracks,
                "timestamp": current_time,
            }
            return empty_tracks

        if not self.client or not self.client.is_authenticated():
            logger.error("Discogs client is not authenticated")
            empty_tracks = []
            self.__class__._cached_tracks[playlist_id] = {
                "tracks": empty_tracks,
                "timestamp": current_time,
            }
            return empty_tracks

        track_items = []

        try:
            # Get tracks based on playlist type
            if playlist_id == "collection":
                # Get collection items from cache or API
                collection = None
                if (
                    hasattr(self.__class__, "_cached_collection")
                    and self.__class__._cached_collection is not None
                ):
                    collection = self.__class__._cached_collection
                else:
                    collection = self.client.get_collection()
                    self.__class__._cached_collection = collection
                    self.__class__._collection_timestamp = current_time

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
                wantlist = None
                if (
                    hasattr(self.__class__, "_cached_wantlist")
                    and self.__class__._cached_wantlist is not None
                ):
                    wantlist = self.__class__._cached_wantlist
                else:
                    wantlist = self.client.get_wantlist()
                    self.__class__._cached_wantlist = wantlist
                    self.__class__._wantlist_timestamp = current_time

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

        # Cache tracks before returning
        self.__class__._cached_tracks[playlist_id] = {
            "tracks": track_items,
            "timestamp": current_time,
        }

        return track_items

    def get_platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name
        """
        return "Discogs"
