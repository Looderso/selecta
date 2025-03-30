"""Rekordbox client for accessing Rekordbox data."""

from loguru import logger
from pyrekordbox import Rekordbox6Database

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.rekordbox.auth import RekordboxAuthManager
from selecta.core.platform.rekordbox.models import RekordboxPlaylist, RekordboxTrack


class RekordboxClient(AbstractPlatform):
    """Client for interacting with the Rekordbox database."""

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initialize the Rekordbox client.

        Args:
            settings_repo: Repository for accessing settings (optional)
        """
        super().__init__(settings_repo)
        self.auth_manager = RekordboxAuthManager(settings_repo=self.settings_repo)
        self.db: Rekordbox6Database | None = None

        # Try to initialize the client if we have valid credentials
        self._initialize_client()

    # src/selecta/core/platform/rekordbox/client.py
    def _initialize_client(self) -> None:
        """Initialize the Rekordbox client with fixed key."""
        try:
            # Always use the fixed key from the auth manager
            db_key = self.auth_manager.get_stored_key()

            # Try to initialize with the key and let pyrekordbox find the database
            try:
                self.db = Rekordbox6Database(key=db_key)
                logger.info("Rekordbox client initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Rekordbox client: {e}")
                self.db = None

        except Exception as e:
            logger.exception(f"Failed to initialize Rekordbox client: {e}")
            self.db = None

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.db:
            return False

        try:
            # Try a simple query to check connection
            query = self.db.get_content()
            if query is None:
                return False

            # Just check if we can execute a query
            try:
                count = query.count()
                logger.debug(f"Rekordbox authentication successful - found {count} tracks")
                return True
            except Exception as e:
                logger.debug(f"Rekordbox query failed: {e}")
                return False
        except Exception as e:
            logger.debug(f"Rekordbox authentication check failed: {e}")
            return False

    def authenticate(self) -> bool:
        """Perform the authentication by checking if we can access the database.

        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # First check if we're already authenticated
            if self.is_authenticated():
                logger.info("Already authenticated with Rekordbox")
                return True

            # Clear any existing database connection and reinitialize
            self.db = None
            self._initialize_client()

            # Check if initialization worked
            return self.is_authenticated()
        except Exception as e:
            logger.exception(f"Rekordbox authentication failed: {e}")
            return False

    def _test_connection(self) -> bool:
        """Test if the database connection is working.

        Returns:
            True if connection is working, False otherwise
        """
        if not self.db:
            return False

        try:
            # Test connection by making a simple query
            query = self.db.get_content()
            if query is None:
                return False

            # Try to access first item to test if query works
            first_item = query.first()
            return first_item is not None or query.count() == 0  # Empty DB is still valid
        except Exception as e:
            logger.debug(f"Rekordbox connection test failed: {e}")
            return False

    def get_all_tracks(self) -> list[RekordboxTrack]:
        """Get all tracks in the Rekordbox database.

        Returns:
            List of RekordboxTrack objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        tracks = []
        contents = self.db.get_content()
        if contents:
            for content in contents:
                track = RekordboxTrack.from_rekordbox_content(content)
                tracks.append(track)
        else:
            raise ValueError("No content available")

        return tracks

    def get_track_by_id(self, track_id: int) -> RekordboxTrack | None:
        """Get a track by its ID.

        Args:
            track_id: The track ID

        Returns:
            RekordboxTrack object if found, None otherwise

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        content = self.db.get_content(ID=track_id)
        if not content:
            return None

        return RekordboxTrack.from_rekordbox_content(content)

    def search_tracks(self, query: str) -> list[RekordboxTrack]:
        """Search for tracks by title, artist, or album.

        Args:
            query: The search query

        Returns:
            List of matching RekordboxTrack objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        results = self.db.search_content(query)
        return [RekordboxTrack.from_rekordbox_content(content) for content in results]

    def get_all_playlists(self) -> list[RekordboxPlaylist]:
        """Get all playlists in the Rekordbox database.

        Returns:
            List of RekordboxPlaylist objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        playlists = []
        playlist_response = self.db.get_playlist()
        if playlist_response:
            for playlist_obj in playlist_response:
                # Skip smart playlists for now
                if playlist_obj.is_smart_playlist:
                    continue

                # Get tracks if it's not a folder
                tracks = []
                if not playlist_obj.is_folder:
                    try:
                        for content in self.db.get_playlist_contents(playlist_obj):
                            track = RekordboxTrack.from_rekordbox_content(content)
                            tracks.append(track)
                    except Exception as e:
                        logger.warning(f"Error getting tracks for playlist {playlist_obj.ID}: {e}")

                playlist = RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, tracks)
                playlists.append(playlist)
        else:
            raise ValueError("No playlist available")

        return playlists

    def get_playlist_by_id(self, playlist_id: str) -> RekordboxPlaylist | None:
        """Get a playlist by its ID.

        Args:
            playlist_id: The playlist ID

        Returns:
            RekordboxPlaylist object if found, None otherwise

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        playlist_obj = self.db.get_playlist(ID=playlist_id)
        if not playlist_obj:
            return None

        # Get tracks if it's not a folder
        tracks = []

        if hasattr(playlist_obj, "is_folder") and not playlist_obj.is_folder:  # type:ignore
            try:
                for content in self.db.get_playlist_contents(playlist_obj):
                    track = RekordboxTrack.from_rekordbox_content(content)
                    tracks.append(track)
            except Exception as e:
                logger.warning(f"Error getting tracks for playlist {playlist_id}: {e}")

        # Convert the DjmdPlaylist to our RekordboxPlaylist model
        return RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, tracks)

    def create_playlist(self, name: str, parent_id: str | None = None) -> RekordboxPlaylist:
        """Create a new playlist in Rekordbox.

        Args:
            name: The name of the new playlist
            parent_id: Optional parent folder ID (root if None)

        Returns:
            The created RekordboxPlaylist

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        parent = None
        if parent_id:
            parent = parent_id

        # Create the playlist in Rekordbox
        playlist_obj = self.db.create_playlist(name, parent=parent)

        # Commit changes to the database
        self.db.commit()

        # Return the created playlist
        return RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, [])

    def create_playlist_folder(self, name: str, parent_id: str | None = None) -> RekordboxPlaylist:
        """Create a new playlist folder in Rekordbox.

        Args:
            name: The name of the new playlist folder
            parent_id: Optional parent folder ID (root if None)

        Returns:
            The created RekordboxPlaylist folder

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        parent = None
        if parent_id:
            parent = parent_id

        # Create the playlist folder in Rekordbox
        playlist_obj = self.db.create_playlist_folder(name, parent=parent)

        # Commit changes to the database
        self.db.commit()

        # Return the created playlist folder
        return RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, [])

    def add_track_to_playlist(self, playlist_id: str, track_id: int) -> bool:
        """Add a track to a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        try:
            # Get the playlist and track
            playlist = self.db.get_playlist(ID=playlist_id)
            content = self.db.get_content(ID=track_id)

            if not playlist or not content:
                return False

            # Add the track to the playlist
            self.db.add_to_playlist(playlist, content)

            # Commit changes to the database
            self.db.commit()

            return True
        except Exception as e:
            logger.exception(f"Error adding track to playlist: {e}")
            return False

    def remove_track_from_playlist(self, playlist_id: str, track_id: int) -> bool:
        """Remove a track from a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        try:
            # Get the playlist
            playlist = self.db.get_playlist(ID=playlist_id)
            if not playlist:
                return False

            # Find the song in the playlist
            song_to_remove = None
            for song in playlist.Songs:  # type: ignore
                if song.ContentID == str(track_id):
                    song_to_remove = song
                    break

            if not song_to_remove:
                return False

            # Remove the track from the playlist
            self.db.remove_from_playlist(playlist, song_to_remove)

            # Commit changes to the database
            self.db.commit()

            return True
        except Exception as e:
            logger.exception(f"Error removing track from playlist: {e}")
            return False
