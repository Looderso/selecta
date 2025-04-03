"""Database connection and session management for Selecta."""

import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from selecta.core.utils.path_helper import get_app_data_path

# Create a base class for declarative models
Base = declarative_base()

# Global engine instance for connection pooling
_ENGINE = None
_ENGINE_LOCK = threading.RLock()

# Global session factory
_SESSION_FACTORY = None


# Define the database file path
def get_db_path() -> Path:
    """Get the database path based on environment.

    Returns:
        Path: The database file path
    """
    # Check for dev mode
    if os.environ.get("SELECTA_DEV_MODE") == "true":
        dev_db_path = os.environ.get("SELECTA_DEV_DB_PATH")
        if dev_db_path:
            logger.info(f"Using development database at {dev_db_path}")
            return Path(dev_db_path)
        else:
            logger.warning("Dev mode enabled but no database path specified.")

    # Default path for production
    return get_app_data_path() / "selecta.db"


DB_PATH = get_db_path()


def get_engine(db_path: Path | str | None = None) -> Engine:
    """Create or return the shared SQLAlchemy engine.

    This function ensures we use a single shared engine for all database operations
    to prevent SQLite locking issues with multiple connections.

    Args:
        db_path: Path to the database file (default: app data directory)

    Returns:
        SQLAlchemy engine
    """
    global _ENGINE

    # Use thread lock to ensure thread safety when initializing the engine
    with _ENGINE_LOCK:
        if _ENGINE is None:
            if db_path is None:
                db_path = DB_PATH

            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

            # Create SQLite engine with foreign key constraints enabled and improved
            # concurrency settings
            db_url = f"sqlite:///{db_path}"
            connect_args = {
                "check_same_thread": False,
                "timeout": 120.0,  # Wait up to 120 seconds for locks to be released
                "isolation_level": None,  # Autocommit mode for better concurrency
            }
            _ENGINE = create_engine(
                db_url,
                echo=False,
                poolclass=NullPool,  # Disable connection pooling for SQLite - prevents lock issues
                connect_args=connect_args,
            )
            logger.debug(f"Created database engine for {db_url}")

            # Apply optimizations to the new engine
            optimize_sqlite_connection(_ENGINE)

    return _ENGINE


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create or return the shared session factory bound to the given engine.

    Args:
        engine: SQLAlchemy engine (will use the global engine if None)

    Returns:
        Session factory
    """
    global _SESSION_FACTORY

    with _ENGINE_LOCK:
        if _SESSION_FACTORY is None:
            if engine is None:
                engine = get_engine()

            # Configure session with optimizations for SQLite
            _SESSION_FACTORY = sessionmaker(
                bind=engine,
                expire_on_commit=False,  # Prevents additional queries after commit
                autoflush=False,  # Only flush when explicitly called or on commit
            )

    return _SESSION_FACTORY


def get_session(engine: Engine | None = None) -> Session:
    """Create and return a new database session.

    NOTE: It's recommended to use session_scope() instead of this function
    to ensure proper session cleanup.

    Args:
        engine: SQLAlchemy engine (will use the global engine if None)

    Returns:
        SQLAlchemy session
    """
    if engine is None:
        engine = get_engine()

    session_factory = get_session_factory(engine)
    session = session_factory()
    return session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    This context manager ensures that sessions are properly closed and
    either committed or rolled back, even if exceptions occur.

    Yields:
        SQLAlchemy session for database operations

    Example:
        with session_scope() as session:
            session.add(some_object)
            # No need to call commit - it happens automatically if no exceptions
    """
    session = get_session()
    try:
        # In SQLAlchemy 2.0, a transaction is automatically started
        # when the session is first used
        yield session
        # Commit transaction
        session.commit()
    except Exception as e:
        logger.exception(f"Session error: {e}")
        # Rollback transaction on error
        session.rollback()
        raise
    finally:
        # Always close the session to release resources
        session.close()


def optimize_sqlite_connection(engine: Engine) -> None:
    """Apply optimizations to a SQLite connection.

    Sets SQLite pragmas to improve performance and reduce locking issues.

    Args:
        engine: SQLAlchemy engine connected to a SQLite database
    """
    # Execute pragmas to optimize SQLite for our application
    with engine.connect() as conn:
        # Use WAL (Write-Ahead Logging) journal mode for better concurrency
        conn.exec_driver_sql("PRAGMA journal_mode = WAL")

        # Set busy timeout to 120 seconds (120000 ms)
        conn.exec_driver_sql("PRAGMA busy_timeout = 120000")

        # Use NORMAL synchronous mode for better performance with acceptable durability
        conn.exec_driver_sql("PRAGMA synchronous = NORMAL")

        # Increase cache size for better performance
        conn.exec_driver_sql("PRAGMA cache_size = 20000")

        # Store temporary tables in memory
        conn.exec_driver_sql("PRAGMA temp_store = MEMORY")

        # Set locking mode to EXCLUSIVE for the duration of a connection
        conn.exec_driver_sql("PRAGMA locking_mode = EXCLUSIVE")

        # Ensure foreign keys are enforced
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")

        # Commit the pragma changes
        conn.commit()


def init_database(db_path: Path | str | None = None) -> None:
    """Initialize the database schema.

    Args:
        db_path: Path to the database file (default: app data directory)
    """
    engine = get_engine(db_path)

    # Import models here to avoid circular imports

    # Create all tables
    Base.metadata.create_all(engine)
    logger.info("Database schema created")


def utc_now() -> datetime:
    """Return current datetime in UTC using modern API.

    This replaces the deprecated datetime.utcnow() with the recommended
    datetime.now(UTC) approach.

    Returns:
        Current UTC datetime
    """
    return datetime.now(UTC)
