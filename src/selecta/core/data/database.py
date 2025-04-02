"""Database connection and session management for Selecta."""

import os
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from selecta.core.utils.path_helper import get_app_data_path

# Create a base class for declarative models
Base = declarative_base()


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
    """Create and return a SQLAlchemy engine.

    Args:
        db_path: Path to the database file (default: app data directory)

    Returns:
        SQLAlchemy engine
    """
    if db_path is None:
        db_path = DB_PATH

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    # Create SQLite engine with foreign key constraints enabled
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    logger.debug(f"Created database engine for {db_url}")
    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Session factory
    """
    session_factory: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory


def get_session(engine: Engine | None = None) -> Session:
    """Create and return a new database session.

    Args:
        engine: SQLAlchemy engine (will create one if not provided)

    Returns:
        SQLAlchemy session
    """
    if engine is None:
        engine = get_engine()

    session_factory = get_session_factory(engine)
    session = session_factory()
    return session


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
