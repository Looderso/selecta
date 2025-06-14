"""YouTube authentication utility functions with improved SSL handling."""

import random
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from ssl import SSLError
from threading import Thread
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from selecta.config.config_manager import load_platform_credentials
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.utils.type_helpers import is_column_truthy


class YouTubeAuthManager:
    """Handles YouTube authentication and token management with improved SSL handling."""

    # Default redirect URI for the OAuth flow
    DEFAULT_REDIRECT_URI = "http://localhost:8080"

    # YouTube API scopes needed for the application
    REQUIRED_SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize the YouTube authentication manager.

        Args:
            client_id: YouTube API client ID (can be loaded from .env if None)
            client_secret: YouTube API client secret (can be loaded from .env if None)
            redirect_uri: OAuth redirect URI (defaults to http://localhost:8080)
            settings_repo: Repository for accessing application settings
        """
        self.settings_repo = settings_repo or SettingsRepository()

        # Load credentials from .env if not provided
        if client_id is None or client_secret is None:
            youtube_creds = load_platform_credentials("youtube")
            client_id = client_id or youtube_creds.get("client_id")
            client_secret = client_secret or youtube_creds.get("client_secret")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or self.DEFAULT_REDIRECT_URI

        # Rate limiting state
        self._last_client_creation_time = 0
        self._min_client_creation_interval = 5.0  # 5 seconds between client creations

        # SSL configuration state
        self._ssl_error_count = 0
        self._max_ssl_retries = 3
        self._current_ssl_level = 0  # 0 = normal, 1 = tolerant, 2 = insecure

        # We'll create the OAuth flow when needed
        self.flow = None

        # Keep track of created clients to ensure proper cleanup
        self._active_clients = set()

    def _create_flow(self) -> InstalledAppFlow | None:
        """Create the OAuth flow for YouTube."""
        if not self.client_id or not self.client_secret:
            logger.error("YouTube OAuth not configured. Missing client ID or client secret.")
            return None

        # Create client config dict from credentials
        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uris": [self.redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        # Create the OAuth flow
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=self.REQUIRED_SCOPES,
            redirect_uri=self.redirect_uri,
        )
        return flow

    def start_auth_flow(self) -> dict | None:
        """Start the YouTube OAuth flow and open the browser for authorization.

        This method will:
        1. Open the browser for the user to authorize the app
        2. Start a local HTTP server to catch the callback
        3. Exchange the authorization code for access and refresh tokens
        4. Store the tokens in the application settings

        Returns:
            The token info dict containing access and refresh tokens, or None if failed
        """
        self.flow = self._create_flow()
        if not self.flow:
            return None

        # Create a server to catch the OAuth callback
        code_received: dict[str, str | None] = {"code": None}
        server_closed = {"closed": False}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                """Handle the OAuth callback GET request."""
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # Extract the code from the query string
                query_components = parse_qs(urlparse(self.path).query)
                if "code" in query_components:
                    code_received["code"] = query_components["code"][0]
                    success_html = """
                    <html>
                    <body>
                        <h1>Authentication Successful!</h1>
                        <p>You can now close this window and return to Selecta.</p>
                        <script>window.close();</script>
                    </body>
                    </html>
                    """
                    self.wfile.write(success_html.encode())
                else:
                    error_html = """
                    <html>
                    <body>
                        <h1>Authentication Failed</h1>
                        <p>Please try again or check the application logs.</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_html.encode())

            def log_message(self, format, *args):
                """Suppress server logs."""
                return

        # Try to find an available port for the callback server
        server = None
        for port in range(8080, 8090):
            try:
                server = HTTPServer(("localhost", port), CallbackHandler)
                # Update the redirect URI with the actual port
                self.redirect_uri = f"http://localhost:{port}"
                break
            except OSError:
                logger.warning(f"Port {port} is in use, trying next port")
                continue

        if not server:
            logger.error("Could not find an available port for YouTube auth callback")
            return None

        def run_server():
            """Run the HTTP server until we receive the authentication code."""
            logger.info(f"Starting local server on port {port} to catch YouTube OAuth callback...")
            while not server_closed["closed"] and not code_received["code"]:
                server.handle_request()
            logger.info("OAuth callback server stopped.")

        # Start the server in a separate thread
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Generate the authorization URL
        auth_url = self.flow.authorization_url(prompt="consent")[0]

        # Open the browser for the user to authorize
        logger.info("Opening browser for YouTube authorization...")
        webbrowser.open(auth_url)

        # Wait for the user to complete authorization
        server_thread.join(timeout=300)  # Wait up to 5 minutes
        server_closed["closed"] = True

        # Get the authorization code from the callback
        auth_code = code_received["code"]
        if not auth_code:
            logger.error("No authorization code received from YouTube.")
            return None

        # Exchange the code for tokens
        try:
            # Set the code on the flow and exchange it for credentials
            self.flow.fetch_token(code=auth_code)
            credentials = self.flow.credentials

            # Format token info like we do with Spotify for consistency
            token_info = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.timestamp(),
            }

            # Store tokens in settings
            self._save_tokens(token_info)
            return token_info

        except Exception as e:
            logger.exception(f"Error exchanging YouTube auth code for tokens: {e}")
            return None

    def get_youtube_client(self):
        """Get an authenticated YouTube API client with rate limiting and progressive SSL fallbacks.

        Returns:
            An authenticated YouTube API service or None if authentication fails
        """
        # Apply rate limiting to client creation
        now = time.time()
        time_since_last = now - self._last_client_creation_time

        if time_since_last < self._min_client_creation_interval:
            sleep_time = self._min_client_creation_interval - time_since_last
            logger.debug(f"Rate limiting YouTube client creation: sleeping for {sleep_time}s")
            time.sleep(sleep_time)

        # Update creation time
        self._last_client_creation_time = time.time()

        # Check if we have stored credentials
        token_info = self._load_tokens()

        if not token_info:
            logger.warning("No stored YouTube tokens found.")
            return None

        # Try to create client with progressively more tolerant SSL settings
        for ssl_level in range(self._current_ssl_level, 3):
            try:
                client = self._create_client_with_ssl_level(token_info, ssl_level)

                if client:
                    # Update the current SSL level if we succeeded with a different level
                    if ssl_level != self._current_ssl_level:
                        logger.info(f"Updated YouTube SSL level from {self._current_ssl_level} to {ssl_level}")
                        self._current_ssl_level = ssl_level

                    # Add to active clients
                    self._active_clients.add(id(client))
                    return client

            except SSLError as e:
                logger.warning(f"SSL error at level {ssl_level}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error creating YouTube client at SSL level {ssl_level}: {e}")
                continue

        logger.error("All SSL levels failed for YouTube client creation")
        return None

    def _create_client_with_ssl_level(self, token_info, ssl_level):
        """Create a YouTube client with specific SSL security level.

        Args:
            token_info: Dictionary with token information
            ssl_level: 0=normal, 1=tolerant, 2=insecure

        Returns:
            YouTube client or None if failed
        """
        import ssl

        import requests
        from google.oauth2.credentials import Credentials
        from googleapiclient.http import HttpRequest
        from requests.adapters import HTTPAdapter
        from urllib3.util import ssl_

        # Create credentials object from token info
        credentials = Credentials(
            token=token_info["access_token"],
            refresh_token=token_info["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        # Check if token is expired and refresh if needed
        if credentials.expired:
            logger.info("YouTube access token expired, refreshing...")
            credentials.refresh(Request())

            # Update token info with refreshed token
            token_info = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.timestamp(),
            }
            self._save_tokens(token_info)

        # Configure SSL based on level
        session = requests.Session()

        if ssl_level == 0:
            # Normal SSL verification with standard settings
            logger.debug("Creating YouTube client with normal SSL verification")
            session.verify = True

        elif ssl_level == 1:
            # Tolerant SSL with custom adapter
            logger.debug("Creating YouTube client with tolerant SSL settings")

            class TolerantSSLAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    context = ssl_.create_urllib3_context(
                        ssl_version=ssl.PROTOCOL_TLS,
                        cert_reqs=ssl.CERT_REQUIRED,
                        options=0x4 | 0x8,  # OP_LEGACY_SERVER_CONNECT | OP_NO_COMPRESSION
                    )
                    # Allow legacy renegotiation for better compatibility
                    context.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
                    kwargs["ssl_context"] = context
                    return super().init_poolmanager(*args, **kwargs)

            session.mount("https://", TolerantSSLAdapter())

        elif ssl_level == 2:
            # Completely insecure - only use as last resort
            logger.warning("Creating YouTube client with SSL verification DISABLED")
            session.verify = False
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Configure discovery cache to avoid network requests during discovery
        try:
            # Build YouTube client with our session and settings
            youtube = build(
                "youtube",
                "v3",
                credentials=credentials,
                requestBuilder=HttpRequest,
                cache_discovery=False,
                static_discovery=True,  # Avoid network calls during discovery
            )

            # Test the client
            try:
                logger.debug("Testing newly created YouTube client")
                # Make a simple test request with backoff
                self._test_request_with_backoff(lambda: youtube.channels().list(part="snippet", mine=True).execute())
                logger.info("YouTube client created and tested successfully")
                return youtube

            except Exception as e:
                logger.warning(f"YouTube client test failed: {e}")
                raise

        except Exception as e:
            logger.error(f"Error building YouTube client: {e}")
            raise

    def _test_request_with_backoff(self, request_func, max_retries=2):
        """Execute a test request with backoff for transient errors.

        Args:
            request_func: Function to execute
            max_retries: Maximum retries

        Returns:
            Response from the request

        Raises:
            Exception if all retries fail
        """
        retries = 0
        while retries <= max_retries:
            try:
                if retries > 0:
                    # Add backoff with jitter
                    sleep_time = (2**retries) + (random.random() * 0.5)
                    logger.debug(f"Test request retry {retries}: sleeping for {sleep_time}s")
                    time.sleep(sleep_time)

                return request_func()

            except Exception as e:
                retries += 1
                logger.warning(f"Test request error, retry {retries}/{max_retries}: {e}")
                if retries > max_retries:
                    raise

        # Should not reach here
        raise RuntimeError("All test request retries failed")

    def cleanup_client(self, client_id):
        """Clean up a YouTube client by ID to prevent resource leaks.

        Args:
            client_id: ID of the client to clean up
        """
        try:
            if client_id in self._active_clients:
                self._active_clients.remove(client_id)
                logger.debug(f"YouTube client {client_id} marked for cleanup")

                # Force garbage collection to clean up resources
                import gc

                gc.collect()

        except Exception as e:
            logger.error(f"Error cleaning up YouTube client: {e}")

    def _save_tokens(self, token_info: dict) -> None:
        """Save YouTube tokens to the application settings."""
        if not token_info:
            logger.warning("No token info to save")
            return

        # Calculate token expiry datetime
        from datetime import UTC, datetime

        expires_at = token_info.get("expires_at", 0)
        expires_datetime = datetime.fromtimestamp(expires_at, tz=UTC)

        # Create a credentials dict with the token info
        creds_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": token_info.get("access_token"),
            "refresh_token": token_info.get("refresh_token"),
            "token_expiry": expires_datetime,
        }

        # Log what we're trying to save
        logger.debug(
            f"Saving tokens: access_token={token_info.get('access_token') is not None}, "
            f"refresh_token={token_info.get('refresh_token') is not None}"
        )

        # Save to settings repository
        try:
            result = self.settings_repo.set_credentials("youtube", creds_data)
            logger.debug(f"Token save result: {result is not None}")

            # Verify the save worked by immediately reading back
            verification = self.settings_repo.get_credentials("youtube")
            if verification:
                logger.debug(f"Verification - access_token present: {verification.access_token is not None}")
                logger.debug(f"Verification - refresh_token present: {verification.refresh_token is not None}")
            else:
                logger.warning("Verification failed - couldn't read back saved credentials")
        except Exception as e:
            logger.exception(f"Error saving tokens: {e}")

        logger.info(f"YouTube tokens saved. Expires at: {expires_datetime}")

    def _load_tokens(self) -> dict | None:
        """Load YouTube tokens from the application settings."""
        try:
            creds = self.settings_repo.get_credentials("youtube")
            logger.debug(f"Loading tokens for YouTube: credentials found = {creds is not None}")

            if creds:
                logger.debug(f"access_token present: {is_column_truthy(creds.access_token)}")
                logger.debug(f"refresh_token present: {is_column_truthy(creds.refresh_token)}")

            if (
                not creds
                or not is_column_truthy(creds.access_token)
                or not is_column_truthy(creds.refresh_token)
                or not hasattr(creds, "token_expiry")
                or creds.token_expiry is None
            ):
                return None

            # Convert to the expected format
            try:
                expires_at = int(creds.token_expiry.timestamp())
            except (AttributeError, ValueError, TypeError):
                # If token_expiry is invalid, use a default expiration of 1 hour from now
                from datetime import UTC, datetime, timedelta

                expires_at = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())

            return {
                "access_token": creds.access_token,
                "refresh_token": creds.refresh_token,
                "expires_at": expires_at,
            }
        except Exception as e:
            logger.exception(f"Error loading YouTube tokens: {e}")
            return None
