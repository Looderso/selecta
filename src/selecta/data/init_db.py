"""Database initialization utilities."""

from pathlib import Path

from loguru import logger

from selecta.data.database import init_database
from selecta.utils.path_helper import get_app_data_path


def initialize_database(db_path: Path | str | None = None) -> None:
    """Create and initialize the database with required tables.

    Args:
        db_path: Path to the database file (default: app data directory)
    """
    logger.info("Initializing database...")

    if db_path is None:
        db_path = get_app_data_path() / "selecta.db"
        logger.info(f"Using default database path: {db_path}")

    # Ensure the directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Initialize the database
    init_database(db_path)

    logger.success(f"Database initialized at {db_path}")


if __name__ == "__main__":
    """Run this script directly to initialize the database."""
    initialize_database()
