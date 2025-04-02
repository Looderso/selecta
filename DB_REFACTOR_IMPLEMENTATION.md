# Database Refactor Implementation

## Overview

This document outlines the implementation details for the database refactor, focusing on platform metadata and image storage.

## Database Schema Changes

### 1. Track Model Enhancements

The `Track` model has been extended with new fields:

```python
class Track(Base):
    # Existing fields...
    year = mapped_column(String(10), nullable=True)
    bpm = mapped_column(Float, nullable=True)
    is_available_locally = mapped_column(Boolean, default=False)
    artwork_url = mapped_column(String(255), nullable=True)  # Kept for backward compatibility
```

### 2. Platform Metadata Tracking

The `TrackPlatformInfo` model has been enhanced to track update status:

```python
class TrackPlatformInfo(Base):
    # Existing fields...
    last_synced = mapped_column(DateTime, nullable=True)
    needs_update = mapped_column(Boolean, default=False)
```

### 3. New Image Model

A new `Image` model has been added to store binary image data:

```python
class ImageSize(enum.Enum):
    """Enum for image sizes."""
    THUMBNAIL = "thumbnail"  # 60x60
    SMALL = "small"          # 120x120
    MEDIUM = "medium"        # 300x300
    LARGE = "large"          # 640x640

class Image(Base):
    """Model for storing images like album covers and artist photos."""

    __tablename__ = "images"

    id = mapped_column(primary_key=True)
    data = mapped_column(LargeBinary, nullable=False)
    mime_type = mapped_column(String(50), nullable=False, default="image/jpeg")
    size = mapped_column(SQLEnum(ImageSize), nullable=False)
    track_id = mapped_column(Integer, ForeignKey("tracks.id"), nullable=True)
    album_id = mapped_column(Integer, ForeignKey("albums.id"), nullable=True)
    source = mapped_column(String(50), nullable=True)  # Platform that provided the image
    source_url = mapped_column(String(255), nullable=True)  # Original URL
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    track = relationship("Track", back_populates="images", foreign_keys=[track_id])
    album = relationship("Album", back_populates="images", foreign_keys=[album_id])
```

### 4. Tag and Genre Support

```python
class Tag(Base):
    """Model for storing user-defined tags."""

    __tablename__ = "tags"

    id = mapped_column(primary_key=True)
    name = mapped_column(String(100), nullable=False, unique=True)

    # Many-to-many relationship with tracks
    tracks = relationship("Track", secondary="track_tags", back_populates="tags")

# Association table for track-tag many-to-many relationship
track_tags = Table(
    "track_tags",
    Base.metadata,
    Column("track_id", Integer, ForeignKey("tracks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)
```

## Repository Implementation

### 1. ImageRepository

```python
class ImageRepository:
    """Repository for image operations."""

    def __init__(self):
        """Initialize the image repository."""
        self.session = get_session()

    def get_track_image(self, track_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> Image | None:
        """Get an image for a track.

        Args:
            track_id: The track ID
            size: The desired image size

        Returns:
            The image or None if not found
        """
        return self.session.query(Image).filter(
            Image.track_id == track_id,
            Image.size == size
        ).first()

    def get_album_image(self, album_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> Image | None:
        """Get an image for an album.

        Args:
            album_id: The album ID
            size: The desired image size

        Returns:
            The image or None if not found
        """
        return self.session.query(Image).filter(
            Image.album_id == album_id,
            Image.size == size
        ).first()

    def resize_and_store_image(
        self,
        original_data: bytes,
        track_id: int | None = None,
        album_id: int | None = None,
        source: str | None = None,
        source_url: str | None = None,
    ) -> dict[ImageSize, Image]:
        """Resize an image to all standard sizes and store them.

        Args:
            original_data: Binary image data
            track_id: Optional track ID to associate with
            album_id: Optional album ID to associate with
            source: Source platform (spotify, discogs, etc.)
            source_url: Original URL of the image

        Returns:
            Dictionary mapping sizes to image objects
        """
        # Implementation details...
```

### 2. TrackRepository Enhancements

```python
def add_platform_info(
    self,
    track_id: int,
    platform: str,
    platform_id: str,
    platform_uri: str,
    platform_data: str | None = None
) -> TrackPlatformInfo:
    """Add or update platform info for a track.

    Args:
        track_id: Track ID
        platform: Platform name (e.g., 'spotify', 'discogs')
        platform_id: ID on the platform
        platform_uri: URI on the platform
        platform_data: JSON string with platform-specific data

    Returns:
        TrackPlatformInfo object
    """
    # Implementation details...

def mark_for_update(self, track_id: int, platform: str) -> None:
    """Mark a track's platform info for update.

    Args:
        track_id: Track ID
        platform: Platform name
    """
    # Implementation details...

def needs_update(self, track_id: int, platform: str) -> bool:
    """Check if a track's platform info needs update.

    Args:
        track_id: Track ID
        platform: Platform name

    Returns:
        True if needs update, False otherwise
    """
    # Implementation details...

def set_track_genres(self, track_id: int, genre_names: list[str], source: str | None = None) -> None:
    """Set genres for a track.

    Args:
        track_id: Track ID
        genre_names: List of genre names
        source: Optional source platform
    """
    # Implementation details...
```

## Client-Side Implementation

### 1. DatabaseImageLoader

A new `DatabaseImageLoader` class has been created to load images from the database:

```python
class DatabaseImageLoader(QObject):
    """Asynchronous image loader for loading images from the database."""

    # Signals
    image_loaded = pyqtSignal(str, QPixmap)
    album_image_loaded = pyqtSignal(int, QPixmap)
    track_image_loaded = pyqtSignal(int, QPixmap)

    def load_track_image(self, track_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> None:
        """Load a track's image from the database."""
        # Implementation details...

    def load_album_image(self, album_id: int, size: ImageSize = ImageSize.THUMBNAIL) -> None:
        """Load an album's image from the database."""
        # Implementation details...
```

### 2. TrackItem Base Class

The `TrackItem` base class has been updated to support images:

```python
class TrackItem(ABC):
    def __init__(
        self,
        track_id: Any,
        title: str,
        artist: str,
        duration_ms: int | None = None,
        album: str | None = None,
        added_at: datetime | None = None,
        album_id: int | None = None,
        has_image: bool = False,
    ):
        # Implementation details...
```

### 3. TrackDetailsPanel

The `TrackDetailsPanel` has been updated to display images:

```python
class TrackDetailsPanel(QWidget):
    """Panel displaying detailed information about a track."""

    # Shared image loader
    _db_image_loader = None

    def set_track(self, track: TrackItem | None):
        """Set the track to display."""
        # Implementation details...

        # Load track image from database if available
        if track.has_image and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_track_image(track.track_id, ImageSize.MEDIUM)

        # Also try to load the album image as a fallback
        if track.album_id and TrackDetailsPanel._db_image_loader:
            TrackDetailsPanel._db_image_loader.load_album_image(track.album_id, ImageSize.MEDIUM)
```

### 4. Search Panels

Both Spotify and Discogs search panels have been updated to download and store images:

```python
def _on_track_sync(self, track_data: dict[str, Any]) -> None:
    """Handle track sync button click."""
    # Implementation details...

    # Download and store images if available
    if album_image_url:
        try:
            # Get the image data
            response = requests.get(album_image_url, timeout=10)
            if response.ok:
                # Store images in database at different sizes
                self.image_repo.resize_and_store_image(
                    original_data=response.content,
                    track_id=track_id,
                    source="spotify",
                    source_url=album_image_url
                )
        except Exception as img_err:
            logger.error(f"Error downloading album image: {img_err}")
            # Continue even if image download fails
```

## Performance Considerations

1. **Asynchronous Loading**: All image loading is performed in background threads to keep the UI responsive.
2. **Image Caching**: The `DatabaseImageLoader` includes a cache to prevent repeated database access.
3. **Multiple Sizes**: Images are stored in multiple sizes to reduce resize operations at runtime.
4. **Fallback Mechanism**: If a track image is not available, the system falls back to album images.

## Future Enhancements

1. **User-defined Tags UI**: Add a UI for managing user-defined tags.
2. **Image Management**: Provide a UI for viewing and managing image sizes.
3. **Batch Sync**: Implement batch synchronization of metadata and images.
