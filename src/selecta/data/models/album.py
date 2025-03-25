"""Album model definitions."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from selecta.data.database import Base


class Album(Base):
    """Album model representing music albums."""

    __tablename__ = "albums"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    release_year = Column(Integer, nullable=True)

    # Album art URL or path
    artwork_url = Column(String(1024), nullable=True)

    # Additional album information
    label = Column(String(255), nullable=True)
    catalog_number = Column(String(100), nullable=True)

    # Related vinyl record (if any)
    vinyl_id = Column(Integer, ForeignKey("vinyl_records.id"), nullable=True)
    vinyl = relationship("Vinyl", back_populates="album")

    # Tracks in the album
    tracks = relationship("Track", back_populates="album")

    def __repr__(self) -> str:
        """String representation of Album.

        Returns:
            str: String representation
        """
        return f"<Album {self.id}: {self.artist} - {self.title}>"
