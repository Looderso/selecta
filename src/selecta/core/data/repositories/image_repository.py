"""Repository for image storage and retrieval."""

import io
from datetime import UTC, datetime

from PIL import Image as PILImage
from sqlalchemy.orm import Session, joinedload

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Image, ImageSize, Track
from selecta.core.data.types import BaseRepository


class ImageRepository(BaseRepository[Image]):
    """Repository for image-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()
        super().__init__(Image, self.session)

    def get_by_id(self, image_id: int) -> Image | None:
        """Get an image by its ID.

        Args:
            image_id: The image ID

        Returns:
            The image if found, None otherwise
        """
        if self.session is None:
            return None
        return self.session.query(Image).filter(Image.id == image_id).first()

    def get_track_image(self, track_id: int, size: ImageSize = ImageSize.MEDIUM) -> Image | None:
        """Get an image for a track by size.

        Args:
            track_id: The track ID
            size: The desired image size

        Returns:
            The image if found, None otherwise
        """
        if self.session is None:
            return None

        # First try to find track-specific image
        image = (
            self.session.query(Image).filter(Image.track_id == track_id, Image.size == size).first()
        )

        if image:
            return image

        # If not found, try to find an album image
        track = (
            self.session.query(Track)
            .options(joinedload(Track.album))
            .filter(Track.id == track_id)
            .first()
        )

        if track and track.album:
            album_image = (
                self.session.query(Image)
                .filter(Image.album_id == track.album.id, Image.size == size)
                .first()
            )
            return album_image

        # If still not found, return any track image
        return self.session.query(Image).filter(Image.track_id == track_id).first()

    def get_album_image(self, album_id: int, size: ImageSize = ImageSize.MEDIUM) -> Image | None:
        """Get an image for an album by size.

        Args:
            album_id: The album ID
            size: The desired image size

        Returns:
            The image if found, None otherwise
        """
        if self.session is None:
            return None

        # Try to find album image of the specified size
        image = (
            self.session.query(Image).filter(Image.album_id == album_id, Image.size == size).first()
        )

        if image:
            return image

        # If not found, return any album image
        return self.session.query(Image).filter(Image.album_id == album_id).first()

    def add_track_image(
        self,
        track_id: int,
        image_data: bytes,
        size: ImageSize,
        mime_type: str = "image/jpeg",
        source: str | None = None,
        source_url: str | None = None,
    ) -> Image:
        """Add an image to a track.

        Args:
            track_id: The track ID
            image_data: Raw image data as bytes
            size: Image size category
            mime_type: MIME type of the image
            source: Source of the image (e.g., 'spotify', 'discogs')
            source_url: URL where the image was obtained

        Returns:
            The created image

        Raises:
            ValueError: If the session is None
        """
        if self.session is None:
            raise ValueError("Session is required for adding an image")

        # Get image dimensions and file size
        width, height = None, None
        try:
            pil_image = PILImage.open(io.BytesIO(image_data))
            width, height = pil_image.size
        except Exception:
            # If we can't open the image, just continue without dimensions
            pass

        # Create the image
        image = Image(
            data=image_data,
            mime_type=mime_type,
            size=size,
            width=width,
            height=height,
            file_size=len(image_data),
            track_id=track_id,
            source=source,
            source_url=source_url,
            created_at=datetime.now(UTC),
        )

        self.session.add(image)
        self.session.commit()
        return image

    def add_album_image(
        self,
        album_id: int,
        image_data: bytes,
        size: ImageSize,
        mime_type: str = "image/jpeg",
        source: str | None = None,
        source_url: str | None = None,
    ) -> Image:
        """Add an image to an album.

        Args:
            album_id: The album ID
            image_data: Raw image data as bytes
            size: Image size category
            mime_type: MIME type of the image
            source: Source of the image (e.g., 'spotify', 'discogs')
            source_url: URL where the image was obtained

        Returns:
            The created image

        Raises:
            ValueError: If the session is None
        """
        if self.session is None:
            raise ValueError("Session is required for adding an image")

        # Get image dimensions and file size
        width, height = None, None
        try:
            pil_image = PILImage.open(io.BytesIO(image_data))
            width, height = pil_image.size
        except Exception:
            # If we can't open the image, just continue without dimensions
            pass

        # Create the image
        image = Image(
            data=image_data,
            mime_type=mime_type,
            size=size,
            width=width,
            height=height,
            file_size=len(image_data),
            album_id=album_id,
            source=source,
            source_url=source_url,
            created_at=datetime.now(UTC),
        )

        self.session.add(image)
        self.session.commit()
        return image

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
            original_data: Original image data
            track_id: The track ID (optional)
            album_id: The album ID (optional)
            source: Source of the image (e.g., 'spotify', 'discogs')
            source_url: URL where the image was obtained

        Returns:
            Dictionary mapping sizes to created Image objects

        Raises:
            ValueError: If neither track_id nor album_id is provided
            ValueError: If the session is None
        """
        if self.session is None:
            raise ValueError("Session is required for resizing and storing images")

        if track_id is None and album_id is None:
            raise ValueError("Either track_id or album_id must be provided")

        # Target sizes in pixels
        size_pixels = {
            ImageSize.THUMBNAIL: (64, 64),
            ImageSize.SMALL: (150, 150),
            ImageSize.MEDIUM: (300, 300),
            ImageSize.LARGE: (640, 640),
        }

        created_images = {}

        try:
            # Open the original image
            pil_image = PILImage.open(io.BytesIO(original_data))

            # Resize to each target size
            for size_enum, dimensions in size_pixels.items():
                # Resize to target dimensions
                resized = pil_image.copy()
                resized.thumbnail(dimensions, PILImage.Resampling.LANCZOS)

                # Convert to bytes
                output = io.BytesIO()
                resized.save(output, format=pil_image.format or "JPEG")
                image_data = output.getvalue()

                # Store the image
                if track_id is not None:
                    image = self.add_track_image(
                        track_id=track_id,
                        image_data=image_data,
                        size=size_enum,
                        mime_type=f"image/{pil_image.format.lower() if pil_image.format else 'jpeg'}",  # noqa: E501
                        source=source,
                        source_url=source_url,
                    )
                else:
                    image = self.add_album_image(
                        album_id=album_id,
                        image_data=image_data,
                        size=size_enum,
                        mime_type=f"image/{pil_image.format.lower() if pil_image.format else 'jpeg'}",  # noqa: E501
                        source=source,
                        source_url=source_url,
                    )

                created_images[size_enum] = image

        except Exception:
            # If resizing fails, store the original image at medium size
            if track_id is not None:
                image = self.add_track_image(
                    track_id=track_id,
                    image_data=original_data,
                    size=ImageSize.MEDIUM,
                    source=source,
                    source_url=source_url,
                )
                created_images[ImageSize.MEDIUM] = image
            else:
                image = self.add_album_image(
                    album_id=album_id,
                    image_data=original_data,
                    size=ImageSize.MEDIUM,
                    source=source,
                    source_url=source_url,
                )
                created_images[ImageSize.MEDIUM] = image

        return created_images

    def delete_track_images(self, track_id: int) -> bool:
        """Delete all images for a track.

        Args:
            track_id: The track ID

        Returns:
            True if images were deleted, False otherwise
        """
        if self.session is None:
            return False

        images = self.session.query(Image).filter(Image.track_id == track_id).all()
        for image in images:
            self.session.delete(image)

        self.session.commit()
        return bool(images)

    def delete_album_images(self, album_id: int) -> bool:
        """Delete all images for an album.

        Args:
            album_id: The album ID

        Returns:
            True if images were deleted, False otherwise
        """
        if self.session is None:
            return False

        images = self.session.query(Image).filter(Image.album_id == album_id).all()
        for image in images:
            self.session.delete(image)

        self.session.commit()
        return bool(images)
