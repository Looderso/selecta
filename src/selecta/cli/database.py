"""Database CLI commands."""

import os
from pathlib import Path

import click
from loguru import logger

from selecta.core.data.init_db import initialize_database
from selecta.core.utils.path_helper import get_app_data_path


@click.group(name="database")
def database():
    """Database management commands for Selecta."""
    pass


@database.command(name="init", help="Initialize a new database")
@click.option(
    "--force/--no-force",
    default=False,
    help="Force database creation even if one already exists",
)
@click.option(
    "--path",
    type=click.Path(),
    help="Custom database path (default: app data directory)",
)
def init_db(force: bool, path: str | None) -> None:
    """Initialize a new Selecta database.

    Args:
        force: Whether to force initialization if database already exists
        path: Optional custom database path
    """
    db_path = Path(path) if path else get_app_data_path() / "selecta.db"

    # Check if database already exists
    if db_path.exists() and not force:
        click.secho(f"Database already exists at {db_path}", fg="yellow")
        if not click.confirm("Do you want to reinitialize the database? All data will be lost."):
            click.echo("Database initialization cancelled.")
            return

    # Initialize the database
    try:
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        click.echo(f"Initializing database at {db_path}")
        initialize_database(db_path)
        click.secho("Database initialized successfully!", fg="green")
    except Exception as e:
        logger.exception(f"Error initializing database: {e}")
        click.secho(f"Error initializing database: {e}", fg="red")


@database.command(name="remove", help="Remove the database")
@click.option(
    "--path",
    type=click.Path(exists=True),
    help="Custom database path (default: app data directory)",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def remove_db(path: str | None, yes: bool) -> None:
    """Remove the Selecta database.

    Args:
        path: Optional custom database path
        yes: Skip confirmation prompt if set
    """
    db_path = Path(path) if path else get_app_data_path() / "selecta.db"

    # Check if database exists
    if not db_path.exists():
        click.secho(f"No database found at {db_path}", fg="yellow")
        return

    # Confirm deletion
    if not yes and not click.confirm(
        f"Are you sure you want to remove the database at {db_path}? This cannot be undone.",
        default=False,
    ):
        click.echo("Database removal cancelled.")
        return

    # Remove the database
    try:
        os.remove(db_path)
        click.secho(f"Database at {db_path} removed successfully!", fg="green")

        # Also remove journal and WAL files if they exist
        wal_path = db_path.with_suffix(".db-wal")
        if wal_path.exists():
            os.remove(wal_path)
            click.echo(f"Removed WAL file at {wal_path}")

        shm_path = db_path.with_suffix(".db-shm")
        if shm_path.exists():
            os.remove(shm_path)
            click.echo(f"Removed SHM file at {shm_path}")

        journal_path = db_path.with_name(f"{db_path.name}-journal")
        if journal_path.exists():
            os.remove(journal_path)
            click.echo(f"Removed journal file at {journal_path}")

    except Exception as e:
        logger.exception(f"Error removing database: {e}")
        click.secho(f"Error removing database: {e}", fg="red")
