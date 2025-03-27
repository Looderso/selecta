"""Rekordbox CLI commands."""

import click
from loguru import logger

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.rekordbox.auth import RekordboxAuthManager
from selecta.core.platform.rekordbox.client import RekordboxClient


@click.group(name="rekordbox")
def rekordbox():
    """Rekordbox commands for Selecta."""
    pass


@rekordbox.command(name="setup", help="Set up Rekordbox database access")
@click.option(
    "--key",
    prompt="Enter your Rekordbox database key",
    help="Rekordbox database decryption key",
)
def setup_rekordbox(key: str) -> None:
    """Set up Rekordbox database key.

    Args:
        key: Rekordbox database decryption key
    """
    # Validate the key format (basic check)
    if not key.startswith("402fd"):
        click.secho("The key doesn't look like a valid Rekordbox key.", fg="red")
        if not click.confirm("Continue anyway?", default=False):
            return

    # Store the key
    settings_repo = SettingsRepository()
    auth_manager = RekordboxAuthManager(settings_repo=settings_repo)

    if auth_manager.store_key(key):
        click.secho("Rekordbox database key stored successfully!", fg="green")

        # Test connection
        rekordbox_client = RekordboxClient(settings_repo=settings_repo)
        if rekordbox_client.is_authenticated():
            click.secho("Successfully connected to Rekordbox database!", fg="green")
        else:
            click.secho("Could not connect to Rekordbox database with the provided key.", fg="red")
    else:
        click.secho("Failed to store Rekordbox database key.", fg="red")


@rekordbox.command(name="download-key", help="Download Rekordbox database key")
def download_rekordbox_key() -> None:
    """Download Rekordbox database key using pyrekordbox."""
    click.echo("Downloading Rekordbox database key...")

    # Create auth manager and try to download key
    settings_repo = SettingsRepository()
    auth_manager = RekordboxAuthManager(settings_repo=settings_repo)

    key = auth_manager.download_key()

    if key:
        click.secho(f"Rekordbox database key downloaded successfully: {key}", fg="green")

        # Test connection
        rekordbox_client = RekordboxClient(settings_repo=settings_repo)
        if rekordbox_client.is_authenticated():
            click.secho("Successfully connected to Rekordbox database!", fg="green")
        else:
            click.secho(
                "Could not connect to Rekordbox database with the downloaded key.", fg="red"
            )
    else:
        click.secho("Failed to download Rekordbox database key.", fg="red")
        click.echo("You can try to download the key manually using:")
        click.echo("python -m pyrekordbox download-key")
        click.echo("Then use 'selecta rekordbox setup' to set the key.")


@rekordbox.command(name="status", help="Check Rekordbox connection status")
def check_rekordbox_status() -> None:
    """Check the status of Rekordbox connection."""
    settings_repo = SettingsRepository()
    rekordbox_client = RekordboxClient(settings_repo=settings_repo)

    # Check if we have credentials
    auth_manager = RekordboxAuthManager(settings_repo=settings_repo)
    key = auth_manager.get_stored_key()

    if not key:
        click.secho("Rekordbox database key not configured.", fg="yellow")
        click.echo(
            "Run 'selecta rekordbox setup' or 'selecta rekordbox download-key' to "
            "configure Rekordbox integration."
        )
        return

    # Check if we can connect to the database
    if rekordbox_client.is_authenticated():
        click.secho("Rekordbox database status: Connected", fg="green")

        # Show some database info
        try:
            track_count = len(rekordbox_client.get_all_tracks())
            playlist_count = len(rekordbox_client.get_all_playlists())
            click.echo(
                f"Rekordbox database contains {track_count} tracks "
                f"and {playlist_count} playlists/folders"
            )
        except Exception as e:
            logger.exception(f"Error fetching Rekordbox database info: {e}")
            click.echo("Could not fetch Rekordbox database information.")
    else:
        click.secho("Rekordbox database status: Not connected", fg="yellow")
        click.echo(
            "Run 'selecta rekordbox setup' or 'selecta rekordbox download-key' "
            "to configure Rekordbox integration."
        )


@rekordbox.command(name="list-playlists", help="List Rekordbox playlists")
def list_rekordbox_playlists() -> None:
    """List all playlists in the Rekordbox database."""
    settings_repo = SettingsRepository()
    rekordbox_client = RekordboxClient(settings_repo=settings_repo)

    # Check if we can connect to the database
    if not rekordbox_client.is_authenticated():
        click.secho("Not connected to Rekordbox database.", fg="red")
        click.echo(
            "Run 'selecta rekordbox setup' or 'selecta rekordbox download-key' to "
            "configure Rekordbox integration."
        )
        return

    # Get all playlists
    try:
        playlists = rekordbox_client.get_all_playlists()

        if not playlists:
            click.echo("No playlists found in Rekordbox database.")
            return

        # Create a tree structure
        playlist_map = {pl.id: pl for pl in playlists}
        # Add root for top-level playlists
        playlist_map["root"] = None  # type: ignore

        # Group playlists by parent
        children = {}
        for pl in playlists:
            if pl.parent_id not in children:
                children[pl.parent_id] = []
            children[pl.parent_id].append(pl)

        # Helper function to print tree
        def print_tree(parent_id, indent=0):
            if parent_id not in children:
                return

            for pl in sorted(children[parent_id], key=lambda x: x.position):
                prefix = "📁 " if pl.is_folder else "📄 "
                track_count = f" ({len(pl.tracks)} tracks)" if not pl.is_folder else ""
                click.echo(f"{'  ' * indent}{prefix}{pl.name}{track_count}")

                if pl.is_folder and pl.id in children:
                    print_tree(pl.id, indent + 1)

        click.secho("Rekordbox Playlists:", fg="green")
        print_tree("root")

    except Exception as e:
        logger.exception(f"Error listing Rekordbox playlists: {e}")
        click.secho(f"Error listing Rekordbox playlists: {e}", fg="red")
