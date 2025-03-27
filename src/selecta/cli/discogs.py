# src/selecta/cli/discogs.py
"""Discogs CLI commands."""

import click
from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.auth import DiscogsAuthManager, validate_discogs_credentials
from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.utils.type_helpers import is_column_truthy


@click.group(name="discogs")
def discogs():
    """Discogs commands for Selecta."""
    pass


@discogs.command(name="setup", help="Set up Discogs API integration")
@click.option(
    "--consumer-key",
    prompt="Enter your Discogs Consumer Key",
    help="Discogs Consumer Key from the Developer Dashboard",
)
@click.option(
    "--consumer-secret",
    prompt="Enter your Discogs Consumer Secret",
    help="Discogs Consumer Secret from the Developer Dashboard",
    hide_input=True,
)
def setup_discogs(consumer_key: str, consumer_secret: str) -> None:
    """Set up Discogs API credentials.

    Args:
        consumer_key: Discogs API consumer key
        consumer_secret: Discogs API consumer secret
    """
    # Validate the credentials
    click.echo("Validating Discogs credentials...")
    if not validate_discogs_credentials(consumer_key, consumer_secret):
        click.secho("Invalid Discogs credentials. Please check and try again.", fg="red")
        return

    # Store the credentials
    settings_repo = SettingsRepository()
    settings_repo.set_credentials(
        "discogs",
        {
            "client_id": consumer_key,
            "client_secret": consumer_secret,
        },
    )

    click.secho("Discogs credentials stored successfully!", fg="green")
    click.echo("To complete authentication, run: selecta discogs auth")


@discogs.command(name="auth", help="Authenticate with Discogs")
def authenticate_discogs() -> None:
    """Authenticate with Discogs using the stored credentials."""
    # Get the auth manager
    settings_repo = SettingsRepository()
    auth_manager = DiscogsAuthManager(settings_repo=settings_repo)

    # Check if we have credentials
    creds = settings_repo.get_credentials("discogs")
    if (
        not creds
        or not is_column_truthy(creds.client_id)
        or not is_column_truthy(creds.client_secret)
    ):
        click.secho(
            "Discogs credentials not found. Please run 'selecta discogs setup' first.",
            fg="red",
        )
        return

    # Start the auth flow
    click.echo("Starting Discogs authentication flow...")
    click.echo("A browser window will open for you to authorize the application.")
    token_info = auth_manager.start_auth_flow()

    if token_info:
        click.secho("Discogs authentication successful!", fg="green")
    else:
        click.secho("Discogs authentication failed. Please try again.", fg="red")


@discogs.command(name="status", help="Check Discogs authentication status")
def check_discogs_status() -> None:
    """Check the status of Discogs authentication."""
    settings_repo = SettingsRepository()
    discogs_client = DiscogsClient(settings_repo=settings_repo)

    # Check if we have credentials
    creds = settings_repo.get_credentials("discogs")
    if (
        not creds
        or not is_column_truthy(creds.client_id)
        or not is_column_truthy(creds.client_secret)
    ):
        click.secho("Discogs API credentials not configured.", fg="yellow")
        click.echo("Run 'selecta discogs setup' to configure Discogs integration.")
        return

    # Check if we're authenticated
    if discogs_client.is_authenticated():
        click.secho("Discogs authentication status: Authenticated", fg="green")

        # Show some user info
        try:
            user_profile = discogs_client.get_user_profile()
            click.echo(f"Connected as: {user_profile['username']}")
            click.echo(f"Discogs user ID: {user_profile['id']}")
        except Exception as e:
            logger.exception(f"Error fetching user profile: {e}")
            click.echo("Could not fetch user profile information.")
    else:
        if is_column_truthy(creds.access_token):
            click.secho("Discogs authentication status: Token expired or invalid", fg="yellow")
            click.echo("Run 'selecta discogs auth' to re-authenticate.")
        else:
            click.secho("Discogs authentication status: Not authenticated", fg="yellow")
            click.echo("Run 'selecta discogs auth' to authenticate with Discogs.")
