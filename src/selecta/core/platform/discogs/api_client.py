"""Direct Discogs API client implementation."""

import time
from typing import Any

import requests
from loguru import logger
from requests_oauthlib import OAuth1


class DiscogsApiClient:
    """Low-level client for making direct requests to the Discogs API."""

    # Discogs API base URL
    BASE_URL = "https://api.discogs.com"

    # Default user agent for API requests
    USER_AGENT = "SelectaApp/1.0 +https://github.com/Looderso/selecta"

    # Rate limiting settings
    MIN_REQUEST_INTERVAL = 1.0  # Minimum seconds between requests to avoid rate limiting

    _cache = {
        "identity": {"data": None, "timestamp": 0, "valid": False},
        "collection": {"data": None, "timestamp": 0},
        "wantlist": {"data": None, "timestamp": 0},
    }
    _cache_timeout = 300  # 5 minutes

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        access_token: str | None = None,
        access_secret: str | None = None,
    ) -> None:
        """Initialize the Discogs API client.

        Args:
            consumer_key: OAuth consumer key (optional)
            consumer_secret: OAuth consumer secret (optional)
            access_token: OAuth access token (optional)
            access_secret: OAuth access token secret (optional)
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

        # For rate limiting
        self._last_request_time: float = 0.0

        # Add a caching mechanism
        self._identity_cache = None
        self._last_identity_check = 0
        self._identity_cache_timeout = 300  # 5 minutes
        self._request_in_progress = {}

    def _get_auth(self) -> OAuth1 | None:
        """Get OAuth1 authentication object if credentials are available.

        Returns:
            OAuth1 object or None if credentials are not available
        """
        if all([self.consumer_key, self.consumer_secret, self.access_token, self.access_secret]):
            return OAuth1(
                self.consumer_key,
                client_secret=self.consumer_secret,
                resource_owner_key=self.access_token,
                resource_owner_secret=self.access_secret,
            )
        return None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests.

        Returns:
            Dictionary of headers
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }

        # Add token-based authentication if available but not using OAuth1
        if self.access_token and not self._get_auth():
            headers["Authorization"] = f"Discogs token={self.access_token}"

        return headers

    def _respect_rate_limit(self) -> None:
        """Ensure we don't exceed rate limits by waiting if necessary."""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        # If we've made a request recently, wait to avoid rate limiting
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

        # Update the last request time
        self._last_request_time = time.time()

    def _request(
        self, method: str, endpoint: str, params: dict | None = None, data: dict | None = None
    ) -> tuple[bool, Any]:
        """Make a request to the Discogs API with caching and request deduplication.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: URL parameters
            data: Body data for POST requests

        Returns:
            Tuple of (success, response_data)
        """
        # Create a cache key for this request
        cache_key = f"{method}:{endpoint}:{str(params)}"

        # If we're already making this exact request, wait for it to finish
        if hasattr(self, "_request_in_progress") and cache_key in self._request_in_progress:
            logger.debug(f"Request already in progress: {cache_key}")
            # Return a cached result if available
            if endpoint == "/oauth/identity" and self._cache["identity"]["data"]:
                return self._cache["identity"]["valid"], self._cache["identity"]["data"]
            return False, {"error": "Request in progress"}

        # Initialize request tracking dict if it doesn't exist
        if not hasattr(self, "_request_in_progress"):
            self._request_in_progress = {}

        # Mark this request as in progress
        self._request_in_progress[cache_key] = True

        try:
            # Check cache for common endpoints
            current_time = time.time()

            # Handle identity endpoint caching
            if endpoint == "/oauth/identity":
                cache = self._cache["identity"]
                if cache["data"] and (current_time - cache["timestamp"]) < self._cache_timeout:
                    logger.debug("Using cached identity data")
                    self._request_in_progress.pop(cache_key, None)
                    return cache["valid"], cache["data"]

            # Handle collection endpoint caching
            elif "collection/folders" in endpoint and method == "GET":
                cache = self._cache["collection"]
                if cache["data"] and (current_time - cache["timestamp"]) < self._cache_timeout:
                    logger.debug("Using cached collection data")
                    self._request_in_progress.pop(cache_key, None)
                    return True, cache["data"]

            # Handle wantlist endpoint caching
            elif "/wants" in endpoint and method == "GET":
                cache = self._cache["wantlist"]
                if cache["data"] and (current_time - cache["timestamp"]) < self._cache_timeout:
                    logger.debug("Using cached wantlist data")
                    self._request_in_progress.pop(cache_key, None)
                    return True, cache["data"]

            # Respect rate limiting
            self._respect_rate_limit()

            url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            auth = self._get_auth()

            try:
                logger.debug(f"Making {method} request to {url}")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data if method.upper() != "GET" else None,
                    auth=auth,
                )

                # Log rate limit information if provided
                if "X-Discogs-Ratelimit" in response.headers:
                    limit = response.headers.get("X-Discogs-Ratelimit")
                    remaining = response.headers.get("X-Discogs-Ratelimit-Remaining")
                    logger.debug(f"Rate limit: {remaining}/{limit}")

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    # Clear in-progress marker for retry
                    self._request_in_progress.pop(cache_key, None)
                    return self._request(method, endpoint, params, data)

                # Raise exception for other errors
                response.raise_for_status()

                # Cache the results for common endpoints
                if endpoint == "/oauth/identity":
                    self._cache["identity"] = {
                        "data": response.json() if response.status_code == 200 else None,
                        "timestamp": time.time(),
                        "valid": response.status_code == 200,
                    }
                elif (
                    "collection/folders" in endpoint
                    and method == "GET"
                    and response.status_code == 200
                ):
                    self._cache["collection"] = {"data": response.json(), "timestamp": time.time()}
                elif "/wants" in endpoint and method == "GET" and response.status_code == 200:
                    self._cache["wantlist"] = {"data": response.json(), "timestamp": time.time()}

                if response.status_code == 204:
                    # Clear the in-progress flag
                    self._request_in_progress.pop(cache_key, None)
                    return True, None

                # Clear the in-progress flag
                self._request_in_progress.pop(cache_key, None)
                return True, response.json()

            except requests.RequestException as e:
                logger.error(f"API request error: {e}")
                # Clear the in-progress flag in case of error
                self._request_in_progress.pop(cache_key, None)
                return False, {"error": str(e)}

        except Exception as e:
            # Clear the in-progress flag in case of error
            self._request_in_progress.pop(cache_key, None)
            logger.error(f"Unexpected error in API request: {e}")
            return False, {"error": str(e)}

    def is_authenticated(self) -> bool:
        """Test if the client is authenticated with caching."""
        # Check if we have the necessary credentials
        if not self.access_token:
            return False

        # Check our identity cache first
        current_time = time.time()
        if (
            self._cache["identity"]["data"] is not None
            and (current_time - self._cache["identity"]["timestamp"]) < self._cache_timeout
        ):
            return self._cache["identity"]["valid"]

        # Otherwise, make a real request
        success, _ = self.get_identity()
        return success

    def get_identity(self) -> tuple[bool, dict]:
        """Get the current user's identity.

        Returns:
            Tuple of (success, user_data)
        """
        return self._request("GET", "/oauth/identity")

    def search_releases(
        self,
        query: str | None = None,
        artist: str | None = None,
        title: str | None = None,
        release_title: str | None = None,
        label: str | None = None,
        year: int | None = None,
        format: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> tuple[bool, dict]:
        """Search for releases on Discogs.

        Args:
            query: General search query
            artist: Artist name
            title: Track title
            release_title: Release/album title
            label: Record label
            year: Release year
            format: Release format (vinyl, CD, etc.)
            limit: Maximum number of results to return (per page)
            page: Page number for pagination

        Returns:
            Tuple of (success, search_results)
        """
        params = {
            "type": "release",
            "per_page": min(limit, 100),  # Discogs max is 100
            "page": page,
        }

        # Build search query
        if query:
            params["q"] = query

        # Add specific parameters
        if artist:
            params["artist"] = artist
        if title:
            params["track"] = title  # Discogs uses 'track' for the title
        if release_title:
            params["release_title"] = release_title
        if label:
            params["label"] = label
        if year:
            params["year"] = year
        if format:
            params["format"] = format

        return self._request("GET", "/database/search", params=params)

    def get_release(self, release_id: int) -> tuple[bool, dict]:
        """Get a specific release by ID.

        Args:
            release_id: Discogs release ID

        Returns:
            Tuple of (success, release_data)
        """
        return self._request("GET", f"/releases/{release_id}")

    def get_collection_folders(self) -> tuple[bool, dict]:
        """Get the user's collection folders.

        Returns:
            Tuple of (success, folders_data)
        """
        success, identity = self.get_identity()
        if not success:
            return False, identity

        username = identity["username"]
        return self._request("GET", f"/users/{username}/collection/folders")

    def get_collection_items(
        self, folder_id: int = 0, page: int = 1, per_page: int = 100
    ) -> tuple[bool, dict]:
        """Get items in a user's collection folder.

        Args:
            folder_id: Collection folder ID (0 = all)
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            Tuple of (success, collection_data)
        """
        success, identity = self.get_identity()
        if not success:
            return False, identity

        username = identity["username"]
        return self._request(
            "GET",
            f"/users/{username}/collection/folders/{folder_id}/releases",
            params={"page": page, "per_page": per_page},
        )

    def get_all_collection_items(self, folder_id: int = 0) -> tuple[bool, list[dict]]:
        """Get all items in a user's collection folder with automatic pagination.

        Args:
            folder_id: Collection folder ID (0 = all)

        Returns:
            Tuple of (success, all_collection_items)
        """
        all_items = []
        page = 1
        has_more = True

        while has_more:
            success, response = self.get_collection_items(folder_id, page)
            if not success:
                return False, all_items

            items = response.get("releases", [])
            all_items.extend(items)

            # Check if there are more pages
            pagination = response.get("pagination", {})
            pages = pagination.get("pages", 0)
            if page >= pages:
                has_more = False
            page += 1

        return True, all_items

    def get_wantlist(self, page: int = 1, per_page: int = 100) -> tuple[bool, dict]:
        """Get the user's wantlist.

        Args:
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            Tuple of (success, wantlist_data)
        """
        success, identity = self.get_identity()
        if not success:
            return False, identity

        username = identity["username"]
        return self._request(
            "GET",
            f"/users/{username}/wants",
            params={"page": page, "per_page": per_page},
        )

    def get_all_wantlist_items(self) -> tuple[bool, list[dict]]:
        """Get all items in a user's wantlist with automatic pagination.

        Returns:
            Tuple of (success, all_wantlist_items)
        """
        all_items = []
        page = 1
        has_more = True

        while has_more:
            success, response = self.get_wantlist(page)
            if not success:
                return False, all_items

            items = response.get("wants", [])
            all_items.extend(items)

            # Check if there are more pages
            pagination = response.get("pagination", {})
            pages = pagination.get("pages", 0)
            if page >= pages:
                has_more = False
            page += 1

        return True, all_items
