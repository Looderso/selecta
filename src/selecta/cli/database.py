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
@click.option(
    "--keep-auth/--no-keep-auth",
    default=False,
    help="Preserve platform authentication credentials when reinitializing",
)
def init_db(force: bool, path: str | None, keep_auth: bool) -> None:
    """Initialize a new Selecta database.

    Args:
        force: Whether to force initialization if database already exists
        path: Optional custom database path
        keep_auth: Whether to preserve platform authentication credentials
    """
    import sqlite3

    from sqlalchemy import text

    from selecta.core.data.database import get_engine

    db_path = Path(path) if path else get_app_data_path() / "selecta.db"

    # Check if database already exists
    if db_path.exists() and not force:
        click.secho(f"Database already exists at {db_path}", fg="yellow")
        if not click.confirm("Do you want to reinitialize the database? All data will be lost."):
            click.echo("Database initialization cancelled.")
            return

    # Backup authentication if requested
    auth_backup = None
    if keep_auth and db_path.exists():
        try:
            click.echo("Backing up platform authentication credentials...")

            # Connect to existing database
            engine = get_engine(db_path)
            with engine.connect() as conn:
                # Check if platform_credentials table exists
                result = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name='platform_credentials'"
                    )
                )
                if result.fetchone():
                    # Get all platform credentials
                    result = conn.execute(text("SELECT * FROM platform_credentials"))
                    rows = result.fetchall()

                    if rows:
                        # Convert to dictionary format
                        auth_backup = []
                        for row in rows:
                            # Get column names from result
                            columns = result.keys()
                            auth_data = {col: row[idx] for idx, col in enumerate(columns)}
                            auth_backup.append(auth_data)

                        click.echo(f"Backed up credentials for {len(auth_backup)} platforms")
                    else:
                        click.echo("No authentication credentials found to back up")
                else:
                    click.echo("No platform_credentials table found in the database")
        except Exception as e:
            logger.warning(f"Failed to backup authentication credentials: {e}")
            click.secho(
                "Failed to backup authentication credentials. Continuing without backup.",
                fg="yellow",
            )
            auth_backup = None

    # Remove existing database files completely if they exist
    if db_path.exists():
        try:
            click.echo(f"Removing existing database at {db_path}")
            wal_path = db_path.with_suffix(".db-wal")
            shm_path = db_path.with_suffix(".db-shm")
            journal_path = db_path.with_name(f"{db_path.name}-journal")

            # Remove all database-related files
            if db_path.exists():
                os.remove(db_path)
            if wal_path.exists():
                os.remove(wal_path)
            if shm_path.exists():
                os.remove(shm_path)
            if journal_path.exists():
                os.remove(journal_path)

            click.echo("Existing database files removed.")
        except Exception as e:
            logger.error(f"Error removing existing database: {e}")
            click.secho(f"Error removing existing database: {e}", fg="red")
            if not click.confirm("Continue with database initialization anyway?"):
                click.echo("Database initialization cancelled.")
                return

    # Initialize the database
    try:
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        click.echo(f"Initializing new database at {db_path}")
        initialize_database(db_path)

        # Restore authentication credentials if requested and backed up
        if keep_auth and auth_backup:
            click.echo("Restoring platform authentication credentials...")
            try:
                # Connect to the new database
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Insert each credential row back
                for auth_data in auth_backup:
                    # Convert to properly formatted SQL
                    columns = list(auth_data.keys())
                    placeholders = ["?" for _ in columns]
                    values = [auth_data[col] for col in columns]

                    # Skip ID column as it's auto-incremented
                    if "id" in columns:
                        idx = columns.index("id")
                        columns.pop(idx)
                        placeholders.pop(idx)
                        values.pop(idx)

                    # Create INSERT statement
                    columns_str = ", ".join(columns)
                    placeholders_str = ", ".join(placeholders)
                    sql = (
                        f"INSERT INTO platform_credentials ({columns_str}) "
                        f"VALUES ({placeholders_str})"
                    )

                    cursor.execute(sql, values)

                conn.commit()
                conn.close()
                click.echo(f"Restored authentication credentials for {len(auth_backup)} platforms")
            except Exception as e:
                logger.error(f"Error restoring authentication credentials: {e}")
                click.secho(f"Error restoring authentication credentials: {e}", fg="red")

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
