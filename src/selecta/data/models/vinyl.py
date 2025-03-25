"""Vinyl record model definitions."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from selecta.data.database import Base


class Vinyl(Base):
    """Vinyl record model representing physical records in collection."""

    __tablename__ = "vinyl_records"

    id = Column(Integer, primary_key=True)

    # Discogs specific fields
    discogs_id = Column(Integer, nullable=True)
    discogs_release_id = Column(Integer, nullable=True)

    # Vinyl status
    is_owned = Column(Boolean, default=False)
    is_wanted = Column(Boolean, default=False)
    for_sale = Column(Boolean, default=False)

    # Purchase details
    purchase_date = Column(DateTime, nullable=True)
    purchase_price = Column(Float, nullable=True)
    purchase_currency = Column(String(3), nullable=True)
    purchase_notes = Column(Text, nullable=True)

    # Condition
    media_condition = Column(String(50), nullable=True)  # e.g., 'Mint', 'Very Good Plus'
    sleeve_condition = Column(String(50), nullable=True)

    # Related album
    album = relationship("Album", back_populates="vinyl", uselist=False)

    # Notes
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of Vinyl.

        Returns:
            str: String representation
        """
        album_title = self.album.title if self.album else "Unknown"
        return f"<Vinyl {self.id}: {album_title} (Discogs ID: {self.discogs_id})>"
