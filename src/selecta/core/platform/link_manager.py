"""Link manager for track-level operations between platforms and the library database.

This module provides the PlatformLinkManager class that focuses exclusively on track-level
operations for linking tracks between platforms and the local library database.
"""

import json
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from selecta.core.data.database import get_session
from selecta.core.data.models.db import Album, Track
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.platform.abstract_platform import AbstractPlatform


class PlatformLinkManager:
    """Manager for linking tracks between platforms and the library database.

    This class focuses exclusively on track-level operations, providing standardized
    methods for importing tracks from platforms and linking them to library tracks.
    For playlist-level operations, use PlatformSyncManager instead.
    """

    def __init__(
        self,
        platform_client: AbstractPlatform,
        track_repo: TrackRepository | None = None,
        session: Session | None = None,
    ):
        """Initialize the link manager.

        Args:
            platform_client: The platform client to use for link operations
            track_repo: Optional track repository (will create one if not provided)
            session: Optional SQLAlchemy session (will use track_repo's session if not provided)
        """
        self.platform_client = platform_client
        self.track_repo = track_repo or TrackRepository()
        self.session = session or self.track_repo.session or get_session()
        self.platform_name = self._get_platform_name()

    def _extract_attribute(self, obj: Any, possible_names: list[str], default: Any = None) -> Any:
        """Safely extract an attribute from an object.

        Tries multiple possible attribute names until one is found.

        Args:
            obj: The object to extract from
            possible_names: List of attribute names to try
            default: Default value if no attribute is found

        Returns:
            The attribute value or default
        """
        # Check if obj is a dictionary
        if isinstance(obj, dict):
            for name in possible_names:
                if name in obj:
                    return obj[name]
            return default

        # Check if obj is an object with attributes
        for name in possible_names:
            if hasattr(obj, name):
                return getattr(obj, name)

        return default

    def _get_platform_name(self) -> str:
        """Get the name of the platform from the client class.

        Returns:
            The platform name (e.g., 'spotify', 'rekordbox', 'discogs')
        """
        # Extract platform name from the client class name
        class_name = self.platform_client.__class__.__name__
        if class_name.endswith("Client"):
            return class_name[:-6].lower()
        return class_name.lower()

    def _get_or_create_album(self, album_name: str, artist_name: str, year: int | None = None) -> Album | None:
        """Get an existing album or create a new one.

        Args:
            album_name: The album title
            artist_name: The album artist
            year: Optional release year

        Returns:
            The album instance (either existing or newly created) or None if inputs are invalid
        """
        if not album_name or not artist_name:
            logger.warning("Cannot create album: Missing album name or artist name")
            return None

        # First try to find an existing album with the same title and artist
        existing_album = (
            self.session.query(Album).filter(Album.title == album_name, Album.artist == artist_name).first()
        )

        if existing_album:
            logger.debug(f"Found existing album: {existing_album.title} by {existing_album.artist}")
            return existing_album

        # Create a new album
        album_data = {
            "title": album_name,
            "artist": artist_name,
        }

        if year:
            album_data["release_year"] = year

        logger.debug(f"Creating new album: {album_name} by {artist_name}")
        album = Album(**album_data)
        self.session.add(album)
        self.session.flush()  # Get the ID without committing

        return album

    def import_track(self, platform_track: Any) -> Track:
        """Import a track from platform to local database.

        This method handles the import of platform-specific track objects to the
        library database, creating or updating Track objects and storing platform
        metadata in TrackPlatformInfo records.

        Args:
            platform_track: The platform-specific track object
                Could be a SpotifyTrack, RekordboxTrack, YouTubeVideo, etc.

        Returns:
            The local Track object (either newly created or existing)

        Raises:
            ValueError: If track cannot be imported
        """
        # Log the track type we're importing
        track_type = type(platform_track).__name__
        logger.info(f"Importing {self.platform_name} track of type {track_type}")

        # For debug purposes, dump the platform_track data
        if hasattr(platform_track, "__dict__"):
            logger.info(f"Platform track data: {platform_track.__dict__}")
        elif isinstance(platform_track, dict):
            logger.info(f"Platform track data (dict): {platform_track}")
        else:
            logger.info(f"Platform track attributes: {dir(platform_track)}")

        # Extract common attributes based on the platform
        if self.platform_name == "spotify":
            # Handle Spotify track format - with detailed debug
            if hasattr(platform_track, "__class__") and platform_track.__class__.__name__ == "SpotifyTrack":
                # Detailed logging for SpotifyTrack instances
                logger.info(
                    f"Importing SpotifyTrack: {platform_track.name} " f"by {', '.join(platform_track.artist_names)}"
                )

                # Extract from SpotifyTrack dataclass (from spotify/models.py)
                # Use safe access with default values to prevent attribute errors
                track_data = {
                    "title": getattr(platform_track, "name", "Unknown Track"),
                    "is_available_locally": False,  # This is a Spotify track, not a local file
                }

                # Get artist names (required field)
                artist_names = getattr(platform_track, "artist_names", [])
                if artist_names:
                    track_data["artist"] = ", ".join(artist_names)
                else:
                    track_data["artist"] = "Unknown Artist"

                # Handle optional fields with safe access
                duration_ms = getattr(platform_track, "duration_ms", None)
                if duration_ms is not None:
                    track_data["duration_ms"] = duration_ms

                # Handle album and release date for year
                album_name = getattr(platform_track, "album_name", None)
                album_release_date = getattr(platform_track, "album_release_date", None)
                year = None

                if album_release_date and len(album_release_date) >= 4:
                    try:
                        year = int(album_release_date[:4])
                        track_data["year"] = year
                    except ValueError:
                        logger.warning(f"Could not parse year from date {album_release_date}")

                # If we have album info, get or create the album object
                if album_name and artist_names:
                    album = self._get_or_create_album(album_name, track_data["artist"], year)
                    if album:
                        track_data["album_id"] = album.id

                # Get required IDs with safe access
                platform_id = getattr(platform_track, "id", "")
                uri = getattr(platform_track, "uri", "")

                # Debug logging for track data
                logger.info(f"Extracted track data: {track_data}")
                logger.info(f"Platform ID: {platform_id}, URI: {uri}")

            else:
                # Dictionary or other object type
                # Handle with safe type checking
                track_data = {}

                # Get title
                if hasattr(platform_track, "name"):
                    track_data["title"] = platform_track.name
                elif isinstance(platform_track, dict) and "name" in platform_track:
                    track_data["title"] = platform_track["name"]
                else:
                    track_data["title"] = "Unknown Track"
                    logger.warning("Could not find track name in Spotify track object")

                # Get artist
                artist_names = []
                if hasattr(platform_track, "artist_names"):
                    artist_names = platform_track.artist_names
                elif isinstance(platform_track, dict):
                    if "artist_names" in platform_track:
                        artist_names = platform_track["artist_names"]
                    elif "artists" in platform_track and isinstance(platform_track["artists"], list):
                        for artist in platform_track["artists"]:
                            if isinstance(artist, dict) and "name" in artist:
                                artist_names.append(artist["name"])

                track_data["artist"] = ", ".join(artist_names) if artist_names else "Unknown Artist"
                if not artist_names:
                    logger.warning("Could not find artist names in Spotify track object")

                # Get duration
                if hasattr(platform_track, "duration_ms"):
                    track_data["duration_ms"] = platform_track.duration_ms
                elif isinstance(platform_track, dict) and "duration_ms" in platform_track:
                    track_data["duration_ms"] = platform_track["duration_ms"]
                else:
                    track_data["duration_ms"] = 0

                # Set as non-local track
                track_data["is_available_locally"] = False

                # Get platform IDs
                if hasattr(platform_track, "id"):
                    platform_id = platform_track.id
                elif isinstance(platform_track, dict) and "id" in platform_track:
                    platform_id = platform_track["id"]
                else:
                    platform_id = ""
                    logger.warning("Could not find platform ID in Spotify track object")

                if hasattr(platform_track, "uri"):
                    uri = platform_track.uri
                elif isinstance(platform_track, dict) and "uri" in platform_track:
                    uri = platform_track["uri"]
                else:
                    uri = ""

            # Create additional platform metadata
            if hasattr(platform_track, "__class__") and platform_track.__class__.__name__ == "SpotifyTrack":
                # Handle SpotifyTrack metadata with safe attribute access
                platform_metadata = {}

                # Add popularity if available
                popularity = getattr(platform_track, "popularity", None)
                if popularity is not None:
                    platform_metadata["popularity"] = popularity

                # Add explicit flag if available
                explicit = getattr(platform_track, "explicit", None)
                if explicit is not None:
                    platform_metadata["explicit"] = explicit

                # Add preview URL if available
                preview_url = getattr(platform_track, "preview_url", None)
                if preview_url:
                    platform_metadata["preview_url"] = preview_url

                # Log metadata
                logger.info(f"Extracted Spotify metadata: {platform_metadata}")
            else:
                # Handle dictionary objects with safe access
                platform_metadata = {}

                # Add popularity
                if hasattr(platform_track, "popularity"):
                    platform_metadata["popularity"] = platform_track.popularity
                elif isinstance(platform_track, dict) and "popularity" in platform_track:
                    platform_metadata["popularity"] = platform_track["popularity"]
                else:
                    platform_metadata["popularity"] = 0

                # Add explicit flag
                if hasattr(platform_track, "explicit"):
                    platform_metadata["explicit"] = platform_track.explicit
                elif isinstance(platform_track, dict) and "explicit" in platform_track:
                    platform_metadata["explicit"] = platform_track["explicit"]
                else:
                    platform_metadata["explicit"] = False

                # Get album info if available
                album_info = getattr(
                    platform_track,
                    "album",
                    platform_track.get("album", {}) if isinstance(platform_track, dict) else {},
                )

                if album_info:
                    album_name = ""
                    release_date = ""
                    year = None

                    if isinstance(album_info, dict):
                        album_name = album_info.get("name", "")
                        # Try to extract year from release date
                        release_date = album_info.get("release_date", "")
                    else:
                        album_name = getattr(album_info, "name", "")
                        release_date = getattr(album_info, "release_date", "")

                    if release_date and len(release_date) >= 4:
                        try:
                            year = int(release_date[:4])
                            track_data["year"] = year
                        except ValueError:
                            logger.warning(f"Could not parse year from date {release_date}")

                    # Create album object if we have name and artist
                    if album_name and track_data.get("artist"):
                        album = self._get_or_create_album(album_name, track_data["artist"], year)
                        if album:
                            track_data["album_id"] = album.id

        elif self.platform_name == "rekordbox":
            # Handle Rekordbox track format
            track_data = {
                "title": getattr(
                    platform_track,
                    "title",
                    platform_track.get("title", "") if isinstance(platform_track, dict) else "",
                ),
                "artist": getattr(
                    platform_track,
                    "artist_name",
                    platform_track.get("artist_name", "") if isinstance(platform_track, dict) else "",
                ),
                "duration_ms": getattr(
                    platform_track,
                    "duration_ms",
                    platform_track.get("duration_ms", 0) if isinstance(platform_track, dict) else 0,
                ),
                "bpm": getattr(
                    platform_track,
                    "bpm",
                    platform_track.get("bpm", None) if isinstance(platform_track, dict) else None,
                ),
            }

            # Get album info if available
            album_name = getattr(
                platform_track,
                "album_name",
                platform_track.get("album_name", "") if isinstance(platform_track, dict) else "",
            )
            year = getattr(
                platform_track,
                "year",
                platform_track.get("year", None) if isinstance(platform_track, dict) else None,
            )

            if album_name and track_data["artist"]:
                album = self._get_or_create_album(album_name, track_data["artist"], year)
                if album:
                    track_data["album_id"] = album.id

            platform_id = str(
                getattr(
                    platform_track,
                    "id",
                    platform_track.get("id", "") if isinstance(platform_track, dict) else "",
                )
            )
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "bpm": getattr(
                    platform_track,
                    "bpm",
                    platform_track.get("bpm", 0) if isinstance(platform_track, dict) else 0,
                ),
                "key": getattr(
                    platform_track,
                    "key",
                    platform_track.get("key", "") if isinstance(platform_track, dict) else "",
                ),
                "rating": getattr(
                    platform_track,
                    "rating",
                    platform_track.get("rating", 0) if isinstance(platform_track, dict) else 0,
                ),
            }

        elif self.platform_name == "discogs":
            # Handle Discogs release format
            track_data = {
                "title": getattr(
                    platform_track,
                    "title",
                    platform_track.get("title", "") if isinstance(platform_track, dict) else "",
                ),
                "artist": getattr(
                    platform_track,
                    "artist",
                    platform_track.get("artist", "") if isinstance(platform_track, dict) else "",
                ),
                # Discogs doesn't typically include duration in ms
            }

            # Get year and album information
            year = getattr(
                platform_track,
                "year",
                platform_track.get("year", None) if isinstance(platform_track, dict) else None,
            )
            if year:
                track_data["year"] = year

            # Get album name - Discogs often stores this as "release_title"
            album_name = getattr(
                platform_track,
                "release_title",
                platform_track.get("release_title", "") if isinstance(platform_track, dict) else "",
            )

            if not album_name:
                # Try album field as fallback
                album_name = getattr(
                    platform_track,
                    "album",
                    platform_track.get("album", "") if isinstance(platform_track, dict) else "",
                )

            if album_name and track_data["artist"]:
                album = self._get_or_create_album(album_name, track_data["artist"], year)
                if album:
                    track_data["album_id"] = album.id

            platform_id = str(
                getattr(
                    platform_track,
                    "id",
                    platform_track.get("id", "") if isinstance(platform_track, dict) else "",
                )
            )
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "genres": getattr(
                    platform_track,
                    "genres",
                    platform_track.get("genres", []) if isinstance(platform_track, dict) else [],
                ),
                "styles": getattr(
                    platform_track,
                    "styles",
                    platform_track.get("styles", []) if isinstance(platform_track, dict) else [],
                ),
                "format": getattr(
                    platform_track,
                    "format",
                    platform_track.get("format", "") if isinstance(platform_track, dict) else "",
                ),
            }
        elif self.platform_name == "youtube":
            # Handle YouTube video format
            track_data = {
                "title": getattr(
                    platform_track,
                    "title",
                    platform_track.get("title", "") if isinstance(platform_track, dict) else "",
                ),
                "artist": getattr(
                    platform_track,
                    "channel_title",
                    platform_track.get("channel_title", "") if isinstance(platform_track, dict) else "",
                ),
                "is_available_locally": False,  # YouTube videos are not local files
            }

            # Get video duration if available
            duration_ms = getattr(
                platform_track,
                "duration_ms",
                platform_track.get("duration_ms", 0) if isinstance(platform_track, dict) else 0,
            )
            if duration_ms:
                track_data["duration_ms"] = duration_ms

            # Get published year if available
            published_at = getattr(
                platform_track,
                "published_at",
                platform_track.get("published_at", "") if isinstance(platform_track, dict) else "",
            )
            year = None
            if published_at and len(published_at) >= 4:
                try:
                    year = int(published_at[:4])
                    track_data["year"] = year
                except ValueError:
                    logger.warning(f"Could not parse year from published_at {published_at}")

            # YouTube videos don't typically have album info, but we could create one
            # based on channel/playlist if needed in the future

            platform_id = getattr(
                platform_track,
                "video_id",
                platform_track.get("video_id", "") if isinstance(platform_track, dict) else "",
            )
            uri = getattr(
                platform_track,
                "url",
                platform_track.get("url", "") if isinstance(platform_track, dict) else "",
            )

            # Create platform metadata
            platform_metadata = {
                "view_count": getattr(
                    platform_track,
                    "view_count",
                    platform_track.get("view_count", 0) if isinstance(platform_track, dict) else 0,
                ),
                "like_count": getattr(
                    platform_track,
                    "like_count",
                    platform_track.get("like_count", 0) if isinstance(platform_track, dict) else 0,
                ),
                "channel_id": getattr(
                    platform_track,
                    "channel_id",
                    platform_track.get("channel_id", "") if isinstance(platform_track, dict) else "",
                ),
                "thumbnail_url": getattr(
                    platform_track,
                    "thumbnail_url",
                    platform_track.get("thumbnail_url", "") if isinstance(platform_track, dict) else "",
                ),
            }
        else:
            raise ValueError(f"Unsupported platform: {self.platform_name}")

        # Validate essential track data - if missing title or artist, raise exception
        if not track_data.get("title") or not track_data.get("artist"):
            logger.error("Cannot import track with missing title or artist")
            logger.error(f"Track data: {track_data}")

            # Gather platform information for better error reporting
            platform_description = f"{self.platform_name} track"
            if platform_id:
                platform_description += f" with ID {platform_id}"

            error_message = f"Failed to import {platform_description}: "
            if not track_data.get("title") and not track_data.get("artist"):
                error_message += "Missing both title and artist"
            elif not track_data.get("title"):
                error_message += f"Missing title (Artist: {track_data.get('artist', '')})"
            else:
                error_message += f"Missing artist (Title: {track_data.get('title', '')})"

            raise ValueError(error_message)

        # Log the final track data we'll use to create/update the track
        logger.info(f"Final track data for database: {track_data}")

        # Check if this track already exists in our database
        existing_track = None

        # First try to find by platform ID
        if platform_id:
            existing_track = self.track_repo.get_by_platform_id(self.platform_name, platform_id)

        # If not found by ID, try by title and artist
        if not existing_track and track_data.get("title") and track_data.get("artist"):
            # Find by title + artist
            query = f"{track_data['title']} {track_data['artist']}"
            matches, _ = self.track_repo.search(query, limit=1)
            if matches:
                existing_track = matches[0]

        if existing_track:
            # Update the existing track with any new information
            # Use preserve_existing=True to avoid overwriting existing fields
            logger.info(f"Updating existing track: {existing_track.id} - {existing_track.title}")

            # If we're trying to update with a new album and the track already has one,
            # don't overwrite
            if "album_id" in track_data and existing_track.album_id is not None:
                logger.debug(
                    f"Track already has album_id {existing_track.album_id}, "
                    f"not overwriting with {track_data.get('album_id')}"
                )
                track_data.pop("album_id")

            self.track_repo.update(existing_track.id, track_data, preserve_existing=True)
            track = existing_track
        else:
            # Create a new track
            logger.info(f"Creating new track with data: {track_data}")
            # Commit any pending album creations to ensure album_id references are valid
            if self.session.new:
                logger.debug("Committing pending objects (e.g. albums) before track creation")
                self.session.commit()

            track = self.track_repo.create(track_data)
            logger.info(f"Created new track: {track.id} - {track.title} by {track.artist}")

        # Add or update platform info
        if platform_id:
            # Convert platform metadata to JSON string
            metadata_json = json.dumps(platform_metadata)
            logger.info(
                f"Adding platform info for track {track.id}: platform={self.platform_name}, "
                f"platform_id={platform_id}"
            )

            self.track_repo.add_platform_info(
                track_id=track.id,
                platform=self.platform_name,
                platform_id=platform_id,
                uri=uri,
                metadata=metadata_json,
            )
            logger.info(f"Successfully added platform info for track {track.id}")

        return track

    def link_tracks(self, local_track_id: int, platform_track: Any) -> bool:
        """Link a local track with platform-specific metadata.

        Args:
            local_track_id: The local track ID
            platform_track: The platform-specific track object

        Returns:
            True if successful

        Raises:
            ValueError: If track cannot be linked
        """
        # Get the local track
        local_track = self.track_repo.get_by_id(local_track_id)
        if not local_track:
            raise ValueError(f"Local track with ID {local_track_id} not found")

        # Extract platform metadata
        if self.platform_name == "spotify":
            # Handle Spotify track format
            platform_id = getattr(
                platform_track,
                "id",
                platform_track.get("id", "") if isinstance(platform_track, dict) else "",
            )
            uri = getattr(
                platform_track,
                "uri",
                platform_track.get("uri", "") if isinstance(platform_track, dict) else "",
            )

            # Create additional platform metadata
            platform_metadata = {
                "popularity": getattr(
                    platform_track,
                    "popularity",
                    platform_track.get("popularity", 0) if isinstance(platform_track, dict) else 0,
                ),
                "explicit": getattr(
                    platform_track,
                    "explicit",
                    platform_track.get("explicit", False) if isinstance(platform_track, dict) else False,
                ),
            }

            # Get album info if available
            album_info = getattr(
                platform_track,
                "album",
                platform_track.get("album", {}) if isinstance(platform_track, dict) else {},
            )
            if album_info and isinstance(album_info, dict) and "images" in album_info:
                images = album_info["images"]
                if images:
                    # Find largest image for best quality when resizing
                    sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
                    if sorted_images:
                        platform_metadata["artwork_url"] = sorted_images[0].get("url")

        elif self.platform_name == "rekordbox":
            # Handle Rekordbox track format
            platform_id = str(
                getattr(
                    platform_track,
                    "id",
                    platform_track.get("id", "") if isinstance(platform_track, dict) else "",
                )
            )
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "bpm": getattr(
                    platform_track,
                    "bpm",
                    platform_track.get("bpm", 0) if isinstance(platform_track, dict) else 0,
                ),
                "key": getattr(
                    platform_track,
                    "key",
                    platform_track.get("key", "") if isinstance(platform_track, dict) else "",
                ),
                "rating": getattr(
                    platform_track,
                    "rating",
                    platform_track.get("rating", 0) if isinstance(platform_track, dict) else 0,
                ),
            }

        elif self.platform_name == "discogs":
            # Handle Discogs release format
            platform_id = str(
                getattr(
                    platform_track,
                    "id",
                    platform_track.get("id", "") if isinstance(platform_track, dict) else "",
                )
            )
            uri = None

            # Create additional platform metadata
            platform_metadata = {
                "genres": getattr(
                    platform_track,
                    "genres",
                    platform_track.get("genres", []) if isinstance(platform_track, dict) else [],
                ),
                "styles": getattr(
                    platform_track,
                    "styles",
                    platform_track.get("styles", []) if isinstance(platform_track, dict) else [],
                ),
                "format": getattr(
                    platform_track,
                    "format",
                    platform_track.get("format", "") if isinstance(platform_track, dict) else "",
                ),
            }

        elif self.platform_name == "youtube":
            # Handle YouTube video format
            platform_id = getattr(
                platform_track,
                "video_id",
                platform_track.get("video_id", "") if isinstance(platform_track, dict) else "",
            )
            uri = getattr(
                platform_track,
                "url",
                platform_track.get("url", "") if isinstance(platform_track, dict) else "",
            )

            # Create platform metadata
            platform_metadata = {
                "view_count": getattr(
                    platform_track,
                    "view_count",
                    platform_track.get("view_count", 0) if isinstance(platform_track, dict) else 0,
                ),
                "like_count": getattr(
                    platform_track,
                    "like_count",
                    platform_track.get("like_count", 0) if isinstance(platform_track, dict) else 0,
                ),
                "channel_id": getattr(
                    platform_track,
                    "channel_id",
                    platform_track.get("channel_id", "") if isinstance(platform_track, dict) else "",
                ),
                "channel_title": getattr(
                    platform_track,
                    "channel_title",
                    platform_track.get("channel_title", "") if isinstance(platform_track, dict) else "",
                ),
                "thumbnail_url": getattr(
                    platform_track,
                    "thumbnail_url",
                    platform_track.get("thumbnail_url", "") if isinstance(platform_track, dict) else "",
                ),
            }

        else:
            raise ValueError(f"Unsupported platform: {self.platform_name}")

        if not platform_id:
            raise ValueError(f"No valid platform ID found for {self.platform_name} track")

        # Convert platform metadata to JSON string
        metadata_json = json.dumps(platform_metadata)

        # Add or update platform info
        self.track_repo.add_platform_info(
            track_id=local_track_id,
            platform=self.platform_name,
            platform_id=platform_id,
            uri=uri,
            metadata=metadata_json,
        )

        return True
