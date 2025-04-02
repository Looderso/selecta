# Python Typing Guidelines for Selecta

This document outlines our typing conventions to ensure consistent and accurate type annotations throughout the Selecta codebase.

## General Guidelines

1. **Use Union Syntax for Optional Types**
   - Use `Type | None` instead of `Optional[Type]` for nullable types
   - Example: `def get_track(self, track_id: int) -> Track | None:`

2. **Type All Function Parameters and Return Values**
   - All function parameters should have explicit type annotations
   - All function return values should have explicit return types (use `-> None` for no return value)
   - Include `self` parameters in method signatures, but don't type them

3. **Use Type Narrowing with TypeGuard**
   - Use `TypeGuard` for functions that check for specific attributes or types
   - Example:

     ```python
     def has_artist_names(obj: Any) -> TypeGuard[HasArtistNames]:
         return hasattr(obj, "artist_names") and hasattr(obj, "album_name")
     ```

4. **Use Protocol for Structural Typing**
   - Use `Protocol` classes for duck typing patterns
   - Add `@runtime_checkable` decorator to Protocol classes when used with `isinstance()`
   - Example:

     ```python
     @runtime_checkable
     class HasArtist(Protocol):
         """Protocol for models with an artist attribute."""
         artist: str
     ```

## SQLAlchemy-Specific Guidelines

1. **Use SQLAlchemy 2.0-Style Mapped Types**
   - Use `Mapped[Type]` for all column fields
   - Use `Mapped[Type | None]` for nullable columns
   - Example:

     ```python
     class Track(Base):
         id: Mapped[int] = mapped_column(primary_key=True)
         title: Mapped[str] = mapped_column(String(255), nullable=False)
         duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
     ```

2. **Type Relationships Properly**
   - For many-to-one: `Mapped[RelatedModel | None]`
   - For one-to-many: `Mapped[List[RelatedModel]]`
   - Example:

     ```python
     # One-to-many relationship
     tracks: Mapped[List["Track"]] = relationship("Track", back_populates="album")

     # Many-to-one relationship
     album: Mapped["Album" | None] = relationship("Album", back_populates="tracks")
     ```

3. **Use Factory Methods for Model Creation**
   - Create dedicated methods that properly set attributes when creating model instances
   - Example:

     ```python
     def _create_platform_info(
         self,
         track_id: int,
         platform: str,
         platform_id: str,
         uri: str | None = None,
         metadata: str | None = None,
     ) -> TrackPlatformInfo:
         """Create a new TrackPlatformInfo object with proper typing."""
         info = TrackPlatformInfo()
         info.track_id = track_id
         info.platform = platform
         info.platform_id = platform_id
         info.uri = uri
         info.platform_data = metadata
         return info
     ```

## PyQt-Specific Guidelines

1. **Type Qt Widget Parameters**
   - Always type parent widgets: `parent: QWidget | None = None`
   - Type context menu positions: `position: Any`
   - Type specific widgets when working with concrete types: `widget: QTableView`

2. **Handle Type Ignores for Qt Methods**
   - Use `# type: ignore` for Qt methods where types can't be resolved properly
   - Example: `self.tracks_table.selectionModel().select(  # type: ignore`

3. **Type PyQt Signals**
   - Type signal parameters when emitting signals
   - Example: `self.track_selected.emit(track)`

## Type Utilities

1. **Use Type Narrowing with hasattr**
   - Create TypeGuard functions for hasattr checks
   - Example:

     ```python
     def has_name(obj: Any) -> TypeGuard[HasName]:
         return hasattr(obj, "name") and obj.name is not None
     ```

2. **Use Type Helpers for Dictionary Access**
   - Create helper functions for safe dictionary access
   - Example:

     ```python
     def get_column_value(model: Any, column_name: str, default: V) -> Union[Any, V]:
         if hasattr(model, column_name):
             value = getattr(model, column_name)
             return value if value is not None else default
         return default
     ```

3. **Use Type Generics for Repositories**
   - Use generic typing for repository classes
   - Example:

     ```python
     class BaseRepository(Generic[ModelType]):
         def __init__(self, model_class: type[ModelType], session: Session | None = None) -> None:
             self.model_class = model_class
             self.session = session
     ```

## Static Type Checking

1. **Ruff Configuration**
   - Enforce typing via Ruff with rules:
     - TCH (Type checking)
     - ANN (Type annotations)
   - Use type checking hook in VS Code
   - Example rules in pyproject.toml:

     ```toml
     [tool.ruff.lint]
     select = [
         "TCH",  # Type checking
         "ANN",  # Type annotations
     ]
     ```

2. **Common Type Imports**
   - Import common types from the typing module:

     ```python
     from typing import (
         Any, Dict, List, Protocol, TypeVar, Union, cast,
         TypeGuard, runtime_checkable
     )
     ```

3. **Handling Type Errors**
   - Use `# type: ignore[specific-error]` for legitimate type ignores
   - Document why the type ignore is necessary

## Examples

### Type-Safe Property Accessors

```python
@property
def is_token_expired(self) -> bool:
    """Check if the access token is expired."""
    if not is_column_truthy(self.access_token) or not is_column_truthy(self.token_expiry):
        return True

    if self.token_expiry is None:
        return True

    return datetime.utcnow() > self.token_expiry
```

### Generic Repository Pattern

```python
class TrackRepository(BaseRepository[Track]):
    """Repository for track-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or get_session()
        super().__init__(Track, self.session)

    def get_by_id(self, track_id: int) -> Track | None:
        """Get a track by its ID."""
        if self.session is None:
            return None
        return self.session.query(Track).filter(Track.id == track_id).first()
```

### PyQt Component Construction

```python
class SearchBar(QWidget):
    """A search bar component."""

    search_confirmed = pyqtSignal(str)

    def __init__(self, placeholder_text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self._setup_ui()
```
