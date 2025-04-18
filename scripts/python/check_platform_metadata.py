#!/usr/bin/env python
"""Debug script to check available metadata from different platforms."""

import pprint
from typing import Any

from loguru import logger

from selecta.core.platform.discogs.client import DiscogsClient
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.spotify.client import SpotifyClient


def print_metadata(title: str, metadata: dict[str, Any]) -> None:
    """Print metadata in a formatted way."""
    print(f"\n{'=' * 80}")
    print(f"=== {title} {'=' * (75 - len(title))}")
    print(f"{'=' * 80}\n")
    pprint.pprint(metadata, width=120, sort_dicts=False)


def check_spotify_metadata() -> None:
    """Check available metadata from Spotify."""
    # Initialize the Spotify client
    platform_factory = PlatformFactory()
    spotify_client = platform_factory.create("spotify")

    if not isinstance(spotify_client, SpotifyClient):
        logger.error("Failed to get Spotify client")
        return

    if not spotify_client.is_authenticated():
        success = spotify_client.authenticate()
        if not success:
            logger.error("Failed to authenticate with Spotify")
            return

    # Search for a famous track
    search_results = spotify_client.search_tracks("Tag am Meer Fantastischen Vier", limit=1)
    if not search_results:
        logger.error("No tracks found in Spotify search")
        return

    # Get the first track
    track = search_results[0]

    # Convert track dictionary to a SpotifyTrack object
    if isinstance(track, dict):
        from selecta.core.platform.spotify.models import SpotifyTrack

        track_obj = SpotifyTrack.from_spotify_dict(track)

        # Print track metadata
        print_metadata(
            "SPOTIFY TRACK",
            {
                "Track ID": track_obj.id,
                "Title": track_obj.name,
                "Artist(s)": track_obj.artist_names,
                "Album": track_obj.album_name,
                "Duration (ms)": track_obj.duration_ms,
                "URI": track_obj.uri,
                "Popularity": track_obj.popularity,
                "Explicit": track_obj.explicit,
                "Release Date": track_obj.album_release_date,
                "Raw Track Dict": track,
            },
        )
    else:
        # Print raw dictionary
        print_metadata("SPOTIFY TRACK", {"Result": track, "Type": type(track).__name__})

    # Try to get detailed audio features if available
    if hasattr(spotify_client, "client") and hasattr(spotify_client.client, "audio_features"):
        try:
            track_id = track_obj.id if isinstance(track, dict) else track.id
            audio_features = spotify_client.client.audio_features(track_id)[0]
            if audio_features:
                print_metadata("SPOTIFY AUDIO FEATURES", audio_features)
        except Exception as e:
            logger.error(f"Error getting audio features: {e}")


def check_discogs_metadata() -> None:
    """Check available metadata from Discogs."""
    # Initialize the Discogs client
    platform_factory = PlatformFactory()
    discogs_client = platform_factory.create("discogs")

    if not isinstance(discogs_client, DiscogsClient):
        logger.error("Failed to get Discogs client")
        return

    if not discogs_client.is_authenticated():
        success = discogs_client.authenticate()
        if not success:
            logger.error("Failed to authenticate with Discogs")
            return

    # Discogs doesn't have a direct search_releases method, but we can check the collection
    try:
        # Get the user's collection first
        collection = discogs_client.get_collection()

        if not collection or len(collection) == 0:
            # If collection is empty, try to get a release directly
            release_id = 1362628  # A Night at the Opera by Queen
            release = discogs_client.get_release_by_id(release_id)
            print_metadata("DISCOGS RELEASE (DIRECT FETCH)", release.__dict__)
        else:
            # Use the first item from collection
            vinyl = collection[0]
            print_metadata("DISCOGS COLLECTION VINYL", vinyl.__dict__)

            # Try to get detailed release info
            if hasattr(vinyl, "release"):
                detailed_release = discogs_client.get_release_by_id(vinyl.release.id)
                print_metadata("DISCOGS DETAILED RELEASE", detailed_release.__dict__)

    except Exception as e:
        logger.error(f"Error getting Discogs data: {e}")

        # Fallback to just showing user profile as proof of authentication
        try:
            user_profile = discogs_client.get_user_profile()
            print_metadata("DISCOGS USER PROFILE", user_profile)
        except Exception as e2:
            logger.error(f"Error getting user profile: {e2}")


def main():
    """Run the metadata check script."""
    print("Starting platform metadata check...")

    try:
        check_spotify_metadata()
    except Exception as e:
        logger.error(f"Error checking Spotify metadata: {e}")

    try:
        check_discogs_metadata()
    except Exception as e:
        logger.error(f"Error checking Discogs metadata: {e}")

    print("\nMetadata check complete!")


if __name__ == "__main__":
    main()
