"""Spotify track item widget for search results."""

from typing import Any

from selecta.ui.components.search.base_search_result import BaseSearchResult
from selecta.ui.components.search.utils import extract_artist_names, extract_title, get_largest_image_url


class SpotifyTrackItem(BaseSearchResult):
    """Widget to display a single Spotify track search result."""

    def __init__(self, track_data: dict[str, Any], parent=None):
        """Initialize the Spotify track item.

        Args:
            track_data: Dictionary with track data from Spotify API
            parent: Parent widget
        """
        super().__init__(track_data, parent)
        self.setObjectName("spotifyTrackItem")
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)

    def setup_content(self) -> None:
        """Set up the Spotify-specific content."""
        # Apply styling
        self.setStyleSheet("""
            #spotifyTrackItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #spotifyTrackItem:hover {
                background-color: #333333;
            }
            #trackTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #artistName {
                font-size: 12px;
                color: #B3B3B3;
            }
            #albumName {
                font-size: 11px;
                color: #999999;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #FFFFFF;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(51, 51, 51, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(51, 51, 51, 0.5);
            }
            QPushButton:disabled {
                border-color: #555;
                color: #555;
            }
        """)

        # Extract track info
        title = self.get_title()
        artist = self.get_artist()
        album_name = self._get_album_name()

        # Add track title
        self.title_label = self.create_elided_label(title, "trackTitle")
        self.text_layout.addWidget(self.title_label)

        # Add artist name
        self.artist_label = self.create_elided_label(artist, "artistName")
        self.text_layout.addWidget(self.artist_label)

        # Add album name if available
        if album_name:
            self.album_label = self.create_elided_label(album_name, "albumName")
            self.text_layout.addWidget(self.album_label)

    def get_title(self) -> str:
        """Get the title of the track.

        Returns:
            Title string
        """
        return extract_title(self.item_data)

    def get_artist(self) -> str:
        """Get the artist name(s) of the track.

        Returns:
            Artist string
        """
        return extract_artist_names(self.item_data)

    def get_image_url(self) -> str:
        """Get the album cover URL for the track.

        Returns:
            URL string or empty if not available
        """
        # Check for album images in Spotify format
        album = self.item_data.get("album", {})
        images = album.get("images", [])
        if images:
            url = get_largest_image_url(images)
            if url:
                return url

        # Check for alternate image fields
        for field in ["artwork_url", "image_url", "cover_url"]:
            if self.item_data.get(field):
                return self.item_data[field]

        return ""

    def _get_album_name(self) -> str:
        """Get the album name of the track.

        Returns:
            Album name string or empty if not available
        """
        # Check for album name in various formats
        album = self.item_data.get("album")
        if album:
            if isinstance(album, dict) and album.get("name"):
                return str(album["name"])
            elif isinstance(album, str):
                return album

        # Check for album_name field
        album_name = self.item_data.get("album_name")
        if album_name:
            return str(album_name)

        return ""
