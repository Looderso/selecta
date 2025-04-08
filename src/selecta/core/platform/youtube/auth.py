"""YouTube authentication utility functions."""

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
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
    """Handles YouTube authentication and token management."""

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

        # We'll create the OAuth flow when needed
        self.flow = None

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

        # Start local server to catch the callback
        server = HTTPServer(("localhost", 8080), CallbackHandler)

        def run_server():
            """Run the HTTP server until we receive the authentication code."""
            logger.info("Starting local server to catch YouTube OAuth callback...")
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
        """Get an authenticated YouTube API client.

        Returns:
            An authenticated YouTube API service or None if authentication fails
        """
        # Check if we have stored credentials
        token_info = self._load_tokens()

        if not token_info:
            logger.warning("No stored YouTube tokens found.")
            return None

        try:
            # Create credentials object from token info
            from google.oauth2.credentials import Credentials

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

            # Build and return the YouTube service
            youtube = build("youtube", "v3", credentials=credentials)
            return youtube

        except Exception as e:
            logger.exception(f"Error creating YouTube client: {e}")
            return None

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

        logger.info(f"YouTube tokens saved. Expires at: {expires_datetime}")

    def _load_tokens(self) -> dict | None:
        """Load YouTube tokens from the application settings."""
        creds = self.settings_repo.get_credentials("youtube")
        logger.debug(f"Loading tokens for YouTube: credentials found = {creds is not None}")

        if creds:
            logger.debug(f"access_token present: {is_column_truthy(creds.access_token)}")
            logger.debug(f"refresh_token present: {is_column_truthy(creds.refresh_token)}")

        if (
            not creds
            or not is_column_truthy(creds.access_token)
            or not is_column_truthy(creds.refresh_token)
        ):
            return None

        # Convert to the expected format
        expires_at = int(creds.token_expiry.timestamp())

        return {
            "access_token": creds.access_token,
            "refresh_token": creds.refresh_token,
            "expires_at": expires_at,
        }


def validate_youtube_credentials(client_id: str, client_secret: str) -> bool:
    """Validate YouTube API credentials by making a test request.

    Args:
        client_id: YouTube API client ID
        client_secret: YouTube API client secret

    Returns:
        True if the credentials are valid, False otherwise
    """
    if not client_id or not client_secret:
        return False

    try:
        # Create client config dict from credentials
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        # Make a simple test request with client credentials
        # For YouTube, we can't easily validate without user auth,
        # so we just check if we can create the flow
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/youtube.readonly"],
        )
        return flow is not None
    except Exception as e:
        logger.error(f"Error validating YouTube credentials: {e}")
        return False
