"""YouTube API client for accessing YouTube data with improved SSL error handling."""

import contextlib
import random
import time
from collections.abc import Callable
from ssl import SSLError
from typing import Any

from googleapiclient.errors import HttpError
from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.abstract_platform import AbstractPlatform
from selecta.core.platform.youtube.auth import YouTubeAuthManager
from selecta.core.platform.youtube.models import YouTubePlaylist, YouTubeVideo


class YouTubeClient(AbstractPlatform):
    """Client for interacting with the YouTube API with improved error handling."""

    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        """Initialize the YouTube client.

        Args:
            settings_repo: Repository for accessing settings (optional)
        """
        super().__init__(settings_repo)
        self.auth_manager = YouTubeAuthManager(settings_repo=self.settings_repo)
        self.client = None
        self._had_ssl_error = False
        self._error_count = 0
        self._max_retries = 3

        # Rate limiting state
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms minimum between requests
        self._request_count = 0
        self._max_requests_per_minute = 60  # YouTube API typically allows ~60 requests per minute

        # Try to initialize the client if we have valid credentials
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the YouTube client with stored credentials."""
        try:
            # Important: set client to None first to avoid memory corruption issues
            # when reinitializing after SSL errors
            old_client = self.client
            old_client_id = id(old_client) if old_client else None

            self.client = None

            # Clean up old client via auth manager
            if old_client and old_client_id:
                self.auth_manager.cleanup_client(old_client_id)

            # Force garbage collection to clean up old client references
            import gc

            gc.collect()

            # Get a fresh client instance
            self.client = self.auth_manager.get_youtube_client()

            if self.client:
                logger.info("YouTube client initialized successfully")
                # Reset counters on successful initialization
                self._had_ssl_error = False
                self._error_count = 0
                self._request_count = 0
            else:
                logger.warning("No valid YouTube credentials found")
        except Exception as e:
            logger.exception(f"Failed to initialize YouTube client: {e}")
            self.client = None

    def _execute_with_rate_limiting(self, request_func: Callable) -> Any:
        """Execute a YouTube API request with rate limiting.

        Args:
            request_func: Function that returns a YouTube request object

        Returns:
            The result of the request

        Raises:
            Various exceptions from the request
        """
        # Calculate time since last request
        now = time.time()
        time_since_last = now - self._last_request_time

        # Apply the rate limiting
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
            time.sleep(sleep_time)

        # Apply quota-based throttling if we're approaching the limit
        if self._request_count >= self._max_requests_per_minute:
            # Calculate how long to wait for next minute window
            elapsed_since_first = now - (self._last_request_time - (self._request_count * self._min_request_interval))
            if elapsed_since_first < 60:
                sleep_time = 60 - elapsed_since_first + (random.random() * 0.5)  # Add jitter
                logger.info(f"Approaching quota limit: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                # Reset the counter
                self._request_count = 0

        # Execute the request
        try:
            request = request_func()
            response = request.execute()

            # Update rate limiting state
            self._last_request_time = time.time()
            self._request_count += 1

            return response

        except SSLError as e:
            # Handle SSL errors by incrementing error count and retrying
            self._had_ssl_error = True
            self._error_count += 1

            logger.warning(f"SSL error in YouTube request (count: {self._error_count}): {e}")

            # If we've hit max retries for this client instance, reinitialize
            if self._error_count >= self._max_retries:
                logger.warning("Max SSL error retries reached, reinitializing YouTube client")
                self._initialize_client()
                raise ValueError("YouTube client encountered too many SSL errors and was reinitialized") from e

            # Otherwise, propagate the error for retry
            raise

        except Exception as e:
            # For other errors, just raise
            logger.error(f"Error in YouTube request: {e}")
            raise

    def _execute_with_retries(self, request_func: Callable, max_retries: int = 3) -> Any:
        """Execute a YouTube API request with retries for transient errors.

        Args:
            request_func: Function that returns a YouTube request object
            max_retries: Maximum number of retries

        Returns:
            The result of the request

        Raises:
            ValueError: If all retries fail
        """
        last_error = None
        for retry in range(max_retries + 1):  # +1 for the initial attempt
            try:
                if retry > 0:
                    # Exponential backoff with jitter
                    sleep_time = (2**retry) + (random.random() * 0.5)
                    logger.debug(f"Retry {retry}/{max_retries}: sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)

                return self._execute_with_rate_limiting(request_func)

            except SSLError as e:
                last_error = e
                logger.warning(f"SSL error, retry {retry}/{max_retries}: {e}")

                # If this was the last retry, reinitialize before giving up
                if retry == max_retries:
                    logger.warning("Max SSL retries reached, reinitializing client")
                    self._initialize_client()

            except HttpError as e:
                # Only retry certain HTTP errors
                if e.resp.status in (429, 500, 502, 503, 504):
                    last_error = e
                    logger.warning(f"Retryable HTTP error {e.resp.status}, retry {retry}/{max_retries}: {e}")
                else:
                    # Don't retry client errors
                    logger.error(f"Non-retryable HTTP error {e.resp.status}: {e}")
                    raise ValueError(f"YouTube API error: {e}") from e

            except Exception as e:
                # Don't retry other exceptions
                logger.error(f"Non-retryable error: {e}")
                raise ValueError(f"YouTube API error: {e}") from e

        # If we got here, all retries failed
        error_msg = f"All {max_retries} retries failed for YouTube request"
        if last_error:
            error_msg += f": {last_error}"

        logger.error(error_msg)
        raise ValueError(error_msg)

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated with valid credentials.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.client:
            return False

        # If we've reached max error count, return False and reinitialize
        if self._error_count >= self._max_retries:
            logger.warning("Max error count reached, reinitializing YouTube client")
            self._initialize_client()
            return self.client is not None

        # Simple check - just test if we have a client
        return True

    def authenticate(self) -> bool:
        """Perform the YouTube OAuth flow to authenticate the user.

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
            logger.exception(f"YouTube authentication failed: {e}")
            return False

    def get_channel_info(self) -> dict[str, Any]:
        """Get the current user's YouTube channel information.

        Returns:
            Dictionary with channel information

        Raises:
            ValueError: If the client is not authenticated
            ValueError: If the channel information is not available
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:

            def request_func():
                return self.client.channels().list(part="snippet,contentDetails,statistics", mine=True)

            response = self._execute_with_retries(request_func)

            if not response or "items" not in response or not response["items"]:
                raise ValueError("YouTube: channel information not available")

            return response["items"][0]
        except Exception as e:
            logger.error(f"Error fetching YouTube channel info: {e}")
            raise ValueError(f"Error fetching YouTube channel info: {str(e)}") from e

    def get_all_playlists(self) -> list[YouTubePlaylist]:
        """Get all playlists from this platform.

        Returns:
            A list of platform-specific playlist objects

        Raises:
            ValueError: If not authenticated or API error occurs
        """
        return self.get_playlists()

    def get_playlists(self) -> list[YouTubePlaylist]:
        """Get all playlists for the current user.

        Returns:
            List of YouTubePlaylist objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        playlists = []
        next_page_token = None

        try:
            while True:

                def request_func(token=next_page_token):
                    return self.client.playlists().list(
                        part="snippet,contentDetails,status",
                        mine=True,
                        maxResults=50,
                        pageToken=token,
                    )

                response = self._execute_with_retries(request_func)

                for item in response.get("items", []):
                    playlist = YouTubePlaylist.from_youtube_dict(item)
                    playlists.append(playlist)

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            return playlists
        except Exception as e:
            logger.error(f"Error fetching YouTube playlists: {e}")
            raise ValueError(f"Error fetching YouTube playlists: {str(e)}") from e

    def get_playlist_tracks(self, playlist_id: str) -> list[YouTubeVideo]:
        """Get all videos in a specified playlist.

        Args:
            playlist_id: The YouTube playlist ID

        Returns:
            List of YouTubeVideo objects

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        videos = []
        next_page_token = None

        try:
            # First, get the playlist items
            while True:

                def playlist_items_request(token=next_page_token):
                    return self.client.playlistItems().list(
                        part="snippet,contentDetails",
                        playlistId=playlist_id,
                        maxResults=50,
                        pageToken=token,
                    )

                playlist_items_response = self._execute_with_retries(playlist_items_request)

                # Extract video IDs
                video_ids = []
                playlist_items = []
                for item in playlist_items_response.get("items", []):
                    video_id = item.get("contentDetails", {}).get("videoId")
                    if video_id:
                        video_ids.append(video_id)
                        playlist_items.append(item)

                # Get detailed video information in batches of 50
                if video_ids:

                    def videos_request(ids=video_ids):
                        return self.client.videos().list(part="snippet,contentDetails,statistics", id=",".join(ids))

                    videos_response = self._execute_with_retries(videos_request)

                    # Create YouTubeVideo objects with added_at information
                    for video_item in videos_response.get("items", []):
                        video_id = video_item.get("id")

                        # Find the matching playlist item to get added_at and playlist_item_id
                        added_at = None
                        playlist_item_id = None
                        for playlist_item in playlist_items:
                            if playlist_item.get("contentDetails", {}).get("videoId") == video_id:
                                playlist_item_id = playlist_item.get(
                                    "id"
                                )  # This is the playlist item ID we need for removal
                                snippet = playlist_item.get("snippet", {})
                                if "publishedAt" in snippet:
                                    from datetime import datetime

                                    with contextlib.suppress(ValueError, TypeError):
                                        added_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                                break

                        video = YouTubeVideo.from_youtube_dict(
                            video_item, added_at=added_at, playlist_item_id=playlist_item_id
                        )
                        videos.append(video)

                next_page_token = playlist_items_response.get("nextPageToken")
                if not next_page_token:
                    break

            return videos
        except HttpError as e:
            logger.error(f"Error fetching YouTube playlist videos: {e}")
            raise ValueError(f"Error fetching YouTube playlist videos: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error fetching YouTube playlist videos: {e}")
            raise ValueError(f"Error fetching YouTube playlist videos: {str(e)}") from e

    def get_playlist(self, playlist_id: str) -> YouTubePlaylist:
        """Get detailed information about a playlist.

        Args:
            playlist_id: The YouTube playlist ID

        Returns:
            YouTubePlaylist object

        Raises:
            ValueError: If the client is not authenticated
            ValueError: No playlist available.
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:

            def playlist_request():
                return self.client.playlists().list(part="snippet,contentDetails,status", id=playlist_id)

            response = self._execute_with_retries(playlist_request)

            if not response or "items" not in response or not response["items"]:
                raise ValueError("No playlist available.")

            return YouTubePlaylist.from_youtube_dict(response["items"][0])
        except HttpError as e:
            logger.error(f"Error fetching YouTube playlist: {e}")
            raise ValueError(f"Error fetching YouTube playlist: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error fetching YouTube playlist: {e}")
            raise ValueError(f"Error fetching YouTube playlist: {str(e)}") from e

    def create_playlist(
        self,
        name: str,
        description: str = "",
        privacy_status: str = "private",
    ) -> YouTubePlaylist:
        """Create a new playlist for the current user.

        Args:
            name: The name of the playlist
            description: Optional description for the playlist
            privacy_status: Privacy status ("public", "private", "unlisted")

        Returns:
            YouTubePlaylist object for the new playlist

        Raises:
            ValueError: If the client is not authenticated
            ValueError: Playlist creation failed.
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:
            # Create the playlist
            def create_playlist_request():
                return self.client.playlists().insert(
                    part="snippet,status",
                    body={
                        "snippet": {"title": name, "description": description},
                        "status": {"privacyStatus": privacy_status},
                    },
                )

            response = self._execute_with_retries(create_playlist_request)

            if not response:
                raise ValueError("Playlist creation failed.")

            return YouTubePlaylist.from_youtube_dict(response)
        except HttpError as e:
            logger.error(f"Error creating YouTube playlist: {e}")
            raise ValueError(f"Error creating YouTube playlist: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error creating YouTube playlist: {e}")
            raise ValueError(f"Error creating YouTube playlist: {str(e)}") from e

    def add_tracks_to_playlist(self, playlist_id: str, video_ids: list[str]) -> bool:
        """Add videos to a playlist.

        Args:
            playlist_id: The YouTube playlist ID
            video_ids: List of YouTube video IDs to add

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        if not video_ids:
            return True  # Nothing to add

        try:
            for video_id in video_ids:

                def add_video_request(vid=video_id):
                    return self.client.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {"kind": "youtube#video", "videoId": vid},
                            }
                        },
                    )

                self._execute_with_retries(add_video_request)

            return True
        except HttpError as e:
            logger.error(f"Error adding videos to YouTube playlist: {e}")
            raise ValueError(f"Error adding videos to YouTube playlist: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error adding videos to YouTube playlist: {e}")
            raise ValueError(f"Error adding videos to YouTube playlist: {str(e)}") from e

    def remove_tracks_from_playlist(self, playlist_id: str, playlist_item_ids: list[str]) -> bool:
        """Remove videos from a playlist.

        Args:
            playlist_id: The YouTube playlist ID
            playlist_item_ids: List of YouTube playlist item IDs to remove

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        if not playlist_item_ids:
            return True  # Nothing to remove

        try:
            for item_id in playlist_item_ids:

                def remove_item_request(item=item_id):
                    return self.client.playlistItems().delete(id=item)

                self._execute_with_retries(remove_item_request)

            return True
        except HttpError as e:
            logger.error(f"Error removing videos from YouTube playlist: {e}")
            raise ValueError(f"Error removing videos from YouTube playlist: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error removing videos from YouTube playlist: {e}")
            raise ValueError(f"Error removing videos from YouTube playlist: {str(e)}") from e

    def update_playlist_details(
        self,
        playlist_id: str,
        title: str | None = None,
        description: str | None = None,
        privacy_status: str | None = None,
    ) -> bool:
        """Update a playlist's details.

        Args:
            playlist_id: The YouTube playlist ID
            title: New title for the playlist (optional)
            description: New description for the playlist (optional)
            privacy_status: New privacy status (optional)

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:
            # Get the current playlist details
            playlist = self.get_playlist(playlist_id)

            # Prepare the update data
            body = {
                "id": playlist_id,
                "snippet": {
                    "title": title or playlist.title,
                    "description": description if description is not None else playlist.description,
                },
                "status": {"privacyStatus": privacy_status or playlist.privacy_status},
            }

            def update_playlist_request():
                return self.client.playlists().update(part="snippet,status", body=body)

            self._execute_with_retries(update_playlist_request)

            return True
        except HttpError as e:
            logger.error(f"Error updating YouTube playlist: {e}")
            raise ValueError(f"Error updating YouTube playlist: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error updating YouTube playlist: {e}")
            raise ValueError(f"Error updating YouTube playlist: {str(e)}") from e

    def search_tracks(self, query: str, limit: int = 10) -> list[dict]:
        """Search for videos on YouTube.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of video data dictionaries

        Raises:
            ValueError: If the client is not authenticated
            ValueError: Search failed.
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:

            def search_request():
                return self.client.search().list(part="snippet", q=query, type="video", maxResults=limit)

            response = self._execute_with_retries(search_request)

            if not response:
                raise ValueError("Search failed.")

            videos = []
            video_ids = []

            # Get video IDs from search results
            for item in response.get("items", []):
                if item.get("id", {}).get("kind") == "youtube#video":
                    video_ids.append(item.get("id", {}).get("videoId"))
                    videos.append(item)

            # If we have video IDs, get additional details
            if video_ids:

                def details_request():
                    return self.client.videos().list(part="contentDetails,statistics", id=",".join(video_ids))

                details_response = self._execute_with_retries(details_request)

                # Merge the detailed data with search results
                for item in videos:
                    video_id = item.get("id", {}).get("videoId")
                    for detail_item in details_response.get("items", []):
                        if detail_item.get("id") == video_id:
                            item["contentDetails"] = detail_item.get("contentDetails", {})
                            item["statistics"] = detail_item.get("statistics", {})
                            break

            return videos
        except HttpError as e:
            logger.error(f"Error searching YouTube videos: {e}")
            raise ValueError(f"Error searching YouTube videos: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {e}")
            raise ValueError(f"Error searching YouTube videos: {str(e)}") from e

    def import_playlist_to_local(self, youtube_playlist_id: str) -> tuple[list[YouTubeVideo], YouTubePlaylist]:
        """Import a YouTube playlist to the local database.

        Args:
            youtube_playlist_id: The YouTube playlist ID

        Returns:
            Tuple of (list of videos, playlist object)

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        # Get the playlist details
        playlist = self.get_playlist(youtube_playlist_id)

        # Get all videos in the playlist
        videos = self.get_playlist_tracks(youtube_playlist_id)

        return videos, playlist

    def export_tracks_to_playlist(
        self, playlist_name: str, video_ids: list[str], existing_playlist_id: str | None = None
    ) -> str:
        """Export videos to a YouTube playlist.

        Args:
            playlist_name: Name for the YouTube playlist
            video_ids: List of YouTube video IDs to add
            existing_playlist_id: Optional ID of an existing playlist to update

        Returns:
            The YouTube playlist ID

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        if existing_playlist_id:
            # Update existing playlist
            try:
                # Check if playlist exists
                self.get_playlist(existing_playlist_id)
                # Add videos to the existing playlist
                if video_ids:
                    self.add_tracks_to_playlist(existing_playlist_id, video_ids)
                return existing_playlist_id
            except Exception as e:
                logger.error(f"Error updating existing playlist: {e}")
                raise ValueError(f"Could not update playlist: {str(e)}") from e
        else:
            # Create a new playlist
            playlist = self.create_playlist(name=playlist_name, privacy_status="private")

            # Add videos to the playlist
            if video_ids:
                self.add_tracks_to_playlist(playlist.id, video_ids)

            return playlist.id

    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a YouTube playlist.

        Args:
            playlist_id: The YouTube playlist ID

        Returns:
            True if successful

        Raises:
            ValueError: If the client is not authenticated
        """
        if not self.client:
            raise ValueError("YouTube client not authenticated")

        try:

            def delete_request():
                return self.client.playlists().delete(id=playlist_id)

            self._execute_with_retries(delete_request)
            logger.info(f"Deleted YouTube playlist: {playlist_id}")
            return True
        except HttpError as e:
            logger.error(f"Error deleting YouTube playlist {playlist_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting YouTube playlist {playlist_id}: {e}")
            return False
