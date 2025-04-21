"""Discogs release item component for search results."""

from typing import Any

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from selecta.ui.components.search.base_search_result import BaseSearchResult


class DiscogsReleaseItem(BaseSearchResult):
    """Widget to display a single Discogs release search result."""

    def __init__(self, release_data: dict[str, Any], parent=None):
        """Initialize the Discogs release item.

        Args:
            release_data: Dictionary with release data from Discogs API
            parent: Parent widget
        """
        super().__init__(release_data, parent)
        self.setObjectName("discogsReleaseItem")
        self.setMinimumHeight(70)
        self.setMaximumHeight(70)

    def setup_content(self) -> None:
        """Set up the Discogs-specific content."""
        # Apply styling
        self.setStyleSheet("""
            #discogsReleaseItem {
                background-color: #282828;
                border-radius: 6px;
                margin: 2px 0px;
            }
            #discogsReleaseItem:hover {
                background-color: #333333;
            }
            #releaseTitle {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #artistName {
                font-size: 12px;
                color: #B3B3B3;
            }
            #releaseYear {
                font-size: 11px;
                color: #999999;
            }
            #releaseLabel {
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

        # Extract release info
        title = self.get_title()
        artist = self.get_artist()
        year = self._get_year()
        label = self._get_label()

        # Release title with elision
        self.title_label = self.create_elided_label(title, "releaseTitle")
        self.text_layout.addWidget(self.title_label)

        # Artist name with elision
        self.artist_label = self.create_elided_label(artist, "artistName")
        self.text_layout.addWidget(self.artist_label)

        # Year and label in one row
        if year or label:
            details_container = QWidget()
            details_layout = QHBoxLayout(details_container)
            details_layout.setSpacing(10)
            details_layout.setContentsMargins(0, 0, 0, 0)

            # Year with elision
            if year:
                self.year_label = self.create_elided_label(f"Year: {year}", "releaseYear")
                details_layout.addWidget(self.year_label)

            # Label with elision
            if label:
                self.label_label = self.create_elided_label(f"Label: {label}", "releaseLabel")
                details_layout.addWidget(self.label_label)

            details_layout.addStretch(1)
            self.text_layout.addWidget(details_container)

    def get_title(self) -> str:
        """Get the title of the release.

        Returns:
            Title string
        """
        return self.item_data.get("title", "Unknown Title")

    def get_artist(self) -> str:
        """Get the artist name of the release.

        Returns:
            Artist name string
        """
        return self.item_data.get("artist", "Unknown Artist")

    def get_image_url(self) -> str:
        """Get the cover image URL for the release.

        Returns:
            URL string or empty if not available
        """
        # Try to get the full cover image URL first
        cover_url = self.item_data.get("cover_url")
        if cover_url:
            return cover_url

        # Fall back to thumbnail URL if available
        thumb_url = self.item_data.get("thumb_url")
        if thumb_url:
            return thumb_url

        return ""

    def _get_year(self) -> str:
        """Get the release year.

        Returns:
            Year string or empty if not available
        """
        year = self.item_data.get("year", "")
        return str(year) if year else ""

    def _get_label(self) -> str:
        """Get the record label.

        Returns:
            Label name or empty if not available
        """
        label = self.item_data.get("label")
        if label:
            return str(label)
        return ""
