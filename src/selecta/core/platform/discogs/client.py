"""Discogs API client for accessing Discogs data."""

from typing import Any

from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.discogs.api_client import DiscogsApiClient
from selecta.core.platform.discogs.auth import DiscogsAuthManager
from selecta.core.platform.discogs.models import DiscogsRelease, DiscogsVinyl


class DiscogsClient(AbstractPlatform):
    """Client for interacting with the Discogs API."""

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initializes the Discogs Client.

        Args:
            settings_repo (SettingsRepository | None, optional): Settings repository from the
                database. Defaults to None.
        """
        super().__init__(settings_repo)
        self.auth_manager = DiscogsAuthManager(settings_repo=self.settings_repo)
        self.client: DiscogsApiClient | None = None
        self._user_identity = None  # Cache for user identity

        # Try to initialize the client if we have valid credentials
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Discogs client with stored credentials."""
        try:
            self.client = self.auth_manager.get_discogs_client()
            if self.client:
                logger.info("Discogs client initialized successfully")
            else:
                logger.warning("No valid Discogs credentials found")
        except Exception as e:
            logger.exception(f"Failed to initialize Discogs client: {e}")
            self.client = None

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials."""
        if not self.client:
            return False

        # Use the API client's is_authenticated method which should be optimized
        return self.client.is_authenticated()

    def authenticate(self) -> bool:
        """Perform the Discogs OAuth flow to authenticate the user.

        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Start the authentication flow
            token_info = self.auth_manager.start_auth_flow()

            if token_info:
                # Re-initialize the client with the new tokens
                self._initialize_client()
                return self.is_authenticated()
            return False
        except Exception as e:
            logger.exception(f"Discogs authentication failed: {e}")
            return False

    def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's Discogs profile."""
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # If we've already fetched the identity, return the cached version
        if self._user_identity:
            return self._user_identity

        # Otherwise, fetch and cache it
        success, identity = self.client.get_identity()
        if not success:
            raise ValueError("Discogs: current user not available")

        # Cache the result
        self._user_identity = {
            "id": identity.get("id"),
            "username": identity.get("username", ""),
            "name": identity.get("name", ""),
            "email": identity.get("email", ""),
            "url": identity.get("resource_url", ""),
        }

        return self._user_identity

    def get_collection(self, username: str | None = None) -> list[DiscogsVinyl]:
        """Get user's collection from Discogs.

        Args:
            username: Optional username (defaults to authenticated user)

        Returns:
            List of DiscogsVinyl objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # If no username is provided, get the authenticated user's username
        if not username:
            success, identity = self.client.get_identity()
            if not success:
                raise ValueError("Could not get user identity")
            username = identity.get("username", "")

        # Get the user's collection
        success, collection_items = self.client.get_all_collection_items()
        if not success:
            raise ValueError("Failed to fetch Discogs collection")

        # Convert to our model
        vinyl_records = []
        for item in collection_items:
            # Extract basic release info
            basic_info = item.get("basic_information", {})

            # Combine with additional fields from the collection item
            release_data = {
                "id": basic_info.get("id", 0),
                "title": basic_info.get("title", ""),
                "year": basic_info.get("year"),
                "thumb": basic_info.get("thumb", ""),
                "cover_image": basic_info.get("cover_image", ""),
                "resource_url": basic_info.get("resource_url", ""),
                "artists": basic_info.get("artists", []),
                "labels": basic_info.get("labels", []),
                "formats": basic_info.get("formats", []),
                "date_added": item.get("date_added"),
                "rating": item.get("rating"),
                "notes": item.get("notes", ""),
            }

            # Create vinyl object
            vinyl = DiscogsVinyl.from_discogs_dict(release_data, is_owned=True)
            vinyl_records.append(vinyl)

        return vinyl_records

    def get_wantlist(self, username: str | None = None) -> list[DiscogsVinyl]:
        """Get user's wantlist from Discogs.

        Args:
            username: Optional username (defaults to authenticated user)

        Returns:
            List of DiscogsVinyl objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # If no username is provided, get the authenticated user's username
        if not username:
            success, identity = self.client.get_identity()
            if not success:
                raise ValueError("Could not get user identity")
            username = identity.get("username", "")

        # Get the user's wantlist
        success, wantlist_items = self.client.get_all_wantlist_items()
        if not success:
            raise ValueError("Failed to fetch Discogs wantlist")

        # Convert to our model
        vinyl_records = []
        for item in wantlist_items:
            # Extract basic release info
            basic_info = item.get("basic_information", {})

            # Combine with additional fields from the wantlist item
            release_data = {
                "id": basic_info.get("id", 0),
                "title": basic_info.get("title", ""),
                "year": basic_info.get("year"),
                "thumb": basic_info.get("thumb", ""),
                "cover_image": basic_info.get("cover_image", ""),
                "resource_url": basic_info.get("resource_url", ""),
                "artists": basic_info.get("artists", []),
                "labels": basic_info.get("labels", []),
                "formats": basic_info.get("formats", []),
                "date_added": item.get("date_added"),
                "notes": item.get("notes", ""),
            }

            # Create vinyl object
            vinyl = DiscogsVinyl.from_discogs_dict(release_data, is_wanted=True)
            vinyl_records.append(vinyl)

        return vinyl_records

    def search_release(
        self, query: str, artist: str | None = None, limit: int = 10
    ) -> list[DiscogsRelease]:
        """Search for releases on Discogs.

        Args:
            query: Search query
            artist: Optional artist name to refine search
            limit: Maximum number of results to return

        Returns:
            List of DiscogsRelease objects
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        try:
            # If both query and artist are provided, use them separately
            if query and artist:
                success, results = self.client.search_releases(
                    query=query, artist=artist, limit=limit
                )
            else:
                # Otherwise, use the query parameter alone
                success, results = self.client.search_releases(query=query, limit=limit)

            if not success:
                raise ValueError(f"Failed to search Discogs: {results.get('error')}")

            # Convert to our model
            releases = []
            for result in results.get("results", []):
                release = DiscogsRelease.from_discogs_dict(result)
                releases.append(release)

            return releases
        except Exception as e:
            logger.exception(f"Error searching Discogs: {e}")
            raise ValueError(f"Failed to search Discogs: {e}") from e

    def get_release_by_id(self, release_id: int) -> DiscogsRelease:
        """Get detailed information about a release by ID.

        Args:
            release_id: Discogs release ID

        Returns:
            DiscogsRelease object

        Raises:
            ValueError: If the client is not authenticated or release not found
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        success, release_data = self.client.get_release(release_id)
        if not success:
            raise ValueError(f"Failed to get release {release_id}")

        return DiscogsRelease.from_discogs_dict(release_data)

    def get_all_playlists(self) -> list[Any]:
        """Get all playlists from this platform.

        For Discogs, collection and wantlist are considered as 'playlists'

        Returns:
            A list of 'playlist' objects (collection and wantlist)

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # For Discogs, we'll represent the user's collection and wantlist as 'playlists'
        # Create fake playlist objects for Collection and Wantlist
        username = self.get_user_profile().get("username", "User")

        # Get counts
        success, collection_count = self.client.get_collection_count()
        if not success:
            collection_count = 0

        success, wantlist_count = self.client.get_wantlist_count()
        if not success:
            wantlist_count = 0

        return [
            {
                "id": "collection",
                "name": f"{username}'s Collection",
                "count": collection_count,
                "description": "Your vinyl record collection from Discogs",
                "type": "collection",
                "is_owned": True,
                "is_wanted": False,
            },
            {
                "id": "wantlist",
                "name": f"{username}'s Wantlist",
                "count": wantlist_count,
                "description": "Your vinyl wantlist from Discogs",
                "type": "wantlist",
                "is_owned": False,
                "is_wanted": True,
            },
        ]

    def get_playlist_tracks(self, playlist_id: str) -> list[DiscogsVinyl]:
        """Get all tracks in a specific playlist.

        For Discogs, this retrieves either collection or wantlist

        Args:
            playlist_id: Either 'collection' or 'wantlist'

        Returns:
            A list of DiscogsVinyl objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        if playlist_id == "collection":
            return self.get_collection()
        elif playlist_id == "wantlist":
            return self.get_wantlist()
        else:
            raise ValueError(
                f"Invalid playlist_id for Discogs: {playlist_id}. Must be 'collection' or 'wantlist'"
            )

    def search_tracks(self, query: str, limit: int = 10) -> list[DiscogsRelease]:
        """Search for tracks on this platform.

        For Discogs, this searches for releases

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            A list of DiscogsRelease objects matching the query

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        return self.search_release(query=query, limit=limit)

    def create_playlist(self, name: str, description: str = "") -> Any:
        """Create a new playlist on this platform.

        Discogs doesn't support custom playlist creation, so this raises an error

        Args:
            name: Name of the playlist
            description: Optional description

        Raises:
            NotImplementedError: Discogs doesn't support playlist creation
        """
        raise NotImplementedError("Discogs doesn't support creating custom playlists")

    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Add tracks to a playlist on this platform.

        For Discogs, this adds releases to collection or wantlist

        Args:
            playlist_id: Either 'collection' or 'wantlist'
            track_ids: List of Discogs release IDs

        Returns:
            True if successful

        Raises:
            ValueError: If not authenticated or API error occurs
            NotImplementedError: For unsupported operations
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        if playlist_id == "collection":
            # Add to collection
            for release_id in track_ids:
                try:
                    success, _ = self.client.add_to_collection(int(release_id))
                    if not success:
                        logger.warning(f"Failed to add release {release_id} to collection")
                except Exception as e:
                    logger.error(f"Error adding release {release_id} to collection: {e}")
            return True
        elif playlist_id == "wantlist":
            # Add to wantlist
            for release_id in track_ids:
                try:
                    success, _ = self.client.add_to_wantlist(int(release_id))
                    if not success:
                        logger.warning(f"Failed to add release {release_id} to wantlist")
                except Exception as e:
                    logger.error(f"Error adding release {release_id} to wantlist: {e}")
            return True
        else:
            raise ValueError(f"Invalid playlist_id for Discogs: {playlist_id}")

    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Remove tracks from a playlist on this platform.

        For Discogs, this removes releases from collection or wantlist

        Args:
            playlist_id: Either 'collection' or 'wantlist'
            track_ids: List of Discogs release IDs

        Returns:
            True if successful

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        if playlist_id == "collection":
            # Remove from collection
            for release_id in track_ids:
                try:
                    success, _ = self.client.remove_from_collection(int(release_id))
                    if not success:
                        logger.warning(f"Failed to remove release {release_id} from collection")
                except Exception as e:
                    logger.error(f"Error removing release {release_id} from collection: {e}")
            return True
        elif playlist_id == "wantlist":
            # Remove from wantlist
            for release_id in track_ids:
                try:
                    success, _ = self.client.remove_from_wantlist(int(release_id))
                    if not success:
                        logger.warning(f"Failed to remove release {release_id} from wantlist")
                except Exception as e:
                    logger.error(f"Error removing release {release_id} from wantlist: {e}")
            return True
        else:
            raise ValueError(f"Invalid playlist_id for Discogs: {playlist_id}")

    def import_playlist_to_local(self, platform_playlist_id: str) -> tuple[list[DiscogsVinyl], Any]:
        """Import a platform playlist to the local database.

        Args:
            platform_playlist_id: 'collection' or 'wantlist'

        Returns:
            A tuple of (list of DiscogsVinyl objects, playlist object)

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # Get the 'playlist' representation
        playlists = self.get_all_playlists()
        playlist = None
        for p in playlists:
            if p["id"] == platform_playlist_id:
                playlist = p
                break

        if not playlist:
            raise ValueError(f"Invalid Discogs playlist ID: {platform_playlist_id}")

        # Get all the tracks
        tracks = self.get_playlist_tracks(platform_playlist_id)

        return tracks, playlist

    def export_tracks_to_playlist(
        self, playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None
    ) -> str:
        """Export tracks to a playlist on this platform.

        Args:
            playlist_name: Name to use for the playlist (ignored for Discogs)
            track_ids: List of Discogs release IDs
            existing_playlist_id: Optional ID of an existing 'playlist' to update

        Returns:
            The platform-specific playlist ID

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        # For Discogs, we can only add to collection or wantlist
        playlist_id = existing_playlist_id or "collection"  # Default to collection

        if playlist_id not in ["collection", "wantlist"]:
            raise ValueError(
                f"Invalid Discogs playlist ID: {playlist_id}. Must be 'collection' or 'wantlist'"
            )

        # Add tracks to the specified 'playlist'
        self.add_tracks_to_playlist(playlist_id, track_ids)

        return playlist_id
