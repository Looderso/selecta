"""Genre model definitions."""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from selecta.core.data.database import Base

# Association table for track-genre relationship
track_genres = Table(
    "track_genres",
    Base.metadata,
    Column("track_id", Integer, ForeignKey("tracks.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id"), primary_key=True),
)


class Genre(Base):
    """Genre model representing music genres."""

    __tablename__ = "genres"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    source = Column(String(50), nullable=True)  # e.g., 'spotify', 'discogs', 'user'

    # Tracks with this genre
    tracks = relationship("Track", secondary=track_genres, back_populates="genres")

    def __repr__(self) -> str:
        """String representation of Genre.

        Returns:
            str: String representation
        """
        return f"<Genre {self.id}: {self.name} ({self.source})>"
