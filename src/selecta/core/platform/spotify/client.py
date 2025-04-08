"""Spotify API client for accessing Spotify data."""

from typing import Any

import spotipy
from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.spotify.auth import SpotifyAuthManager
from selecta.core.platform.spotify.models import SpotifyAudioFeatures, SpotifyPlaylist, SpotifyTrack


class SpotifyClient(AbstractPlatform):
    """Client for interacting with the Spotify API."""

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initialize the Spotify client.

        Args:
            settings_repo: Repository for accessing settings (optional)
        """
        super().__init__(settings_repo)
        self.auth_manager = SpotifyAuthManager(settings_repo=self.settings_repo)
        self.client: spotipy.Spotify | None = None

        # Try to initialize the client if we have valid credentials
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Spotify client with stored credentials."""
        try:
            self.client = self.auth_manager.get_spotify_client()
            if self.client:
                # Test the client with a simple request
                self.client.current_user()
                logger.info("Spotify client initialized successfully")
            else:
                logger.warning("No valid Spotify credentials found")
        except Exception as e:
            logger.exception(f"Failed to initialize Spotify client: {e}")
            self.client = None

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.client:
            return False

        try:
            # Try to make a simple API call
            self.client.current_user()
            return True
        except:
            return False

    def authenticate(self) -> bool:
        """Perform the Spotify OAuth flow to authenticate the user.

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
            logger.exception(f"Spotify authentication failed: {e}")
            return False

    def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's Spotify profile.

        Returns:
            Dictionary with user profile information

        Raises:
            ValueError: If the client is not authenticated
            ValueError: If the current user is not available
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        current_user = self.client.current_user()
        if not current_user:
            raise ValueError("Spotify: current user not available")

        return current_user

    def get_all_playlists(self) -> list[Any]:
        """Get all playlists from this platform.

        Returns:
            A list of platform-specific playlist objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        return self.get_playlists()

    def get_playlists(self) -> list[dict[str, Any]]:
        """Get all playlists for the current user.

        Returns:
            List of playlist dictionaries

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        playlists = []
        results = self.client.current_user_playlists(limit=50)

        while results:
            playlists.extend(results["items"])
            if results["next"]:
                results = self.client.next(results)
            else:
                break

        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> list[SpotifyTrack]:
        """Get all tracks in a specified playlist.

        Args:
            playlist_id: The Spotify playlist ID

        Returns:
            List of SpotifyTrack objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        tracks = []
        results = self.client.playlist_tracks(playlist_id, limit=100)

        while results:
            for item in results["items"]:
                # Skip null tracks (can happen with removed songs)
                if not item or not item.get("track"):
                    continue

                track = SpotifyTrack.from_spotify_dict(item)
                tracks.append(track)

            if results["next"]:
                results = self.client.next(results)
            else:
                break

        return tracks

    def get_playlist(self, playlist_id: str) -> SpotifyPlaylist:
        """Get detailed information about a playlist.

        Args:
            playlist_id: The Spotify playlist ID

        Returns:
            SpotifyPlaylist object

        Raises:
            ValueError: If the client is not authenticated
            ValueError: No playlists available.
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        playlist_data = self.client.playlist(playlist_id)
        if not playlist_data:
            raise ValueError("No playlists available.")
        return SpotifyPlaylist.from_spotify_dict(playlist_data)

    def create_playlist(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        collaborative: bool = False,
    ) -> SpotifyPlaylist:
        """Create a new playlist for the current user.

        Args:
            name: The name of the playlist
            description: Optional description for the playlist
            public: Whether the playlist should be public (default: False)
            collaborative: Whether the playlist should be collaborative (default: False)

        Returns:
            SpotifyPlaylist object for the new playlist

        Raises:
            ValueError: If the client is not authenticated
            ValueError: Playlist creation failed.
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        # Get the current user's ID
        user_id = self.get_user_profile()["id"]

        # Create the playlist
        playlist_data = self.client.user_playlist_create(
            user_id,
            name,
            public=public,
            collaborative=collaborative,
            description=description,
        )

        if not playlist_data:
            raise ValueError("Playlist creation failed.")

        return SpotifyPlaylist.from_spotify_dict(playlist_data)

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: list[str]) -> bool:
        """Add tracks to a playlist.

        Args:
            playlist_id: The Spotify playlist ID
            track_uris: List of Spotify track URIs to add

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        if not track_uris:
            return True  # Nothing to add

        # Spotify API can only handle 100 tracks at a time
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            self.client.playlist_add_items(playlist_id, batch)

        return True

    def remove_tracks_from_playlist(self, playlist_id: str, track_uris: list[str]) -> bool:
        """Remove tracks from a playlist.

        Args:
            playlist_id: The Spotify playlist ID
            track_uris: List of Spotify track URIs to remove

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        if not track_uris:
            return True  # Nothing to remove

        # Spotify API can only handle 100 tracks at a time
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i : i + 100]
            self.client.playlist_remove_all_occurrences_of_items(playlist_id, batch)

        return True

    def update_playlist_details(
        self,
        playlist_id: str,
        name: str | None = None,
        description: str | None = None,
        public: bool | None = None,
        collaborative: bool | None = None,
    ) -> bool:
        """Update a playlist's details.

        Args:
            playlist_id: The Spotify playlist ID
            name: New name for the playlist (optional)
            description: New description for the playlist (optional)
            public: Whether the playlist should be public (optional)
            collaborative: Whether the playlist should be collaborative (optional)

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        # Prepare the update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if public is not None:
            update_data["public"] = public
        if collaborative is not None:
            update_data["collaborative"] = collaborative

        if update_data:
            self.client.playlist_change_details(playlist_id, **update_data)

        return True

    def get_audio_features(self, track_ids: list[str]) -> list[SpotifyAudioFeatures]:
        """Get audio features for a list of tracks.

        Args:
            track_ids: List of Spotify track IDs

        Returns:
            List of SpotifyAudioFeatures objects

        Raises:
            ValueError: If the client is not authenticated
            ValueError: Features couln't be retrieved
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        features = []

        # Process in batches of 100 (Spotify API limit)
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            batch_features = self.client.audio_features(batch)
            if not batch_features:
                raise ValueError("Features couln't be retrieved.")

            for feature_data in batch_features:
                if feature_data:  # Skip None values
                    features.append(SpotifyAudioFeatures.from_spotify_dict(feature_data))

        return features

    def search_tracks(self, query: str, limit: int = 10) -> list[dict]:
        """Search for tracks on Spotify.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of track data dictionaries with full information including album art

        Raises:
            ValueError: If the client is not authenticated
            ValueError: Search failed.
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        results = self.client.search(query, limit=limit, type="track")
        if not results:
            raise ValueError("Search failed.")

        tracks = []
        for item in results.get("tracks", {}).get("items", []):
            # Return the raw track data from Spotify API that includes album images
            tracks.append(item)

        return tracks

    def import_playlist_to_local(
        self, spotify_playlist_id: str
    ) -> tuple[list[SpotifyTrack], SpotifyPlaylist]:
        """Import a Spotify playlist to the local database.

        Args:
            spotify_playlist_id: The Spotify playlist ID

        Returns:
            Tuple of (list of tracks, playlist object)

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        # Get the playlist details
        playlist = self.get_playlist(spotify_playlist_id)

        # Get all tracks in the playlist
        tracks = self.get_playlist_tracks(spotify_playlist_id)

        return tracks, playlist

    def export_tracks_to_playlist(
        self, playlist_name: str, track_ids: list[str], existing_playlist_id: str | None = None
    ) -> str:
        """Export tracks to a Spotify playlist.

        Args:
            playlist_name: Name for the Spotify playlist
            track_ids: List of Spotify track URIs or IDs to add
            existing_playlist_id: Optional ID of an existing playlist to update

        Returns:
            The Spotify playlist ID

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("Spotify client not authenticated")

        # Ensure we have URI format for all tracks
        track_uris = []
        for track_id in track_ids:
            # If it's already a URI (spotify:track:xxx), use it as is
            if track_id.startswith("spotify:track:"):
                track_uris.append(track_id)
            # If it's just an ID, convert to URI
            else:
                track_uris.append(f"spotify:track:{track_id}")

        if existing_playlist_id:
            # Update existing playlist
            # First verify the playlist exists
            try:
                # Check if playlist exists
                self.get_playlist(existing_playlist_id)
                # Add tracks to the existing playlist
                if track_uris:
                    self.add_tracks_to_playlist(existing_playlist_id, track_uris)
                return existing_playlist_id
            except Exception as e:
                logger.error(f"Error updating existing playlist: {e}")
                raise ValueError(f"Could not update playlist: {str(e)}") from e
        else:
            # Create a new playlist
            playlist = self.create_playlist(name=playlist_name, public=False)

            # Add tracks to the playlist
            if track_uris:
                self.add_tracks_to_playlist(playlist.id, track_uris)

            return playlist.id
