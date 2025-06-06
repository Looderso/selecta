"""Discogs authentication utility functions."""

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

import requests
from loguru import logger
from requests_oauthlib import OAuth1

from selecta.config.config_manager import load_platform_credentials
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.api_client import DiscogsApiClient
from selecta.core.utils.type_helpers import column_to_str, is_column_truthy


class DiscogsAuthManager:
    """Handles Discogs authentication and token management."""

    # Discogs API endpoints for OAuth
    REQUEST_TOKEN_URL = "https://api.discogs.com/oauth/request_token"
    AUTHORIZE_URL = "https://www.discogs.com/oauth/authorize"
    ACCESS_TOKEN_URL = "https://api.discogs.com/oauth/access_token"

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize the Discogs authentication manager.

        Args:
            consumer_key: Discogs API consumer key (can be loaded from .env if None)
            consumer_secret: Discogs API consumer secret (can be loaded from .env if None)
            settings_repo: Repository for accessing application settings
        """
        self.settings_repo = settings_repo or SettingsRepository()

        # Load credentials from .env if not provided
        if consumer_key is None or consumer_secret is None:
            discogs_creds = load_platform_credentials("discogs")
            consumer_key = consumer_key or discogs_creds.get("client_id")
            consumer_secret = consumer_secret or discogs_creds.get("client_secret")

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        # Initialize the API client with just the consumer credentials
        self.api_client = DiscogsApiClient(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
        )

    def get_authorize_url(
        self, callback_url: str = "http://localhost:8080"
    ) -> tuple[str, str, str] | None:
        """Get the Discogs authorization URL for the user to visit.

        Args:
            callback_url: OAuth callback URL

        Returns:
            A tuple of (token, secret, url) or None if client is not configured
        """
        if not self.consumer_key or not self.consumer_secret:
            logger.error("Discogs client not configured. Missing consumer key or secret.")
            return None

        try:
            # Create OAuth1 for getting request token (no token/secret yet)
            oauth = OAuth1(
                self.consumer_key,
                client_secret=self.consumer_secret,
                callback_uri=callback_url,
            )

            # Get request token
            response = requests.post(self.REQUEST_TOKEN_URL, auth=oauth)
            response.raise_for_status()

            # Parse response
            credentials = parse_qs(response.text)
            resource_owner_key = credentials.get("oauth_token")[0]
            resource_owner_secret = credentials.get("oauth_token_secret")[0]

            # Generate authorization URL
            authorize_url = f"{self.AUTHORIZE_URL}?oauth_token={resource_owner_key}"

            return resource_owner_key, resource_owner_secret, authorize_url

        except Exception as e:
            logger.exception(f"Error getting Discogs authorization URL: {e}")
            return None

    def start_auth_flow(self) -> dict[str, str] | None:
        """Start the Discogs OAuth flow and open the browser for authorization.

        This method will:
        1. Open the browser for the user to authorize the app
        2. Start a local HTTP server to catch the callback
        3. Exchange the authorization code for access and refresh tokens
        4. Store the tokens in the application settings

        Returns:
            A dict containing the token and secret, or None if failed
        """
        auth_result = self.get_authorize_url()
        if not auth_result:
            return None

        token, secret, auth_url = auth_result

        # Create a server to catch the OAuth callback
        verifier_received: dict[str, str | None] = {"verifier": None}
        server_closed = {"closed": False}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                """Handle the OAuth callback GET request."""
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # Extract the verifier from the query string
                query = urlparse(self.path).query
                query_components = parse_qs(query)

                logger.debug(f"Received callback with query: {query}")

                if "oauth_verifier" in query_components:
                    verifier_received["verifier"] = query_components["oauth_verifier"][0]
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
                        <p>No oauth_verifier found in the callback URL.</p>
                        <p>Please try again or check the application logs.</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_html.encode())
                    logger.error(f"No oauth_verifier in callback query: {query}")

            def log_message(self, format, *args):
                """Suppress server logs."""
                return

        # Start local server to catch the callback
        server = HTTPServer(("localhost", 8080), CallbackHandler)

        def run_server():
            """Run the HTTP server until we receive the authentication verifier."""
            logger.info("Starting local server to catch Discogs OAuth callback...")
            while not server_closed["closed"] and not verifier_received["verifier"]:
                server.handle_request()
            logger.info("OAuth callback server stopped.")

        # Start the server in a separate thread
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Open the browser for the user to authorize
        logger.info("Opening browser for Discogs authorization...")
        webbrowser.open(auth_url)

        # Wait for the user to complete authorization
        server_thread.join(timeout=300)  # Wait up to 5 minutes
        server_closed["closed"] = True

        # Get the verifier from the callback
        verifier = verifier_received["verifier"]
        if not verifier:
            logger.error("No authorization verifier received from Discogs.")
            return None

        logger.debug(f"Received verifier: {verifier}")

        # Exchange the verifier for an access token
        try:
            logger.debug("Exchanging verifier for access token...")

            # Create OAuth1 with the request token and secret
            oauth = OAuth1(
                self.consumer_key,
                client_secret=self.consumer_secret,
                resource_owner_key=token,
                resource_owner_secret=secret,
                verifier=verifier,
            )

            # Exchange for access token
            response = requests.post(self.ACCESS_TOKEN_URL, auth=oauth)
            response.raise_for_status()

            # Parse the response
            credentials = parse_qs(response.text)
            access_token = credentials.get("oauth_token")[0]
            access_secret = credentials.get("oauth_token_secret")[0]

            logger.debug("Access token received successfully")

            # Store tokens in settings
            self._save_tokens(access_token, access_secret)

            return {"token": access_token, "secret": access_secret}
        except Exception as e:
            logger.exception(f"Error exchanging Discogs verifier for tokens: {e}")
            return None

    def get_discogs_client(self) -> DiscogsApiClient | None:
        """Get an authenticated Discogs API client.

        Returns:
            An authenticated DiscogsApiClient or None if authentication fails
        """
        try:
            # Check if we have stored tokens
            stored_tokens = self._load_tokens()
            if (
                not stored_tokens
                or not stored_tokens.get("token")
                or not stored_tokens.get("secret")
            ):
                logger.warning("No stored Discogs tokens found or tokens incomplete")
                return None

            # Create a new client with the stored tokens
            client = DiscogsApiClient(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=stored_tokens["token"],
                access_secret=stored_tokens["secret"],
            )

            # Test the client with a simple request
            if client.is_authenticated():
                logger.debug("Discogs client authenticated successfully")
                return client
            else:
                logger.error("Authentication test failed")
                return None

        except Exception as e:
            logger.exception(f"Error creating Discogs client: {e}")
            return None

    def _save_tokens(self, token: str, secret: str) -> None:
        """Save Discogs tokens to the application settings.

        Args:
            token: The OAuth access token
            secret: The OAuth access token secret
        """
        # Save to settings repository
        self.settings_repo.set_credentials(
            "discogs",
            {
                "client_id": self.consumer_key,
                "client_secret": self.consumer_secret,
                "access_token": token,
                "refresh_token": secret,  # Using refresh_token field to store the secret
            },
        )

        logger.info("Discogs tokens saved.")

    def _load_tokens(self) -> dict[str, str] | None:
        """Load Discogs tokens from the application settings.

        Returns:
            Dictionary with token information or None if not found
        """
        creds = self.settings_repo.get_credentials("discogs")
        if (
            not creds
            or not is_column_truthy(creds.access_token)
            or not is_column_truthy(creds.refresh_token)
        ):
            return None

        return {
            "token": column_to_str(creds.access_token),
            "secret": column_to_str(creds.refresh_token),  # Using refresh_token field as the secret
        }


def validate_discogs_credentials(consumer_key: str, consumer_secret: str) -> bool:
    """Validate Discogs API credentials by making a test request.

    Args:
        consumer_key: Discogs API consumer key
        consumer_secret: Discogs API consumer secret

    Returns:
        True if the credentials are valid, False otherwise
    """
    if not consumer_key or not consumer_secret:
        return False

    try:
        # Create a client with just the consumer credentials (no user auth needed for this test)
        client = DiscogsApiClient(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
        )

        # Try to make a simple search request that doesn't require authentication
        success, _ = client.search_releases(query="test")
        return success
    except Exception as e:
        logger.error(f"Error validating Discogs credentials: {e}")
        return False
