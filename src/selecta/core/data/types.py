"""Type definitions for SQLAlchemy models and database operations."""

from datetime import datetime
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
