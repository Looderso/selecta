"""Database connection and session management for Selecta."""

import os
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from selecta.core.utils.path_helper import get_app_data_path

# Create a base class for declarative models
Base = declarative_base()

# Define the database file path
DB_PATH = get_app_data_path() / "selecta.db"


def get_engine(db_path: Path | str | None = None) -> Any:
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


def get_session_factory(engine: Any) -> sessionmaker:
    """Create a session factory bound to the given engine.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Session factory
    """
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory


def get_session(engine: Any = None) -> Session:
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
    from selecta.core.data.models import (  # noqa
        Track,
        Playlist,
        Album,
        Vinyl,
        Genre,
        Tag,
        TrackAttribute,
        UserSettings,
        PlatformCredentials,
    )

    # Create all tables
    Base.metadata.create_all(engine)
    logger.info("Database schema created")
