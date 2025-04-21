"""Type definitions for SQLAlchemy models and database operations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any,
    Generic,
    Protocol,
    TypeGuard,
    TypeVar,
    runtime_checkable,
)

from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

# Type variable for models
T = TypeVar("T")
ModelType = TypeVar("ModelType")


# Define protocol types for common model attributes
class HasId(Protocol):
    """Protocol for models with an ID attribute."""

    id: int


@runtime_checkable
class HasName(Protocol):
    """Protocol for models with a name attribute."""

    name: str


@runtime_checkable
class HasTitle(Protocol):
    """Protocol for models with a title attribute."""

    title: str


@runtime_checkable
class HasArtist(Protocol):
    """Protocol for models with an artist attribute."""

    artist: str


# SQLAlchemy-specific protocols
@runtime_checkable
class SQLAHasId(Protocol):
    """Protocol for SQLAlchemy models with an ID column."""

    id: ColumnElement[int]


@runtime_checkable
class SQLAHasTimestamps(Protocol):
    """Protocol for models with timestamp columns."""

    created_at: ColumnElement[datetime]
    updated_at: ColumnElement[datetime]


# TypeGuard functions
def has_id(obj: Any) -> TypeGuard[HasId]:
    """Check if an object has an id attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has an id attribute
    """
    return hasattr(obj, "id") and obj.id is not None


def has_name(obj: Any) -> TypeGuard[HasName]:
    """Check if an object has a name attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a name attribute
    """
    return hasattr(obj, "name") and obj.name is not None


def has_title(obj: Any) -> TypeGuard[HasTitle]:
    """Check if an object has a title attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a title attribute
    """
    return hasattr(obj, "title") and obj.title is not None


def has_artist(obj: Any) -> TypeGuard[HasArtist]:
    """Check if an object has an artist attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has an artist attribute
    """
    return hasattr(obj, "artist") and obj.artist is not None


# Generic repository base with typed methods
class BaseRepository(Generic[ModelType]):
    """Base repository with generic typing for common database operations."""

    def __init__(self, model_class: type[ModelType], session: Session | None = None) -> None:
        """Initialize the repository.

        Args:
            model_class: The SQLAlchemy model class
            session: SQLAlchemy session (optional)
        """
        self.model_class = model_class
        self.session = session

    def get_by_id(self, entity_id: int) -> ModelType | None:
        """Get an entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            The entity or None if not found
        """
        if self.session is None:
            return None
        return self.session.query(self.model_class).filter_by(id=entity_id).first()

    def get_all(self) -> list[ModelType]:
        """Get all entities.

        Returns:
            List of all entities
        """
        if self.session is None:
            return []
        return self.session.query(self.model_class).all()

    def create(self, data: dict[str, Any]) -> ModelType:
        """Create a new entity.

        Args:
            data: Entity data

        Returns:
            The created entity
        """
        if self.session is None:
            raise ValueError("Session is required for create operation")
        entity = self.model_class(**data)
        self.session.add(entity)
        self.session.commit()
        return entity

    def update(self, entity_id: int, data: dict[str, Any]) -> ModelType | None:
        """Update an entity.

        Args:
            entity_id: Entity ID
            data: Updated data

        Returns:
            The updated entity or None if not found
        """
        if self.session is None:
            return None
        entity = self.get_by_id(entity_id)
        if entity is None:
            return None

        for key, value in data.items():
            setattr(entity, key, value)

        self.session.commit()
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete an entity.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        if self.session is None:
            return False
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False

        self.session.delete(entity)
        self.session.commit()
        return True


# Utility functions for safe column access
def column_exists(model: Any, column_name: str) -> bool:
    """Check if a model has a column.

    Args:
        model: SQLAlchemy model
        column_name: Column name

    Returns:
        True if the column exists
    """
    return hasattr(model, column_name)


V = TypeVar("V")


def get_column_value(model: Any, column_name: str, default: V) -> Any | V:
    """Get a column value safely.

    Args:
        model: SQLAlchemy model
        column_name: Column name
        default: Default value if column doesn't exist or is None

    Returns:
        Column value or default
    """
    if hasattr(model, column_name):
        value = getattr(model, column_name)
        return value if value is not None else default
    return default


# Sync-related types
class ChangeType(Enum):
    """Type of change detected during playlist synchronization."""

    PLATFORM_ADDITION = auto()  # Track added on platform side
    PLATFORM_REMOVAL = auto()  # Track removed on platform side
    LIBRARY_ADDITION = auto()  # Track added in library
    LIBRARY_REMOVAL = auto()  # Track removed from library


@dataclass
class TrackChange:
    """Represents a single change to a track during sync."""

    change_id: str  # Unique identifier for this change
    change_type: ChangeType
    library_track_id: int | None = None  # Library track ID if available
    platform_track_id: str | None = None  # Platform track ID if available

    # Additional details to show in UI
    track_title: str = ""
    track_artist: str = ""

    # When the track was added (if known)
    added_at: datetime | None = None

    # Whether this change should be applied during sync
    selected: bool = True


@dataclass
class SyncChanges:
    """Contains all changes detected during a sync operation."""

    # Library playlist ID
    library_playlist_id: int

    # Platform details
    platform: str
    platform_playlist_id: str

    # Is this a personal playlist?
    is_personal_playlist: bool = True

    # Track changes grouped by type
    platform_additions: list[TrackChange] = field(default_factory=list)
    platform_removals: list[TrackChange] = field(default_factory=list)
    library_additions: list[TrackChange] = field(default_factory=list)
    library_removals: list[TrackChange] = field(default_factory=list)

    # Errors or warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes to apply."""
        return bool(
            self.platform_additions
            or self.platform_removals
            or self.library_additions
            or self.library_removals
        )

    @property
    def selected_changes_count(self) -> int:
        """Count the number of selected changes."""
        return (
            len([c for c in self.platform_additions if c.selected])
            + len([c for c in self.platform_removals if c.selected])
            + len([c for c in self.library_additions if c.selected])
            + len([c for c in self.library_removals if c.selected])
        )


@dataclass
class SyncPreview:
    """Human-readable preview of sync changes for display in UI."""

    # Library playlist details
    library_playlist_id: int
    library_playlist_name: str

    # Platform details
    platform: str
    platform_playlist_id: str
    platform_playlist_name: str

    # Is this a personal playlist?
    is_personal_playlist: bool = True

    # Last sync time
    last_synced: datetime | None = None

    # Human-readable changes with track details
    platform_additions: list[TrackChange] = field(default_factory=list)
    platform_removals: list[TrackChange] = field(default_factory=list)
    library_additions: list[TrackChange] = field(default_factory=list)
    library_removals: list[TrackChange] = field(default_factory=list)

    # Errors or warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of applying sync changes."""

    # Library playlist ID
    library_playlist_id: int

    # Platform details
    platform: str
    platform_playlist_id: str

    # Number of changes applied by type
    platform_additions_applied: int = 0
    platform_removals_applied: int = 0
    library_additions_applied: int = 0
    library_removals_applied: int = 0

    # Errors or warnings
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_changes_applied(self) -> int:
        """Total number of changes applied."""
        return (
            self.platform_additions_applied
            + self.platform_removals_applied
            + self.library_additions_applied
            + self.library_removals_applied
        )

    @property
    def success(self) -> bool:
        """Whether the sync was successful."""
        return not self.errors
