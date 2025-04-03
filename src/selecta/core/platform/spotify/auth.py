"""Spotify authentication utility functions."""

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

import spotipy
from loguru import logger
from redis import AuthenticationError
from spotipy.oauth2 import SpotifyOAuth

from selecta.config.config_manager import load_platform_credentials
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.utils.type_helpers import is_column_truthy


class SpotifyAuthManager:
    """Handles Spotify authentication and token management."""

    # Default redirect URI for the OAuth flow
    DEFAULT_REDIRECT_URI = "http://localhost:8080"

    # Spotify API scopes needed for the application
    REQUIRED_SCOPES = [
        "user-library-read",
        "user-library-modify",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-public",
        "playlist-modify-private",
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize the Spotify authentication manager.

        Args:
            client_id: Spotify API client ID (can be loaded from .env if None)
            client_secret: Spotify API client secret (can be loaded from .env if None)
            redirect_uri: OAuth redirect URI (defaults to http://localhost:8080)
            settings_repo: Repository for accessing application settings
        """
        self.settings_repo = settings_repo or SettingsRepository()

        # Load credentials from .env if not provided
        if client_id is None or client_secret is None:
            spotify_creds = load_platform_credentials("spotify")
            client_id = client_id or spotify_creds.get("client_id")
            client_secret = client_secret or spotify_creds.get("client_secret")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or self.DEFAULT_REDIRECT_URI

        # Create the Spotify OAuth manager if we have credentials
        self.sp_oauth = None
        if self.client_id and self.client_secret:
            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=" ".join(self.REQUIRED_SCOPES),
                cache_handler=None,  # We'll handle token caching ourselves
            )

    def get_auth_url(self) -> str | None:
        """Get the Spotify authorization URL for the user to visit.

        Returns:
            The authorization URL or None if OAuth is not configured
        """
        if not self.sp_oauth:
            logger.error("Spotify OAuth not configured. Missing client ID or client secret.")
            return None

        return self.sp_oauth.get_authorize_url()

    def start_auth_flow(self) -> dict | None:
        """Start the Spotify OAuth flow and open the browser for authorization.

        This method will:
        1. Open the browser for the user to authorize the app
        2. Start a local HTTP server to catch the callback
        3. Exchange the authorization code for access and refresh tokens
        4. Store the tokens in the application settings

        Returns:
            The token info dict containing access and refresh tokens, or None if failed
        """
        auth_url = self.get_auth_url()
        if not auth_url:
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

        # Start local server to catch the callback
        server = HTTPServer(("localhost", 8080), CallbackHandler)

        def run_server():
            """Run the HTTP server until we receive the authentication code."""
            logger.info("Starting local server to catch Spotify OAuth callback...")
            while not server_closed["closed"] and not code_received["code"]:
                server.handle_request()
            logger.info("OAuth callback server stopped.")

        # Start the server in a separate thread
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Open the browser for the user to authorize
        logger.info("Opening browser for Spotify authorization...")
        webbrowser.open(auth_url)

        # Wait for the user to complete authorization
        server_thread.join(timeout=300)  # Wait up to 5 minutes
        server_closed["closed"] = True

        # Get the authorization code from the callback
        auth_code = code_received["code"]
        if not auth_code:
            logger.error("No authorization code received from Spotify.")
            return None

        # Exchange the code for tokens
        try:
            # With:
            if self.sp_oauth:
                token_info = self.sp_oauth.get_access_token(auth_code)
                # Store tokens in settings
                self._save_tokens(token_info)
                return token_info
            else:
                # Handle the None case
                raise AuthenticationError("Oauth failed.")

        except Exception as e:
            logger.exception(f"Error exchanging Spotify auth code for tokens: {e}")
            return None

    def get_spotify_client(self) -> spotipy.Spotify | None:
        """Get an authenticated Spotify client.

        Returns:
            An authenticated Spotify client or None if authentication fails
        """
        # Check if we have stored credentials
        token_info = self._load_tokens()

        logger.debug(f"Loaded tokens: {token_info is not None}")
        if token_info:
            logger.debug(f"Token info contains access_token: {'access_token' in token_info}")
            logger.debug(f"Token info contains refresh_token: {'refresh_token' in token_info}")

        if not token_info:
            logger.warning("No stored Spotify tokens found.")
            return None

        # Check if we need to refresh the token
        if self.sp_oauth and self.sp_oauth.is_token_expired(token_info):
            logger.info("Spotify access token expired, refreshing...")
            try:
                token_info = self.sp_oauth.refresh_access_token(token_info["refresh_token"])
                self._save_tokens(token_info)
            except Exception as e:
                logger.exception(f"Error refreshing Spotify token: {e}")
                return None

        # Create and return the Spotify client
        spotify = spotipy.Spotify(auth=token_info["access_token"])
        return spotify

    def _save_tokens(self, token_info: dict) -> None:
        """Save Spotify tokens to the application settings."""
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
            result = self.settings_repo.set_credentials("spotify", creds_data)
            logger.debug(f"Token save result: {result is not None}")

            # Verify the save worked by immediately reading back
            verification = self.settings_repo.get_credentials("spotify")
            if verification:
                logger.debug(
                    f"Verification - access_token present: {verification.access_token is not None}"
                )
                logger.debug(
                    f"Verification - refresh_token present:"
                    f" {verification.refresh_token is not None}"
                )
            else:
                logger.warning("Verification failed - couldn't read back saved credentials")
        except Exception as e:
            logger.exception(f"Error saving tokens: {e}")

        logger.info(f"Spotify tokens saved. Expires at: {expires_datetime}")

    def _load_tokens(self) -> dict | None:
        """Load Spotify tokens from the application settings."""
        creds = self.settings_repo.get_credentials("spotify")
        logger.debug(f"Loading tokens for Spotify: credentials found = {creds is not None}")

        if creds:
            logger.debug(f"access_token present: {is_column_truthy(creds.access_token)}")
            logger.debug(f"refresh_token present: {is_column_truthy(creds.refresh_token)}")

        if (
            not creds
            or not is_column_truthy(creds.access_token)
            or not is_column_truthy(creds.refresh_token)
        ):
            return None

        # Convert to the format expected by Spotipy
        expires_at = int(creds.token_expiry.timestamp())

        return {
            "access_token": creds.access_token,
            "refresh_token": creds.refresh_token,
            "expires_at": expires_at,
        }


def validate_spotify_credentials(client_id: str, client_secret: str) -> bool:
    """Validate Spotify API credentials by making a test request.

    Args:
        client_id: Spotify API client ID
        client_secret: Spotify API client secret

    Returns:
        True if the credentials are valid, False otherwise
    """
    if not client_id or not client_secret:
        return False

    try:
        # Create a client credentials manager for validation
        from spotipy.oauth2 import SpotifyClientCredentials

        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )

        # Create a client and make a simple test request
        spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        spotify.artist("4Z8W4fKeB5YxbusRsdQVPb")  # Test with Radiohead's artist ID
        return True
    except Exception as e:
        logger.error(f"Error validating Spotify credentials: {e}")
        return False
