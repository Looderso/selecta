"""Vinyl repository for database operations."""

import json
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Album, Track, Vinyl
from selecta.core.data.types import BaseRepository


class VinylRepository(BaseRepository[Vinyl]):
    """Repository for vinyl-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()
        super().__init__(Vinyl, self.session)

    def get_by_id(self, vinyl_id: int) -> Vinyl | None:
        """Get a vinyl record by its ID.

        Args:
            vinyl_id: The vinyl ID

        Returns:
            The vinyl record if found, None otherwise
        """
        if self.session is None:
            return None

        return (
            self.session.query(Vinyl)
            .options(joinedload(Vinyl.album).joinedload(Album.tracks))
            .filter(Vinyl.id == vinyl_id)
            .first()
        )

    def get_by_discogs_id(self, discogs_id: int) -> Vinyl | None:
        """Get a vinyl record by its Discogs ID.

        Args:
            discogs_id: The Discogs ID

        Returns:
            The vinyl record if found, None otherwise
        """
        if self.session is None:
            return None

        return (
            self.session.query(Vinyl)
            .options(joinedload(Vinyl.album))
            .filter(Vinyl.discogs_id == discogs_id)
            .first()
        )

    def get_all(
        self,
        owned_only: bool = False,
        wanted_only: bool = False,
        for_sale_only: bool = False,
    ) -> list[Vinyl]:
        """Get all vinyl records with optional filtering.

        Args:
            owned_only: Only return owned records
            wanted_only: Only return wanted records
            for_sale_only: Only return records for sale

        Returns:
            List of vinyl records
        """
        if self.session is None:
            return []

        query = self.session.query(Vinyl).options(joinedload(Vinyl.album))

        if owned_only:
            query = query.filter(Vinyl.is_owned)
        if wanted_only:
            query = query.filter(Vinyl.is_wanted)
        if for_sale_only:
            query = query.filter(Vinyl.for_sale)

        return query.all()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> tuple[list[Vinyl], int]:
        """Search for vinyl records by album title or artist.

        Args:
            query: The search query
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of vinyl records, total count)
        """
        if self.session is None:
            return [], 0

        # Prepare search terms
        search_term = f"%{query}%"

        # Build the query
        base_query = (
            self.session.query(Vinyl)
            .join(Album)
            .filter(or_(Album.title.ilike(search_term), Album.artist.ilike(search_term)))
        )

        # Get total count
        total = base_query.count()

        # Get paginated results
        records = (
            base_query.options(joinedload(Vinyl.album))
            .order_by(Album.artist, Album.title)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return records, total

    def create(self, vinyl_data: dict[str, Any], album_data: dict[str, Any] | None = None) -> Vinyl:
        """Create a new vinyl record.

        Args:
            vinyl_data: Dictionary with vinyl data
            album_data: Optional dictionary with album data

        Returns:
            The created vinyl record
        """
        if self.session is None:
            raise ValueError("Session is required for creating a vinyl record")

        # Create album if provided
        album_id = None
        if album_data:
            album = Album(**album_data)
            self.session.add(album)
            self.session.flush()
            album_id = album.id

        # Create vinyl record without album_id in constructor
        vinyl = Vinyl(**vinyl_data)
        self.session.add(vinyl)

        # Set album_id after creation if we have one
        if album_id is not None:
            # Use setattr to avoid typing issues
            vinyl.album_id = album_id

        self.session.commit()
        return vinyl

    def update(
        self, vinyl_id: int, vinyl_data: dict[str, Any], album_data: dict[str, Any] | None = None
    ) -> Vinyl | None:
        """Update an existing vinyl record.

        Args:
            vinyl_id: The vinyl ID
            vinyl_data: Dictionary with updated vinyl data
            album_data: Optional dictionary with updated album data

        Returns:
            The updated vinyl record if found, None otherwise
        """
        if self.session is None:
            return None

        vinyl = self.get_by_id(vinyl_id)
        if not vinyl:
            return None

        # Update vinyl attributes
        for key, value in vinyl_data.items():
            setattr(vinyl, key, value)

        # Update album if provided
        if album_data and vinyl.album:
            album = vinyl.album
            for key, value in album_data.items():
                setattr(album, key, value)

        self.session.commit()
        return vinyl

    def delete(self, vinyl_id: int) -> bool:
        """Delete a vinyl record by its ID.

        Args:
            vinyl_id: The vinyl ID

        Returns:
            True if deleted, False if not found
        """
        if self.session is None:
            return False

        vinyl = self.get_by_id(vinyl_id)
        if not vinyl:
            return False

        # Check if we should delete the album too (if it's only connected to this vinyl)
        album = vinyl.album
        delete_album = False

        if album and not album.tracks:
            # If album has no tracks, delete it along with the vinyl
            delete_album = True

        # Delete the vinyl
        self.session.delete(vinyl)

        # Delete orphaned album if needed
        if delete_album:
            self.session.delete(album)

        self.session.commit()
        return True

    def update_vinyl_from_discogs(self, vinyl_id: int, discogs_data: str | dict[str, Any]) -> bool:
        """Update vinyl and album information from Discogs data.

        Args:
            vinyl_id: The vinyl ID
            discogs_data: JSON string or dictionary with Discogs data

        Returns:
            True if updated, False if failed
        """
        if self.session is None:
            return False

        vinyl = self.get_by_id(vinyl_id)
        if not vinyl:
            return False

        # Parse JSON if needed
        if isinstance(discogs_data, str):
            try:
                data = json.loads(discogs_data)
            except json.JSONDecodeError:
                return False
        else:
            data = discogs_data

        # Update vinyl fields
        updated = False

        # Update condition information
        if "media_condition" in data:
            vinyl.media_condition = data["media_condition"]
            updated = True

        if "sleeve_condition" in data:
            vinyl.sleeve_condition = data["sleeve_condition"]
            updated = True

        # Update catalog number
        if vinyl.album and "catno" in data:
            vinyl.album.catalog_number = data["catno"]
            updated = True

        # Update label information
        if vinyl.album and "label" in data:
            vinyl.album.label = data["label"]
            updated = True

        # Update artwork
        if vinyl.album and "cover_url" in data:
            vinyl.album.artwork_url = data["cover_url"]
            # Update linked tracks as well
            for track in vinyl.album.tracks:
                if not track.artwork_url:
                    track.artwork_url = data["cover_url"]
            updated = True

        # Update release year
        if vinyl.album and "year" in data:
            vinyl.album.release_year = data["year"]
            updated = True

        if updated:
            self.session.commit()

        return updated

    def get_track_by_vinyl_id(self, vinyl_id: int) -> list[Track]:
        """Get all tracks associated with a vinyl record.

        Args:
            vinyl_id: The vinyl ID

        Returns:
            List of tracks
        """
        if self.session is None:
            return []

        vinyl = self.get_by_id(vinyl_id)
        if not vinyl or not vinyl.album:
            return []

        return vinyl.album.tracks
