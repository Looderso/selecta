"""Type conversion and helper utilities for SQLAlchemy models."""

from typing import Any, Protocol, TypedDict, TypeGuard, TypeVar, cast, runtime_checkable

from sqlalchemy.sql.elements import ColumnElement

# Define a generic type variable for return type
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


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
    from loguru import logger

    # Log the actual value and its type for debugging
    logger.debug(f"Column value: {column_value!r} (type: {type(column_value).__name__})")

    # Handle None case
    if column_value is None:
        return False

    # For actual booleans
    if isinstance(column_value, bool):
        return column_value

    # For string values
    if isinstance(column_value, str):
        # Empty strings are falsey
        if not column_value:
            return False
        # Check for common false strings
        return column_value.lower() not in ("false", "0", "no", "n", "f", "")

    # Handle SQLAlchemy Column objects
    if hasattr(column_value, "__clause_element__"):
        # For SQLAlchemy objects, convert to string and check
        try:
            str_value = str(column_value)
            logger.debug(f"Converted SQL value to string: {str_value!r}")
            return bool(str_value) and str_value.lower() not in ("false", "0", "no", "n", "f", "")
        except Exception as e:
            logger.error(f"Error converting SQL value to bool: {e}")
            return False

    # For other values, try to convert to bool
    try:
        return bool(column_value)
    except (TypeError, ValueError):
        return False


# Common Protocol classes for type checking
@runtime_checkable
class HasDescription(Protocol):
    """Protocol for objects with a description attribute."""

    description: str


@runtime_checkable
class HasName(Protocol):
    """Protocol for objects with a name attribute."""

    name: str


@runtime_checkable
class HasTrackCount(Protocol):
    """Protocol for objects with a track_count attribute."""

    track_count: int


@runtime_checkable
class HasChildren(Protocol):
    """Protocol for objects with a children attribute."""

    children: list[Any]


@runtime_checkable
class HasBPM(Protocol):
    """Protocol for objects with a bpm attribute."""

    bpm: int | float


@runtime_checkable
class HasLocalDatabaseFolderChangedHandler(Protocol):
    """Protocol for objects with a on_local_database_folder_changed method."""

    def on_local_database_folder_changed(self, folder_path: str) -> None: ...


@runtime_checkable
class HasImportRekordboxHandler(Protocol):
    """Protocol for objects with a on_import_rekordbox method."""

    def on_import_rekordbox(self) -> None: ...


@runtime_checkable
class HasShowSpotifySearch(Protocol):
    """Protocol for objects with a show_spotify_search method."""

    def show_spotify_search(self) -> None: ...


@runtime_checkable
class HasShowDiscogsSearch(Protocol):
    """Protocol for objects with a show_discogs_search method."""

    def show_discogs_search(self) -> None: ...


@runtime_checkable
class HasRightContainer(Protocol):
    """Protocol for objects with a right_container and right_layout attributes."""

    right_container: Any
    right_layout: Any


@runtime_checkable
class HasArtistAndTitle(Protocol):
    """Protocol for objects with artist and title attributes."""

    id: Any
    artist: str
    title: str
    year: Any
    label: Any
    catno: Any
    format: Any
    genre: Any
    thumb_url: Any
    cover_url: Any
    uri: Any


@runtime_checkable
class HasSearchBar(Protocol):
    """Protocol for objects with a search_bar attribute and search method."""

    search_bar: Any

    def _on_search(self, query: str) -> None: ...


@runtime_checkable
class HasArtistNames(Protocol):
    """Protocol for objects with artist_names and album_name attributes."""

    artist_names: list[str]
    album_name: str
    id: str
    name: str
    uri: str
    album_id: str
    duration_ms: int
    popularity: int
    explicit: bool


@runtime_checkable
class HasSwitchPlatform(Protocol):
    """Protocol for objects with a switch_platform method."""

    def switch_platform(self, platform: str) -> None: ...


@runtime_checkable
class HasIsFolder(Protocol):
    """Protocol for objects with an is_folder method."""

    def is_folder(self) -> bool: ...

    _is_folder: bool


@runtime_checkable
class HasHorizontalSplitter(Protocol):
    """Protocol for objects with horizontal_splitter and vertical_splitter attributes."""

    horizontal_splitter: Any
    vertical_splitter: Any


@runtime_checkable
class HasAuthPanel(Protocol):
    """Protocol for objects with an auth_panel attribute."""

    auth_panel: Any


@runtime_checkable
class HasDetailsPanel(Protocol):
    """Protocol for objects with a playlist_component.details_panel attribute chain."""

    playlist_component: Any  # This itself would have a details_panel attribute


@runtime_checkable
class HasPlatformClients(Protocol):
    """Protocol for objects with a _platform_clients attribute."""

    _platform_clients: dict[str, Any]


@runtime_checkable
class HasIsAuthenticated(Protocol):
    """Protocol for objects with an is_authenticated method."""

    def is_authenticated(self) -> bool: ...


# Common TypedDict classes for dictionary-like objects
class TrackData(TypedDict, total=False):
    """TypedDict for track data."""

    title: str
    artist: str
    album: str
    bpm: int | float | str
    genre: str
    tags: list[str]
    platforms: list[str]
    duration: int
    duration_ms: int
    platforms_tooltip: str
    year: int
    track_number: int
    disc_number: int
    key: str


class PlaylistData(TypedDict, total=False):
    """TypedDict for playlist data."""

    name: str
    description: str
    tracks: list[Any]
    track_count: int
    id: Any
    parent_id: Any
    images: list[str]
    owner: str
    platform: str


# Type guard functions
def has_description(obj: Any) -> TypeGuard[HasDescription]:
    """Type guard to check if an object has a description attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a description attribute
    """
    return hasattr(obj, "description") and obj.description is not None


def has_track_count(obj: Any) -> TypeGuard[HasTrackCount]:
    """Type guard to check if an object has a track_count attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a track_count attribute
    """
    return hasattr(obj, "track_count")


def has_children(obj: Any) -> TypeGuard[HasChildren]:
    """Type guard to check if an object has a children attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a children attribute
    """
    return hasattr(obj, "children") and isinstance(obj.children, list)


def has_bpm(obj: Any) -> TypeGuard[HasBPM]:
    """Type guard to check if an object has a bpm attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a bpm attribute
    """
    return hasattr(obj, "bpm") and obj.bpm is not None


def has_local_db_folder_handler(obj: Any) -> TypeGuard[HasLocalDatabaseFolderChangedHandler]:
    """Type guard to check if an object has an on_local_database_folder_changed method.

    Args:
        obj: Object to check

    Returns:
        True if the object has an on_local_database_folder_changed method
    """
    return hasattr(obj, "on_local_database_folder_changed")


def has_import_rekordbox_handler(obj: Any) -> TypeGuard[HasImportRekordboxHandler]:
    """Type guard to check if an object has an on_import_rekordbox method.

    Args:
        obj: Object to check

    Returns:
        True if the object has an on_import_rekordbox method
    """
    return hasattr(obj, "on_import_rekordbox")


def has_show_spotify_search(obj: Any) -> TypeGuard[HasShowSpotifySearch]:
    """Type guard to check if an object has a show_spotify_search method.

    Args:
        obj: Object to check

    Returns:
        True if the object has a show_spotify_search method
    """
    return hasattr(obj, "show_spotify_search")


def has_show_discogs_search(obj: Any) -> TypeGuard[HasShowDiscogsSearch]:
    """Type guard to check if an object has a show_discogs_search method.

    Args:
        obj: Object to check

    Returns:
        True if the object has a show_discogs_search method
    """
    return hasattr(obj, "show_discogs_search")


def has_right_container(obj: Any) -> TypeGuard[HasRightContainer]:
    """Type guard to check if an object has right_container and right_layout attributes.

    Args:
        obj: Object to check

    Returns:
        True if the object has right_container and right_layout attributes
    """
    return hasattr(obj, "right_container") and hasattr(obj, "right_layout")


def has_artist_and_title(obj: Any) -> TypeGuard[HasArtistAndTitle]:
    """Type guard to check if an object has artist and title attributes.

    Args:
        obj: Object to check

    Returns:
        True if the object has artist and title attributes
    """
    return hasattr(obj, "artist") and hasattr(obj, "title")


def has_search_bar(obj: Any) -> TypeGuard[HasSearchBar]:
    """Type guard to check if an object has a search_bar attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a search_bar attribute
    """
    return hasattr(obj, "search_bar")


def has_artist_names(obj: Any) -> TypeGuard[HasArtistNames]:
    """Type guard to check if an object has artist_names and album_name attributes.

    Args:
        obj: Object to check

    Returns:
        True if the object has artist_names and album_name attributes
    """
    return hasattr(obj, "artist_names") and hasattr(obj, "album_name")


def has_switch_platform(obj: Any) -> TypeGuard[HasSwitchPlatform]:
    """Type guard to check if an object has a switch_platform method.

    Args:
        obj: Object to check

    Returns:
        True if the object has a switch_platform method
    """
    return hasattr(obj, "switch_platform") and callable(obj.switch_platform)


def has_is_folder(obj: Any) -> TypeGuard[HasIsFolder]:
    """Type guard to check if an object has an is_folder method or _is_folder attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has an is_folder method or _is_folder attribute
    """
    return (hasattr(obj, "is_folder") and callable(obj.is_folder)) or hasattr(obj, "_is_folder")


def has_horizontal_splitter(obj: Any) -> TypeGuard[HasHorizontalSplitter]:
    """Type guard to check if an object has horizontal_splitter and vertical_splitter attributes.

    Args:
        obj: Object to check

    Returns:
        True if the object has horizontal_splitter and vertical_splitter attributes
    """
    return hasattr(obj, "horizontal_splitter") and hasattr(obj, "vertical_splitter")


def has_auth_panel(obj: Any) -> TypeGuard[HasAuthPanel]:
    """Type guard to check if an object has an auth_panel attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has an auth_panel attribute
    """
    return hasattr(obj, "auth_panel")


def has_details_panel(obj: Any) -> TypeGuard[HasDetailsPanel]:
    """Type guard to check if an object has a playlist_component with a details_panel attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a playlist_component with a details_panel attribute
    """
    return hasattr(obj, "playlist_component") and hasattr(obj.playlist_component, "details_panel")


def has_platform_clients(obj: Any) -> TypeGuard[HasPlatformClients]:
    """Type guard to check if an object has a _platform_clients attribute.

    Args:
        obj: Object to check

    Returns:
        True if the object has a _platform_clients attribute
    """
    return hasattr(obj, "_platform_clients")


def has_is_authenticated(obj: Any) -> TypeGuard[HasIsAuthenticated]:
    """Type guard to check if an object has an is_authenticated method.

    Args:
        obj: Object to check

    Returns:
        True if the object has an is_authenticated method
    """
    return hasattr(obj, "is_authenticated") and callable(obj.is_authenticated)


# Type-safe dictionary access helpers
def dict_get(data: dict[K, V], key: K, default: T) -> V | T:
    """Get a value from a dictionary with a default.

    Args:
        data: Dictionary to get the value from
        key: Key to look up
        default: Default value to return if key is not found

    Returns:
        Value from the dictionary or the default
    """
    return data.get(key, default)


def dict_int(data: dict[str, Any], key: str, default: int = 0) -> int:
    """Get an integer value from a dictionary.

    Args:
        data: Dictionary to get the value from
        key: Key to look up
        default: Default value to return if key is not found or value cannot be converted

    Returns:
        Integer value
    """
    value = data.get(key, default)
    return column_to_int(value)


def dict_str(data: dict[str, Any], key: str, default: str = "") -> str:
    """Get a string value from a dictionary.

    Args:
        data: Dictionary to get the value from
        key: Key to look up
        default: Default value to return if key is not found or value cannot be converted

    Returns:
        String value
    """
    value = data.get(key, default)
    return column_to_str(value)


def dict_bool(data: dict[str, Any], key: str, default: bool = False) -> bool:
    """Get a boolean value from a dictionary.

    Args:
        data: Dictionary to get the value from
        key: Key to look up
        default: Default value to return if key is not found or value cannot be converted

    Returns:
        Boolean value
    """
    value = data.get(key, default)
    return column_to_bool(value)


# Additional SQLAlchemy-specific helpers
ModelType = TypeVar("ModelType")


def safe_query(
    session: Any | None, model_class: type[ModelType], condition: Any | None = None
) -> list[ModelType]:
    """Execute a SQLAlchemy query safely with appropriate error handling and type safety.

    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        condition: Optional filter condition

    Returns:
        List of model instances
    """
    if session is None:
        return []

    try:
        query = session.query(model_class)
        if condition is not None:
            query = query.filter(condition)
        return query.all()
    except Exception:
        # Log the exception but return empty list to avoid breaking caller
        return []


def safe_get(session: Any | None, model_class: type[ModelType], entity_id: int) -> ModelType | None:
    """Safely get an entity by ID with proper error handling.

    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        entity_id: Entity ID

    Returns:
        Entity instance or None if not found or on error
    """
    if session is None:
        return None

    try:
        return session.query(model_class).filter_by(id=entity_id).first()
    except Exception:
        # Log the exception but return None to avoid breaking caller
        return None
