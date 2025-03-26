# src/selecta/utils/type_helpers.py
"""Type conversion and helper utilities for SQLAlchemy models."""

from typing import Any, TypeVar, cast

from sqlalchemy.sql.elements import ColumnElement

# Define a generic type variable for return type
T = TypeVar("T")


def ensure_type(value: Any, type_: type[T]) -> T:
    """Convert a SQLAlchemy Column or any other value to the specified type.

    Args:
        value: The value to convert (can be a Column object or primitive)
        type_: The target type to convert to

    Returns:
        The value converted to the specified type
    """
    # If it's already the right type, return it
    if isinstance(value, type_):
        return value

    # Cast Column objects to their actual type for type checkers
    if isinstance(value, ColumnElement):
        return cast(T, value)

    # For None values that need to be a specific type
    if value is None and type_ is not None:
        if type_ is str:
            return cast(T, "")
        if type_ is int:
            return cast(T, 0)
        if type_ is bool:
            return cast(T, False)
        # Add more types as needed

    # Try converting the value
    try:
        return type_(value)  # type: ignore
    except (TypeError, ValueError):
        # Fallback: cast the value
        return cast(T, value)


def column_to_bool(column_value: Any) -> bool:
    """Convert a SQLAlchemy Column to a boolean.

    Args:
        column_value: The Column value to convert

    Returns:
        Boolean value
    """
    # Handle None case
    if column_value is None:
        return False

    # For actual booleans
    if isinstance(column_value, bool):
        return column_value

    # For string values ("true", "1", "yes", etc.)
    if isinstance(column_value, str):
        return column_value.lower() in ("true", "1", "yes", "t", "y")

    # For other values, try to convert to bool
    try:
        return bool(column_value)
    except (TypeError, ValueError):
        return False


def column_to_int(column_value: Any) -> int:
    """Convert a SQLAlchemy Column to an integer.

    Args:
        column_value: The Column value to convert

    Returns:
        Integer value
    """
    if column_value is None:
        return 0

    if isinstance(column_value, int):
        return column_value

    try:
        return int(column_value)
    except (TypeError, ValueError):
        return 0


def column_to_str(column_value: Any) -> str:
    """Convert a SQLAlchemy Column to a string.

    Args:
        column_value: The Column value to convert

    Returns:
        String value
    """
    if column_value is None:
        return ""

    if isinstance(column_value, str):
        return column_value

    try:
        return str(column_value)
    except (TypeError, ValueError):
        return ""


def is_column_truthy(column_value: Any) -> bool:
    """Check if a SQLAlchemy Column value is truthy.

    Args:
        column_value: Column value to check

    Returns:
        True if the column value is truthy, False otherwise
    """
    return column_to_bool(column_value)
