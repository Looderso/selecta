"""Spotify CLI commands."""

import click
from loguru import logger

from selecta.data.repositories.settings_repository import SettingsRepository
from selecta.platform.spotify.auth import SpotifyAuthManager, validate_spotify_credentials
from selecta.platform.spotify.client import SpotifyClient


@click.group(name="spotify")
def spotify():
    """Spotify commands for Selecta."""
    pass


@spotify.command(name="setup", help="Set up Spotify API integration")
@click.option(
    "--client-id",
    prompt="Enter your Spotify Client ID",
    help="Spotify Client ID from the Developer Dashboard",
)
@click.option(
    "--client-secret",
    prompt="Enter your Spotify Client Secret",
    help="Spotify Client Secret from the Developer Dashboard",
    hide_input=True,
)
def setup_spotify(client_id: str, client_secret: str) -> None:
    """Set up Spotify API credentials.

    Args:
        client_id: Spotify API client ID
        client_secret: Spotify API client secret
    """
    # Validate the credentials
    click.echo("Validating Spotify credentials...")
    if not validate_spotify_credentials(client_id, client_secret):
        click.secho("Invalid Spotify credentials. Please check and try again.", fg="red")
        return

    # Store the credentials
    settings_repo = SettingsRepository()
    settings_repo.set_credentials(
        "spotify",
        {
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    click.secho("Spotify credentials stored successfully!", fg="green")
    click.echo("To complete authentication, run: selecta spotify auth")


@spotify.command(name="auth", help="Authenticate with Spotify")
def authenticate_spotify() -> None:
    """Authenticate with Spotify using the stored credentials."""
    # Get the auth manager
    settings_repo = SettingsRepository()
    auth_manager = SpotifyAuthManager(settings_repo=settings_repo)

    # Check if we have credentials
    creds = settings_repo.get_credentials("spotify")
    if not creds or not creds.client_id or not creds.client_secret:  # type: ignore
        click.secho(
            "Spotify credentials not found. Please run 'selecta spotify setup' first.",
            fg="red",
        )
        return

    # Start the auth flow
    click.echo("Starting Spotify authentication flow...")
    click.echo("A browser window will open for you to authorize the application.")
    token_info = auth_manager.start_auth_flow()

    if token_info:
        click.secho("Spotify authentication successful!", fg="green")
    else:
        click.secho("Spotify authentication failed. Please try again.", fg="red")


@spotify.command(name="status", help="Check Spotify authentication status")
def check_spotify_status() -> None:
    """Check the status of Spotify authentication."""
    settings_repo = SettingsRepository()
    spotify_client = SpotifyClient(settings_repo=settings_repo)

    # Check if we have credentials
    creds = settings_repo.get_credentials("spotify")
    if not creds or not creds.client_id or not creds.client_secret:  # type: ignore
        click.secho("Spotify API credentials not configured.", fg="yellow")
        click.echo("Run 'selecta spotify setup' to configure Spotify integration.")
        return

    # Check if we're authenticated
    if spotify_client.is_authenticated():
        click.secho("Spotify authentication status: Authenticated", fg="green")

        # Show some user info
        try:
            user_profile = spotify_client.get_user_profile()
            click.echo(f"Connected as: {user_profile['display_name']} ({user_profile['email']})")
            click.echo(f"Spotify user ID: {user_profile['id']}")
        except Exception as e:
            logger.exception(f"Error fetching user profile: {e}")
            click.echo("Could not fetch user profile information.")
    else:
        if creds.access_token:  # type: ignore
            click.secho("Spotify authentication status: Token expired or invalid", fg="yellow")
            click.echo("Run 'selecta spotify auth' to re-authenticate.")
        else:
            click.secho("Spotify authentication status: Not authenticated", fg="yellow")
            click.echo("Run 'selecta spotify auth' to authenticate with Spotify.")
