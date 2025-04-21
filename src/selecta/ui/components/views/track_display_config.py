"""Configuration for platform-specific track display."""


class TrackDisplayConfig:
    """Configuration for platform-specific track display."""

    # Field configurations for different platforms
    _platform_fields = {
        # Default/Local platform fields
        "default": [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("tags", "Tags"),
            ("genre", "Genre"),
            ("bpm", "BPM"),
            ("year", "Year"),
            ("duration", "Duration"),
            ("quality", "Quality"),
        ],
        # Spotify platform fields
        "spotify": [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("duration", "Duration"),
        ],
        # YouTube platform fields
        "youtube": [
            ("title", "Title"),
            ("artist", "Channel"),
            ("duration", "Duration"),
        ],
        # Discogs platform fields
        "discogs": [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("year", "Year"),
            ("country", "Country"),
        ],
        # Rekordbox platform fields
        "rekordbox": [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("bpm", "BPM"),
            ("genre", "Genre"),
            ("tags", "Tags"),
            ("quality", "Quality"),
        ],
    }

    @classmethod
    def get_fields_for_platform(cls, platform: str) -> list[tuple[str, str]]:
        """Get the field configuration for a specific platform.

        Args:
            platform: Platform name (default, spotify, youtube, discogs, rekordbox)

        Returns:
            List of (field_key, display_name) tuples
        """
        # Return platform-specific fields if available, otherwise default fields
        return cls._platform_fields.get(platform, cls._platform_fields["default"])

    @classmethod
    def should_show_platform_update_button(cls, platform: str) -> bool:
        """Determine if platform update button should be shown for this platform.

        Args:
            platform: Platform name

        Returns:
            True if update button should be shown, False otherwise
        """
        # Only show update button for local tracks
        return platform == "default" or platform == "local"
