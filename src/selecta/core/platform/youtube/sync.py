"""YouTube synchronization utilities."""

from datetime import UTC, datetime
from typing import Any, cast

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from selecta.core.data.database import get_session as get_db_session
from selecta.core.data.models.db import PlatformCredentials as PlatformMetadata
from selecta.core.data.models.db import Playlist, Track
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.core.platform.youtube.models import YouTubeVideo


def import_youtube_playlist(
    youtube_client: YouTubeClient, youtube_playlist_id: str, session: Session | None = None
) -> tuple[Playlist, list[Track]]:
    """Import a YouTube playlist into the local database.

    Args:
        youtube_client: Authenticated YouTube client
        youtube_playlist_id: YouTube playlist ID to import
        session: Database session (optional)

    Returns:
        Tuple of (created/updated playlist, list of imported tracks)

    Raises:
        ValueError: If import fails
    """
    if not youtube_client.is_authenticated():
        raise ValueError("YouTube client not authenticated")

    # Use provided session or create a new one
    close_session = False
    if session is None:
        session = get_db_session()
        close_session = True

    try:
        # Import the YouTube playlist
        videos, youtube_playlist = youtube_client.import_playlist_to_local(youtube_playlist_id)

        # Check if this playlist already exists in the database
        existing_playlist = session.execute(
            select(Playlist)
            .join(PlatformMetadata)
            .where(
                PlatformMetadata.platform == "youtube",
                PlatformMetadata.platform_id == youtube_playlist_id,
            )
        ).scalar_one_or_none()

        # Create or update the playlist
        if existing_playlist:
            playlist = existing_playlist
            logger.info(
                f"Updating existing playlist '{playlist.name}' from YouTube playlist "
                f"'{youtube_playlist.title}'"
            )
            # Update playlist details
            playlist.name = youtube_playlist.title
            playlist.description = youtube_playlist.description
            playlist.updated_at = datetime.now(UTC)
        else:
            # Create a new playlist
            playlist = Playlist(
                name=youtube_playlist.title,
                description=youtube_playlist.description,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(playlist)
            session.flush()  # Ensure playlist has an ID
            logger.info(
                f"Created new playlist '{playlist.name}' from YouTube playlist "
                f"'{youtube_playlist.title}'"
            )

            # Create YouTube platform metadata for the playlist
            playlist_metadata = PlatformMetadata(
                entity_id=playlist.id,
                entity_type="playlist",
                platform="youtube",
                platform_id=youtube_playlist.id,
                metadata={
                    "channel_id": youtube_playlist.channel_id,
                    "channel_title": youtube_playlist.channel_title,
                    "video_count": youtube_playlist.video_count,
                    "privacy_status": youtube_playlist.privacy_status,
                },
            )
            session.add(playlist_metadata)

        # Import all videos from the playlist
        imported_tracks: list[Track] = []
        for video in videos:
            track = import_youtube_video(youtube_client, video, session)
            if track and track not in playlist.tracks:
                playlist.tracks.append(track)
                imported_tracks.append(track)

        # Commit the changes if we created the session
        if close_session:
            session.commit()

        return playlist, imported_tracks

    except Exception as e:
        if close_session:
            session.rollback()
        logger.exception(f"Error importing YouTube playlist: {e}")
        raise ValueError(f"Failed to import YouTube playlist: {str(e)}") from e
    finally:
        if close_session:
            session.close()


def import_youtube_video(
    youtube_client: YouTubeClient, video: YouTubeVideo | dict[str, Any], session: Session
) -> Track | None:
    """Import a YouTube video as a track into the local database.

    Args:
        youtube_client: Authenticated YouTube client
        video: YouTube video object or API response dict
        session: Database session

    Returns:
        Created or updated Track object, or None if import fails
    """
    try:
        # Convert video dict to YouTubeVideo if needed
        if isinstance(video, dict):
            video = YouTubeVideo.from_youtube_dict(cast(dict[str, Any], video))

        # Check if this video already exists in the database
        existing_track = session.execute(
            select(Track)
            .join(PlatformMetadata)
            .where(
                PlatformMetadata.platform == "youtube",
                PlatformMetadata.platform_id == video.id,
            )
        ).scalar_one_or_none()

        # Create or update the track
        if existing_track:
            track = existing_track
            logger.debug(f"Found existing track for YouTube video: {video.title}")

            # Update track details if needed
            track.title = video.title
            track.artist = video.channel_title
            track.updated_at = datetime.now(UTC)

            # Update metadata if needed
            for metadata in track.platform_metadata:
                if metadata.platform == "youtube" and metadata.platform_id == video.id:
                    # Update any changed metadata
                    metadata.metadata = {
                        "title": video.title,
                        "description": video.description,
                        "channel_id": video.channel_id,
                        "channel_title": video.channel_title,
                        "duration_seconds": video.duration_seconds,
                        "thumbnail_url": video.thumbnail_url,
                        "view_count": video.view_count,
                        "like_count": video.like_count,
                        "published_at": video.published_at.isoformat()
                        if video.published_at
                        else None,
                    }
                    break
        else:
            # Create a new track
            track = Track(
                title=video.title,
                artist=video.channel_title,
                album="",  # YouTube videos don't have albums
                track_number=0,
                duration=video.duration_seconds or 0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(track)
            session.flush()  # Ensure track has an ID

            # Create YouTube platform metadata for the track
            track_metadata = PlatformMetadata(
                entity_id=track.id,
                entity_type="track",
                platform="youtube",
                platform_id=video.id,
                metadata={
                    "title": video.title,
                    "description": video.description,
                    "channel_id": video.channel_id,
                    "channel_title": video.channel_title,
                    "duration_seconds": video.duration_seconds,
                    "thumbnail_url": video.thumbnail_url,
                    "view_count": video.view_count,
                    "like_count": video.like_count,
                    "published_at": video.published_at.isoformat() if video.published_at else None,
                },
            )
            session.add(track_metadata)
            logger.debug(f"Created new track for YouTube video: {video.title}")

        return track
    except Exception as e:
        logger.exception(f"Error importing YouTube video: {e}")
        return None


def export_playlist_to_youtube(
    youtube_client: YouTubeClient,
    playlist_id: int,
    youtube_playlist_id: str | None = None,
    session: Session | None = None,
) -> str:
    """Export a local playlist to YouTube.

    Args:
        youtube_client: Authenticated YouTube client
        playlist_id: Local playlist ID to export
        youtube_playlist_id: Optional existing YouTube playlist ID to update
        session: Database session (optional)

    Returns:
        YouTube playlist ID

    Raises:
        ValueError: If export fails
    """
    if not youtube_client.is_authenticated():
        raise ValueError("YouTube client not authenticated")

    # Use provided session or create a new one
    close_session = False
    if session is None:
        session = get_db_session()
        close_session = True

    try:
        # Get the local playlist
        playlist = session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        ).scalar_one_or_none()

        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found")

        # Get YouTube video IDs for all tracks in the playlist
        youtube_video_ids = []
        for track in playlist.tracks:
            # Find YouTube metadata for this track
            for metadata in track.platform_metadata:
                if metadata.platform == "youtube":
                    youtube_video_ids.append(metadata.platform_id)
                    break

        # If no YouTube playlist ID was provided, check if playlist is already linked to YouTube
        if not youtube_playlist_id:
            for metadata in playlist.platform_metadata:
                if metadata.platform == "youtube":
                    youtube_playlist_id = metadata.platform_id
                    logger.info(f"Found existing YouTube playlist ID: {youtube_playlist_id}")
                    break

        # Export to YouTube
        result_playlist_id = youtube_client.export_tracks_to_playlist(
            playlist_name=playlist.name,
            video_ids=youtube_video_ids,
            existing_playlist_id=youtube_playlist_id,
        )

        # If this is a new YouTube playlist, create a metadata link
        if not youtube_playlist_id:
            # Get the YouTube playlist details
            youtube_playlist = youtube_client.get_playlist(result_playlist_id)

            # Create metadata for the playlist
            playlist_metadata = PlatformMetadata(
                entity_id=playlist.id,
                entity_type="playlist",
                platform="youtube",
                platform_id=result_playlist_id,
                metadata={
                    "channel_id": youtube_playlist.channel_id,
                    "channel_title": youtube_playlist.channel_title,
                    "video_count": youtube_playlist.video_count,
                    "privacy_status": youtube_playlist.privacy_status,
                },
            )
            session.add(playlist_metadata)

            # Update the local playlist
            playlist.updated_at = datetime.now(UTC)

            if close_session:
                session.commit()

        return result_playlist_id

    except Exception as e:
        if close_session:
            session.rollback()
        logger.exception(f"Error exporting playlist to YouTube: {e}")
        raise ValueError(f"Failed to export playlist to YouTube: {str(e)}") from e
    finally:
        if close_session:
            session.close()


def sync_youtube_playlist(
    youtube_client: YouTubeClient, playlist_id: int, session: Session | None = None
) -> tuple[int, int]:
    """Synchronize a local playlist with its YouTube counterpart.

    Args:
        youtube_client: Authenticated YouTube client
        playlist_id: Local playlist ID to sync
        session: Database session (optional)

    Returns:
        Tuple of (number of added tracks, number of removed tracks)

    Raises:
        ValueError: If sync fails
    """
    if not youtube_client.is_authenticated():
        raise ValueError("YouTube client not authenticated")

    # Use provided session or create a new one
    close_session = False
    if session is None:
        session = get_db_session()
        close_session = True

    try:
        # Get the local playlist
        playlist = session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        ).scalar_one_or_none()

        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found")

        # Find the YouTube playlist ID
        youtube_playlist_id = None
        for metadata in playlist.platform_metadata:
            if metadata.platform == "youtube":
                youtube_playlist_id = metadata.platform_id
                break

        if not youtube_playlist_id:
            raise ValueError("Playlist is not linked to a YouTube playlist")

        # Get the YouTube playlist and videos
        videos, youtube_playlist = youtube_client.import_playlist_to_local(youtube_playlist_id)

        # Get existing YouTube track IDs in the local playlist
        local_youtube_ids = set()
        for track in playlist.tracks:
            for metadata in track.platform_metadata:
                if metadata.platform == "youtube":
                    local_youtube_ids.add(metadata.platform_id)
                    break

        # Get YouTube track IDs from the YouTube playlist
        remote_youtube_ids = {video.id for video in videos}

        # Calculate differences
        to_add = remote_youtube_ids - local_youtube_ids
        to_remove = local_youtube_ids - remote_youtube_ids

        # Add new tracks
        added_count = 0
        for video in videos:
            if video.id in to_add:
                track = import_youtube_video(youtube_client, video, session)
                if track and track not in playlist.tracks:
                    playlist.tracks.append(track)
                    added_count += 1

        # Remove tracks that are no longer in the YouTube playlist
        removed_count = 0
        if to_remove:
            tracks_to_remove = []
            for track in playlist.tracks:
                for metadata in track.platform_metadata:
                    if metadata.platform == "youtube" and metadata.platform_id in to_remove:
                        tracks_to_remove.append(track)
                        removed_count += 1
                        break

            for track in tracks_to_remove:
                playlist.tracks.remove(track)

        # Update playlist metadata
        for metadata in playlist.platform_metadata:
            if metadata.platform == "youtube" and metadata.platform_id == youtube_playlist_id:
                metadata.metadata = {
                    "channel_id": youtube_playlist.channel_id,
                    "channel_title": youtube_playlist.channel_title,
                    "video_count": youtube_playlist.video_count,
                    "privacy_status": youtube_playlist.privacy_status,
                }
                break

        # Update the playlist
        playlist.name = youtube_playlist.title
        playlist.description = youtube_playlist.description
        playlist.updated_at = datetime.now(UTC)

        # Commit changes if we created the session
        if close_session:
            session.commit()

        return added_count, removed_count

    except Exception as e:
        if close_session:
            session.rollback()
        logger.exception(f"Error syncing YouTube playlist: {e}")
        raise ValueError(f"Failed to sync YouTube playlist: {str(e)}") from e
    finally:
        if close_session:
            session.close()
