# src/selecta/platform/discogs/client.py
"""Discogs API client for accessing Discogs data."""

from typing import Any

import discogs_client
from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.discogs.auth import DiscogsAuthManager
from selecta.core.platform.discogs.models import DiscogsRelease, DiscogsVinyl


class DiscogsClient(AbstractPlatform):
    """Client for interacting with the Discogs API."""

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initialize the Discogs client.

        Args:
            settings_repo: Repository for accessing settings (optional)
        """
        super().__init__(settings_repo)
        self.auth_manager = DiscogsAuthManager(settings_repo=self.settings_repo)
        self.client: discogs_client.Client | None = None

        # Try to initialize the client if we have valid credentials
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Discogs client with stored credentials."""
        try:
            self.client = self.auth_manager.get_discogs_client()
            if self.client:
                # Test the client with a simple request
                self.client.identity()
                logger.info("Discogs client initialized successfully")
            else:
                logger.warning("No valid Discogs credentials found")
        except Exception as e:
            logger.exception(f"Failed to initialize Discogs client: {e}")
            self.client = None

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.client:
            return False

        try:
            # Try to make an API call that requires authentication
            self.client.identity()
            return True
        except:
            return False

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
        """Get the current user's Discogs profile.

        Returns:
            Dictionary with user profile information

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Discogs client not authenticated")

        identity = self.client.identity()
        if not identity:
            raise ValueError("Discogs: current user not available")

        # Get user data as dictionary
        user_data = {
            "id": identity.id,
            "username": identity.username,
            "name": getattr(identity, "name", ""),
            "email": getattr(identity, "email", ""),
            "url": identity.url,
        }

        return user_data

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

        # If no username is provided, use the authenticated user
        if not username:
            # Convert the SimpleField to a string explicitly
            identity = self.client.identity()
            username = str(identity.username) if identity and hasattr(identity, "username") else ""

        # Get the user's collection
        collection_items = []
        try:
            user = self.client.user(username)
            collection = user.collection_folders[0].releases  # Folder 0 is "All"

            # Convert collection to list if needed
            items = list(collection) if hasattr(collection, "__iter__") else []

            # Convert to our model
            for item in items:
                release = item.release
                vinyl = DiscogsVinyl.from_discogs_object(release, is_owned=True)
                collection_items.append(vinyl)

            return collection_items
        except Exception as e:
            logger.exception(f"Error fetching Discogs collection: {e}")
            raise ValueError(f"Failed to fetch Discogs collection: {e}") from e

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

        # If no username is provided, use the authenticated user
        if not username:
            identity = self.client.identity()
            username = str(identity.username) if identity and hasattr(identity, "username") else ""

        # Get the user's wantlist
        wantlist_items = []
        try:
            user = self.client.user(username)
            wantlist = user.wantlist

            # Convert to our model
            for item in wantlist:  # type: ignore
                release = item.release
                vinyl = DiscogsVinyl.from_discogs_object(release, is_wanted=True)
                wantlist_items.append(vinyl)

            return wantlist_items
        except Exception as e:
            logger.exception(f"Error fetching Discogs wantlist: {e}")
            raise ValueError(f"Failed to fetch Discogs wantlist: {e}") from e

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
            search_params = {"type": "release", "per_page": limit}

            if artist:
                search_params["artist"] = artist

            results = self.client.search(query, **search_params)

            # Convert to our model
            releases = []
            for result in results:
                if hasattr(result, "id"):  # Only process valid results
                    release = DiscogsRelease.from_discogs_object(result)
                    releases.append(release)

            return releases
        except Exception as e:
            logger.exception(f"Error searching Discogs: {e}")
            raise ValueError(f"Failed to search Discogs: {e}") from e
