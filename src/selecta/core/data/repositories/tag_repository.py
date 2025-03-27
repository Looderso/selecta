"""Tag and genre repository for database operations."""

from sqlalchemy.orm import Session

from selecta.core.data.database import get_session
from selecta.core.data.models.genre import Genre
from selecta.core.data.models.tag import PlaylistTag, Tag, TrackTag


class TagRepository:
    """Repository for tag and genre-related database operations."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session (creates a new one if not provided)
        """
        self.session = session or get_session()

    # === Tag Methods ===

    def get_tag_by_id(self, tag_id: int) -> Tag | None:
        """Get a tag by its ID.

        Args:
            tag_id: The tag ID

        Returns:
            The tag if found, None otherwise
        """
        return self.session.query(Tag).filter(Tag.id == tag_id).first()

    def get_tag_by_name(self, name: str) -> Tag | None:
        """Get a tag by its name.

        Args:
            name: The tag name

        Returns:
            The tag if found, None otherwise
        """
        return self.session.query(Tag).filter(Tag.name == name).first()

    def get_all_tags(self) -> list[Tag]:
        """Get all tags.

        Returns:
            List of tags
        """
        return self.session.query(Tag).order_by(Tag.name).all()

    def create_tag(
        self, name: str, description: str | None = None, color: str | None = None
    ) -> Tag:
        """Create a new tag.

        Args:
            name: The tag name
            description: Optional description
            color: Optional color code

        Returns:
            The created tag
        """
        tag = Tag(name=name, description=description, color=color)
        self.session.add(tag)
        self.session.commit()
        return tag

    def update_tag(
        self,
        tag_id: int,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> Tag | None:
        """Update an existing tag.

        Args:
            tag_id: The tag ID
            name: Optional new name
            description: Optional new description
            color: Optional new color

        Returns:
            The updated tag if found, None otherwise
        """
        tag = self.get_tag_by_id(tag_id)
        if not tag:
            return None

        # Use setattr instead of direct assignment to avoid typing issues
        if name is not None:
            tag.name = name
        if description is not None:
            tag.description = description
        if color is not None:
            tag.color = color

        self.session.commit()
        return tag

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag by its ID.

        Args:
            tag_id: The tag ID

        Returns:
            True if deleted, False if not found
        """
        tag = self.get_tag_by_id(tag_id)
        if not tag:
            return False

        self.session.delete(tag)
        self.session.commit()
        return True

    def add_tag_to_track(self, track_id: int, tag_id: int) -> TrackTag | None:
        """Add a tag to a track.

        Args:
            track_id: The track ID
            tag_id: The tag ID

        Returns:
            The created track-tag association, or None if already exists
        """
        # Check if this association already exists
        existing = (
            self.session.query(TrackTag)
            .filter(TrackTag.track_id == track_id, TrackTag.tag_id == tag_id)
            .first()
        )

        if existing:
            return None

        track_tag = TrackTag(track_id=track_id, tag_id=tag_id)
        self.session.add(track_tag)
        self.session.commit()
        return track_tag

    def remove_tag_from_track(self, track_id: int, tag_id: int) -> bool:
        """Remove a tag from a track.

        Args:
            track_id: The track ID
            tag_id: The tag ID

        Returns:
            True if removed, False if not found
        """
        track_tag = (
            self.session.query(TrackTag)
            .filter(TrackTag.track_id == track_id, TrackTag.tag_id == tag_id)
            .first()
        )

        if not track_tag:
            return False

        self.session.delete(track_tag)
        self.session.commit()
        return True

    def get_track_tags(self, track_id: int) -> list[Tag]:
        """Get all tags for a track.

        Args:
            track_id: The track ID

        Returns:
            List of tags
        """
        return self.session.query(Tag).join(TrackTag).filter(TrackTag.track_id == track_id).all()

    def add_tag_to_playlist(self, playlist_id: int, tag_id: int) -> PlaylistTag | None:
        """Add a tag to a playlist.

        Args:
            playlist_id: The playlist ID
            tag_id: The tag ID

        Returns:
            The created playlist-tag association, or None if already exists
        """
        # Check if this association already exists
        existing = (
            self.session.query(PlaylistTag)
            .filter(PlaylistTag.playlist_id == playlist_id, PlaylistTag.tag_id == tag_id)
            .first()
        )

        if existing:
            return None

        playlist_tag = PlaylistTag(playlist_id=playlist_id, tag_id=tag_id)
        self.session.add(playlist_tag)
        self.session.commit()
        return playlist_tag

    def remove_tag_from_playlist(self, playlist_id: int, tag_id: int) -> bool:
        """Remove a tag from a playlist.

        Args:
            playlist_id: The playlist ID
            tag_id: The tag ID

        Returns:
            True if removed, False if not found
        """
        playlist_tag = (
            self.session.query(PlaylistTag)
            .filter(PlaylistTag.playlist_id == playlist_id, PlaylistTag.tag_id == tag_id)
            .first()
        )

        if not playlist_tag:
            return False

        self.session.delete(playlist_tag)
        self.session.commit()
        return True

    def get_playlist_tags(self, playlist_id: int) -> list[Tag]:
        """Get all tags for a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of tags
        """
        return (
            self.session.query(Tag)
            .join(PlaylistTag)
            .filter(PlaylistTag.playlist_id == playlist_id)
            .all()
        )

    # === Genre Methods ===

    def get_genre_by_id(self, genre_id: int) -> Genre | None:
        """Get a genre by its ID.

        Args:
            genre_id: The genre ID

        Returns:
            The genre if found, None otherwise
        """
        return self.session.query(Genre).filter(Genre.id == genre_id).first()

    def get_genre_by_name(self, name: str) -> Genre | None:
        """Get a genre by its name.

        Args:
            name: The genre name

        Returns:
            The genre if found, None otherwise
        """
        return self.session.query(Genre).filter(Genre.name == name).first()

    def get_all_genres(self, source: str | None = None) -> list[Genre]:
        """Get all genres, optionally filtered by source.

        Args:
            source: Optional source filter (e.g., 'spotify', 'discogs', 'user')

        Returns:
            List of genres
        """
        query = self.session.query(Genre)

        if source:
            query = query.filter(Genre.source == source)

        return query.order_by(Genre.name).all()

    def create_genre(self, name: str, source: str | None = None) -> Genre:
        """Create a new genre.

        Args:
            name: The genre name
            source: Optional source (e.g., 'spotify', 'discogs', 'user')

        Returns:
            The created genre
        """
        genre = Genre(name=name, source=source)
        self.session.add(genre)
        self.session.commit()
        return genre

    def get_or_create_genre(self, name: str, source: str | None = None) -> Genre:
        """Get a genre by name or create it if it doesn't exist.

        Args:
            name: The genre name
            source: Optional source

        Returns:
            The existing or newly created genre
        """
        genre = self.get_genre_by_name(name)
        if genre:
            return genre

        return self.create_genre(name, source)

    def add_genre_to_track(self, track_id: int, genre_id: int) -> bool:
        """Add a genre to a track.

        Args:
            track_id: The track ID
            genre_id: The genre ID

        Returns:
            True if added (or already exists), False if not found
        """
        from selecta.core.data.models.track import Track

        track = self.session.query(Track).filter(Track.id == track_id).first()
        genre = self.get_genre_by_id(genre_id)

        if not track or not genre:
            return False

        if genre not in track.genres:
            track.genres.append(genre)
            self.session.commit()

        return True

    def remove_genre_from_track(self, track_id: int, genre_id: int) -> bool:
        """Remove a genre from a track.

        Args:
            track_id: The track ID
            genre_id: The genre ID

        Returns:
            True if removed, False if not found
        """
        from selecta.core.data.models.track import Track

        track = self.session.query(Track).filter(Track.id == track_id).first()
        genre = self.get_genre_by_id(genre_id)

        if not track or not genre:
            return False

        if genre in track.genres:
            track.genres.remove(genre)
            self.session.commit()

        return True

    def get_track_genres(self, track_id: int) -> list[Genre]:
        """Get all genres for a track.

        Args:
            track_id: The track ID

        Returns:
            List of genres
        """
        from selecta.core.data.models.track import Track

        track = self.session.query(Track).filter(Track.id == track_id).first()
        if not track:
            return []

        return track.genres
