"""Database initialization utilities."""

import sqlite3
from pathlib import Path

from loguru import logger
from sqlalchemy import inspect

from selecta.core.data.database import get_engine, init_database
from selecta.core.utils.path_helper import get_app_data_path


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

    # Verify the schema after initialization
    verify_schema(db_path)

    logger.success(f"Database initialized at {db_path}")


def verify_schema(db_path: Path | str) -> bool:
    """Verify and fix the database schema if needed.

    Args:
        db_path: Path to the database file

    Returns:
        bool: True if schema is valid, False if there are issues
    """
    logger.info("Verifying database schema...")

    engine = get_engine(db_path)
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    # Check for critical tables
    critical_tables = ["tracks", "playlists", "track_platform_info"]
    missing_tables = [table for table in critical_tables if table not in tables]

    if missing_tables:
        logger.error(f"Critical tables missing: {missing_tables}")
        return False

    # Check TrackPlatformInfo schema specifically
    if "track_platform_info" in tables:
        columns = [col["name"] for col in inspector.get_columns("track_platform_info")]
        required_columns = [
            "id",
            "track_id",
            "platform",
            "platform_id",
            "uri",
            "platform_data",
            "last_synced",
            "needs_update",
        ]

        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            logger.warning(f"TrackPlatformInfo missing columns: {missing_columns}")
            logger.warning("Attempting to fix schema...")

            try:
                fix_track_platform_info_schema(db_path, columns)

                # Re-check after fixing
                inspector = inspect(engine)
                columns = [col["name"] for col in inspector.get_columns("track_platform_info")]
                still_missing = [col for col in required_columns if col not in columns]

                if still_missing:
                    logger.error(f"Failed to fix schema: still missing {still_missing}")
                    return False
                else:
                    logger.success("Schema fixed successfully")
                    return True
            except Exception as e:
                logger.error(f"Error fixing schema: {e}")
                logger.warning("Run 'python upgrade_db.py' to fix schema issues.")
                return False
        else:
            logger.info("TrackPlatformInfo schema is valid")
            return True
    else:
        logger.error("TrackPlatformInfo table not found")
        return False


def fix_track_platform_info_schema(db_path: Path | str, existing_columns: list[str]) -> None:
    """Fix the TrackPlatformInfo table schema.

    Args:
        db_path: Path to the database file
        existing_columns: List of existing column names
    """
    logger.info("Fixing TrackPlatformInfo schema...")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create a new table with all required columns
        cursor.execute("""
            CREATE TABLE track_platform_info_new (
                id INTEGER PRIMARY KEY,
                track_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                platform_id VARCHAR(255) NOT NULL,
                uri VARCHAR(512),
                platform_data TEXT,
                last_synced DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                needs_update BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY(track_id) REFERENCES tracks(id)
            )
        """)

        # Copy existing data
        if existing_columns:
            # Build the column list from the original table
            cols = ", ".join(existing_columns)

            cursor.execute(f"""
                INSERT INTO track_platform_info_new (
                    {cols}, last_synced, needs_update
                )
                SELECT
                    {cols}, CURRENT_TIMESTAMP, 0
                FROM track_platform_info
            """)

        # Rename tables
        cursor.execute("DROP TABLE track_platform_info")
        cursor.execute("ALTER TABLE track_platform_info_new RENAME TO track_platform_info")

        # Create index
        cursor.execute(
            "CREATE INDEX ix_track_platform_info_track_id ON track_platform_info(track_id)"
        )

        conn.commit()
        conn.close()

        logger.success("TrackPlatformInfo schema fixed")
    except Exception as e:
        logger.error(f"Error fixing TrackPlatformInfo schema: {e}")
        raise


if __name__ == "__main__":
    """Run this script directly to initialize the database."""
    initialize_database()
