"""Rekordbox client for accessing Rekordbox data."""

import os

from loguru import logger
from pyrekordbox import Rekordbox6Database

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.rekordbox.auth import RekordboxAuthManager
from selecta.core.platform.rekordbox.models import RekordboxPlaylist, RekordboxTrack


class PatchedRekordbox6Database(Rekordbox6Database):
    """A patched version of the Rekordbox6Database class that overrides commit method.

    This class disables Rekordbox PID check for commit operations.
    """

    def __init__(self, path=None, db_dir="", key="", unlock=True):
        """Override the init method to disable Rekordbox PID check."""
        # Get the original get_rekordbox_pid function
        import pyrekordbox.utils

        original_get_pid = pyrekordbox.utils.get_rekordbox_pid

        # Temporarily monkey patch the function to always return 0
        def mock_get_pid(*args, **kwargs):
            return 0

        try:
            # Apply our patch
            pyrekordbox.utils.get_rekordbox_pid = mock_get_pid
            logger.debug("Patched get_rekordbox_pid to always return 0")

            # Call the original __init__ with our patched function in place
            super().__init__(path, db_dir, key, unlock)
            logger.debug("PatchedRekordbox6Database initialized successfully")
        finally:
            # Restore the original function
            pyrekordbox.utils.get_rekordbox_pid = original_get_pid
            logger.debug("Restored original get_rekordbox_pid function")

    def commit(self, autoinc=True):
        """Override the commit method to disable Rekordbox PID check."""
        # Get the original get_rekordbox_pid function
        import pyrekordbox.utils

        original_get_pid = pyrekordbox.utils.get_rekordbox_pid

        # Temporarily monkey patch the function to always return 0
        def mock_get_pid(*args, **kwargs):
            return 0

        try:
            # Apply our patch
            pyrekordbox.utils.get_rekordbox_pid = mock_get_pid
            logger.debug("Patched get_rekordbox_pid for commit to always return 0")

            # Directly implement commit logic to bypass the PID check
            if autoinc:
                self.registry.autoincrement_local_update_count(set_row_usn=True)
            if self.session:
                self.session.commit()
            if self.registry:
                self.registry.clear_buffer()

            # Update the masterPlaylists6.xml file
            if self.playlist_xml is not None:
                # Sync the updated_at values of the playlists
                playlist_result = self.get_playlist()
                if playlist_result is not None:
                    for pl in playlist_result:
                        plxml = self.playlist_xml.get(pl.ID)
                        if plxml is None:
                            logger.warning(f"Playlist {pl.ID} not found in masterPlaylists6.xml")
                            continue

                        ts = plxml["Timestamp"]
                        diff = pl.updated_at - ts
                        if abs(diff.total_seconds()) > 1:
                            logger.debug(f"Updating updated_at of playlist {pl.ID} in XML")
                            self.playlist_xml.update(pl.ID, updated_at=pl.updated_at)

                # Save the XML file if it was modified
                if self.playlist_xml.modified:
                    self.playlist_xml.save()

            logger.debug("Commit completed successfully")
            return True
        finally:
            # Restore the original function
            pyrekordbox.utils.get_rekordbox_pid = original_get_pid
            logger.debug("Restored original get_rekordbox_pid function after commit")


class RekordboxClient(AbstractPlatform):
    """Client for interacting with the Rekordbox database."""

    # Singleton instance
    _instance = None
    _is_initialized = False

    # Store original get_rekordbox_pid function at module level
    _original_get_pid_func = None

    @classmethod
    def disable_rekordbox_checks(cls, disable: bool = True) -> None:
        """Globally disable Rekordbox checks.

        This class method can be called before any instances are created to
        globally disable the Rekordbox running checks in the pyrekordbox library.

        Args:
            disable: If True, disable the checks. If False, restore the original behavior.
        """
        import pyrekordbox.utils

        # Store original function if not already stored
        if cls._original_get_pid_func is None:
            cls._original_get_pid_func = pyrekordbox.utils.get_rekordbox_pid

        if disable:
            # Replace with dummy function that always returns 0
            def mock_get_pid(*args, **kwargs):
                return 0

            pyrekordbox.utils.get_rekordbox_pid = mock_get_pid
            logger.debug("Globally disabled pyrekordbox Rekordbox running checks")
        else:
            # Restore original function if we have it
            if cls._original_get_pid_func is not None:
                pyrekordbox.utils.get_rekordbox_pid = cls._original_get_pid_func
                logger.debug("Restored pyrekordbox Rekordbox running checks")

    def __new__(cls, settings_repo: SettingsRepository | None = None) -> "RekordboxClient":
        """Create a new RekordboxClient or return the existing instance.

        This implements the singleton pattern to ensure only one instance
        of RekordboxClient exists.

        Args:
            settings_repo: Repository for accessing settings (optional)

        Returns:
            The singleton RekordboxClient instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._is_initialized = False
        return cls._instance

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initialize the Rekordbox client.

        Args:
            settings_repo: Repository for accessing settings (optional)
        """
        # Only run initialization once
        if self._is_initialized:
            return

        # Disable Rekordbox running checks globally during initialization
        self.__class__.disable_rekordbox_checks(True)

        try:
            super().__init__(settings_repo)
            self.auth_manager = RekordboxAuthManager(settings_repo=self.settings_repo)
            self.db: Rekordbox6Database | None = None

            # Try to initialize the client if we have valid credentials
            self._initialize_client()
            self._is_initialized = True
        finally:
            # Always restore normal checks at the end of initialization
            self.__class__.disable_rekordbox_checks(False)

    def __del__(self) -> None:
        """Clean up resources when the object is destroyed."""
        self.close()

    def __enter__(self) -> "RekordboxClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

    def close(self) -> None:
        """Close the database connection and clean up resources."""
        if self.db is not None:
            try:
                logger.debug("Closing Rekordbox database connection")
                self.db.close()
            except Exception as e:
                logger.debug(f"Error closing Rekordbox database: {e}")
            finally:
                self.db = None

    # src/selecta/core/platform/rekordbox/client.py
    def _patch_rekordbox_pid_check(self, enable_patch: bool = True) -> None:
        """Monkey-patch the get_rekordbox_pid function in pyrekordbox.

        Args:
            enable_patch: If True, patches the function to always return 0 (no Rekordbox running).
                         If False, restores the original function.
        """
        # Use the class method for consistency
        self.__class__.disable_rekordbox_checks(enable_patch)

    def _initialize_client(self) -> None:
        """Initialize the Rekordbox client with fixed key."""
        try:
            # Close any existing database connection first
            if self.db is not None:
                logger.debug("Closing existing database connection before initialization")
                self.close()

            # Always use the fixed key from the auth manager
            logger.debug("Getting Rekordbox database key from auth manager")
            db_key = self.auth_manager.get_stored_key()

            if not db_key:
                logger.error("Could not get Rekordbox database key from auth manager")
                self.db = None
                return

            # Try to initialize with the key and let pyrekordbox find the database
            # Use our PatchedRekordbox6Database to avoid "Rekordbox is running" issues
            try:
                logger.debug("Attempting to initialize Rekordbox database with patched client")

                # The get_database_path function may not exist in the version of pyrekordbox installed
                # Instead of relying on it, we'll let PatchedRekordbox6Database find the database automatically

                # Initialize the database directly with just the key
                # This works because pyrekordbox will automatically locate the database file
                self.db = PatchedRekordbox6Database(key=db_key)
                logger.info("Initialized Rekordbox database with automatic database path detection")

                # Test if the DB is working
                if self.db:
                    try:
                        # Simple test to verify functionality
                        logger.debug("Testing database connection...")
                        content_query = self.db.get_content()
                        count = content_query.count() if content_query else 0
                        logger.info(f"Rekordbox client initialized successfully: found {count} tracks")
                    except Exception as test_error:
                        logger.warning(f"Database initialized but test query failed: {test_error}")
                        # Keep the connection open anyway, it might still work
                else:
                    logger.warning("PatchedRekordbox6Database returned None")
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

        # Check if Rekordbox is running (with improved process state detection)
        self.check_rekordbox_process()

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

    def check_rekordbox_process(self) -> tuple[bool, int | None, str | None]:
        """Check if Rekordbox is running and get process details.

        Returns:
            Tuple of (is_running, pid, status) where:
                - is_running: True if a Rekordbox process is active (running/sleeping)
                - pid: Process ID of Rekordbox if found, None otherwise
                - status: Process status string if found, None otherwise
        """
        try:
            import os

            import psutil
            from pyrekordbox.config import get_rekordbox_pid

            # Get our own process and child processes
            our_pid = os.getpid()
            our_process = psutil.Process(our_pid)
            our_children = our_process.children(recursive=True)
            our_child_pids = {child.pid for child in our_children}

            # Look for Rekordbox in all processes, not just relying on pid file
            # First check the pid file
            pid = get_rekordbox_pid()

            # Verify if this process is actually running and not one of our child processes
            if pid and pid not in our_child_pids:
                try:
                    process = psutil.Process(pid)
                    status = process.status()

                    # We found a Rekordbox process
                    if status in ["running", "sleeping"]:
                        logger.warning(
                            f"Rekordbox is currently running with PID {pid} "
                            f"(status: {status}) - database changes may cause conflicts"
                        )
                        return True, pid, status
                    else:
                        logger.info(
                            f"Rekordbox process exists with PID {pid} but status is {status}, proceeding anyway"
                        )
                        return False, pid, status
                except psutil.NoSuchProcess:
                    # Process doesn't exist anymore
                    logger.info(f"Rekordbox process with PID {pid} no longer exists")
                    # Continue checking other processes

            # Also look for Rekordbox process by name, excluding our own child processes
            for proc in psutil.process_iter(["pid", "name", "status"]):
                if "rekordbox" in proc.info["name"].lower() and proc.info["pid"] not in our_child_pids:
                    pid = proc.info["pid"]
                    status = proc.info["status"]
                    logger.warning(f"Found Rekordbox process by name with PID {pid} (status: {status})")
                    if status in ["running", "sleeping"]:
                        return True, pid, status

            # Check if there are rekordbox-like processes among our children (spawned by us)
            for child_pid in our_child_pids:
                try:
                    child = psutil.Process(child_pid)
                    if "rekordbox" in child.name().lower():
                        logger.info(
                            f"Found Rekordbox process with PID {child_pid} spawned by our application - ignoring"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # No active Rekordbox process found
            return False, None, None

        except Exception as e:
            logger.debug(f"Failed to check if Rekordbox is running: {e}")
            return False, None, None

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

            # Reinitialize client - this will close any existing connection
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

    def create_playlist(self, name: str, parent_id: str | None = None, force: bool = False) -> RekordboxPlaylist:
        """Create a new playlist in Rekordbox.

        Args:
            name: The name of the new playlist
            parent_id: Optional parent folder ID (root if None)
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            The created RekordboxPlaylist

        Raises:
            ValueError: If the client is not authenticated
            RuntimeError: If Rekordbox is running and force=False
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        parent = None
        if parent_id:
            parent = parent_id

        # Create the playlist in Rekordbox
        playlist_obj = self.db.create_playlist(name, parent=parent)

        # Use our custom commit method
        try:
            self.custom_commit(force=force)
        except RuntimeError:
            # Let the RuntimeError propagate up if it's related to Rekordbox running
            raise
        except Exception as e:
            logger.exception(f"Error committing changes: {e}")

        # Return the created playlist
        return RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, [])

    def create_playlist_folder(self, name: str, parent_id: str | None = None, force: bool = False) -> RekordboxPlaylist:
        """Create a new playlist folder in Rekordbox.

        Args:
            name: The name of the new playlist folder
            parent_id: Optional parent folder ID (root if None)
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            The created RekordboxPlaylist folder

        Raises:
            ValueError: If the client is not authenticated
            RuntimeError: If Rekordbox is running and force=False
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        parent = None
        if parent_id:
            parent = parent_id

        # Create the playlist folder in Rekordbox
        playlist_obj = self.db.create_playlist_folder(name, parent=parent)

        # Use our custom commit method
        try:
            self.custom_commit(force=force)
        except RuntimeError:
            # Let the RuntimeError propagate up if it's related to Rekordbox running
            raise
        except Exception as e:
            logger.exception(f"Error committing changes: {e}")

        # Return the created playlist folder
        return RekordboxPlaylist.from_rekordbox_playlist(playlist_obj, [])

    def force_commit(self) -> None:
        """Force commit changes to the database, bypassing Rekordbox running check.

        This is a lower-level method that calls commit on our patched database class,
        which already bypasses the Rekordbox running check.
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        # Since we're using PatchedRekordbox6Database, this will bypass the check automatically
        self.db.commit()
        logger.info("Forced commit successful")

    def custom_commit(self, force: bool = False) -> bool:
        """Custom commit method that handles Rekordbox running error.

        Args:
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            True if successful

        Raises:
            RuntimeError: If Rekordbox is running and force=False
            Exception: For other errors
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        try:
            # Since we're using our patched database, force is mostly redundant now
            # But keep the param for backward compatibility
            logger.info(f"Committing changes to Rekordbox database (force={force})")
            # Our PatchedRekordbox6Database commit method automatically bypasses the check
            self.db.commit()
            return True
        except Exception as e:
            logger.exception(f"Error during commit: {e}")
            raise

    def get_playlist_tracks(self, playlist_id: str) -> list[RekordboxTrack]:
        """Get all tracks in a specific playlist.

        Args:
            playlist_id: The platform-specific playlist ID

        Returns:
            A list of platform-specific track objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        playlist = self.get_playlist_by_id(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found")
        return playlist.tracks

    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Add tracks to a playlist on this platform.

        Args:
            playlist_id: The platform-specific playlist ID
            track_ids: List of track IDs to add

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        success = True
        for track_id in track_ids:
            try:
                # Convert string ID to integer for Rekordbox
                track_id_int = int(track_id)
                if not self.add_track_to_playlist(playlist_id, track_id_int):
                    success = False
            except (ValueError, TypeError):
                success = False
        return success

    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Remove tracks from a playlist on this platform.

        Args:
            playlist_id: The platform-specific playlist ID
            track_ids: List of track IDs to remove

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        success = True
        for track_id in track_ids:
            try:
                # Convert string ID to integer for Rekordbox
                track_id_int = int(track_id)
                if not self.remove_track_from_playlist(playlist_id, track_id_int):
                    success = False
            except (ValueError, TypeError):
                success = False
        return success

    def add_track_to_playlist(self, playlist_id: str, track_id: int, force: bool = False) -> bool:
        """Add a track to a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If the client is not authenticated
            RuntimeError: If Rekordbox is running and force=False
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

            # Use our custom commit method
            try:
                self.custom_commit(force=force)
            except RuntimeError:
                # Let the RuntimeError propagate up if it's related to Rekordbox running
                raise
            except Exception as e:
                logger.exception(f"Error committing changes: {e}")
                return False

            return True
        except RuntimeError:
            # Let the RuntimeError propagate up if it's related to Rekordbox running
            raise
        except Exception as e:
            logger.exception(f"Error adding track to playlist: {e}")
            return False

    def remove_track_from_playlist(self, playlist_id: str, track_id: int, force: bool = False) -> bool:
        """Remove a track from a playlist.

        Args:
            playlist_id: The playlist ID
            track_id: The track ID
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If the client is not authenticated
            RuntimeError: If Rekordbox is running and force=False
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
            try:
                self.db.commit()
            except RuntimeError as e:
                error_msg = str(e)
                # Only re-raise for Rekordbox running error, allowing caller to handle with
                # force option
                if "Rekordbox is running" in error_msg and not force:
                    logger.warning(f"Rekordbox is running during commit: {error_msg}")
                    raise RuntimeError("Rekordbox is running. Please close Rekordbox before commiting changes.") from e
                else:
                    # For other errors or if force=True, just log and return False
                    logger.exception(f"Error committing changes: {e}")
                    return False

            return True
        except RuntimeError:
            # Let the RuntimeError propagate up if it's related to Rekordbox running
            raise
        except Exception as e:
            logger.exception(f"Error removing track from playlist: {e}")
            return False

    def import_playlist_to_local(self, rekordbox_playlist_id: str) -> tuple[list[RekordboxTrack], RekordboxPlaylist]:
        """Import a Rekordbox playlist to the local database.

        Args:
            rekordbox_playlist_id: The Rekordbox playlist ID

        Returns:
            Tuple of (list of tracks, playlist object)

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        # Get the playlist details
        playlist = self.get_playlist_by_id(rekordbox_playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with ID {rekordbox_playlist_id} not found")

        # The tracks are already included in the playlist object
        return playlist.tracks, playlist

    def export_tracks_to_playlist(
        self,
        playlist_name: str,
        track_ids: list[str],
        existing_playlist_id: str | None = None,
        parent_folder_id: str | None = None,
        force: bool = False,
    ) -> str:
        """Export tracks to a Rekordbox playlist.

        Args:
            playlist_name: Name for the Rekordbox playlist
            track_ids: List of Rekordbox track IDs to add (as strings)
            existing_playlist_id: Optional ID of an existing playlist to update
            parent_folder_id: Optional parent folder ID (Rekordbox-specific)
            force: If True, attempts to commit even if Rekordbox is running (Rekordbox-specific)

        Returns:
            The Rekordbox playlist ID

        Raises:
            ValueError: If the client is not authenticated
            RuntimeError: If Rekordbox is running and force=False
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        # Convert string IDs to integers
        int_track_ids = []
        for track_id in track_ids:
            try:
                int_track_ids.append(int(track_id))
            except ValueError:
                logger.warning(f"Invalid track ID (non-integer): {track_id}")

        if existing_playlist_id:
            # Update existing playlist
            try:
                # Verify the playlist exists
                existing_playlist = self.get_playlist_by_id(existing_playlist_id)
                if not existing_playlist:
                    raise ValueError(f"Playlist with ID {existing_playlist_id} not found")

                # Add tracks to the existing playlist
                for track_id in int_track_ids:
                    try:
                        self.add_track_to_playlist(existing_playlist_id, track_id, force=force)
                    except Exception as e:
                        logger.warning(f"Failed to add track {track_id} to playlist: {e}")

                return existing_playlist_id
            except Exception as e:
                logger.error(f"Error updating existing playlist: {e}")
                raise ValueError(f"Could not update playlist: {str(e)}") from e
        else:
            # Create a new playlist
            playlist = self.create_playlist(name=playlist_name, parent_id=parent_folder_id, force=force)

            # Add tracks to the playlist
            for track_id in int_track_ids:
                try:
                    self.add_track_to_playlist(playlist.id, track_id, force=force)
                except Exception as e:
                    logger.warning(f"Failed to add track {track_id} to playlist: {e}")

            return playlist.id

    def get_all_folders(self) -> list[tuple[str, str]]:
        """Get all playlist folders in the Rekordbox database.

        Returns:
            List of tuples (folder_id, folder_name)

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        folders = []
        playlist_response = self.db.get_playlist()
        if playlist_response:
            for playlist_obj in playlist_response:
                # Only include folders
                if not hasattr(playlist_obj, "is_folder") or not playlist_obj.is_folder:  # type: ignore
                    continue

                # Add the folder to the list
                folder_id = str(playlist_obj.ID)
                folder_name = playlist_obj.Name
                folders.append((folder_id, folder_name))

        return folders

    def add_track_to_collection(self, file_path: str, force: bool = False) -> int | None:
        """Add a local audio file to the Rekordbox collection.

        Args:
            file_path: Path to the local audio file
            force: If True, attempts to commit even if Rekordbox is running

        Returns:
            Rekordbox track ID if successful, None if failed

        Raises:
            ValueError: If the client is not authenticated
            ValueError: If the track already exists in Rekordbox
            RuntimeError: If Rekordbox is running and force=False
        """
        if not self.db:
            raise ValueError("Rekordbox client not authenticated")

        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File {file_path} does not exist")
            return None

        try:
            # Add the track to Rekordbox collection
            content = self.db.add_content(
                path=file_path,
                # Optionally add more metadata from the file if needed
            )

            # Use our custom commit method
            try:
                self.custom_commit(force=force)
            except RuntimeError:
                # Let the RuntimeError propagate up if it's related to Rekordbox running
                raise
            except Exception as e:
                logger.exception(f"Error committing changes: {e}")
                return None

            # Return the ID of the newly added track
            track_id = int(content.ID)
            logger.info(f"Added track {file_path} to Rekordbox with ID {track_id}")
            return track_id

        except RuntimeError:
            # Let the RuntimeError propagate up if it's related to Rekordbox running
            raise
        except ValueError as e:
            # Track might already exist in collection
            logger.warning(f"Could not add track to Rekordbox: {e}")

            # Try to find the track by path in case it already exists
            try:
                existing_content = self.db.get_content(FolderPath=file_path)
                if existing_content is not None and hasattr(existing_content, "ID"):
                    track_id = int(existing_content.ID)  # type: ignore
                    logger.info(f"Track already exists in Rekordbox with ID {track_id}")
                    return track_id
            except Exception as search_error:
                logger.error(f"Error searching for existing track: {search_error}")

            return None
        except Exception as e:
            logger.exception(f"Error adding track to Rekordbox: {e}")
            return None
