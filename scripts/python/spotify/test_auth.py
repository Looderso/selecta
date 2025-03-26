#!/usr/bin/env python3
"""Example script demonstrating Spotify integration.

This script shows how to use the Spotify client to:
1. Get user profile information
2. List playlists
3. Get tracks from a playlist
4. Get audio features for tracks
5. Search for tracks

Run this after authenticating with 'selecta spotify auth'.
"""

import sys
from pathlib import Path

from selecta.platform.spotify.client import SpotifyClient

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from selecta.data.init_db import initialize_database
from selecta.platform.platform_factory import PlatformFactory


def demonstrate_spotify_features():
    """Demonstrate key features of the Spotify client."""
    print("=== Selecta Spotify Integration Demo ===")

    # Initialize the database first
    initialize_database()

    # Create a Spotify client using the factory
    spotify = PlatformFactory.create("spotify")
    assert isinstance(spotify, SpotifyClient)

    if not spotify:
        print("Error: Failed to create Spotify client.")
        return

    # Check if authenticated
    if not spotify.is_authenticated():
        print("Not authenticated with Spotify.")
        print("Please run 'selecta spotify auth' to authenticate first.")
        return

    # Display user info
    user_profile = spotify.get_user_profile()
    print(user_profile)
    print(f"Connected as: {user_profile['display_name']}")

    # Retrieve and display playlists
    playlists = spotify.get_playlists()
    print(f"\nYour Playlists ({len(playlists)}):")

    for i, playlist in enumerate(playlists[:5]):
        print(f"{i + 1}. {playlist['name']} ({playlist['tracks']['total']} tracks)")

    if len(playlists) > 5:
        print(f"...and {len(playlists) - 5} more")

    # If playlists exist, show tracks from the first one
    if playlists:
        playlist_id = playlists[0]["id"]
        playlist_name = playlists[0]["name"]

        print(f"\nTracks from '{playlist_name}':")
        tracks = spotify.get_playlist_tracks(playlist_id)

        for i, track in enumerate(tracks[:10]):
            artists = ", ".join(track.artist_names)
            print(f"{i + 1}. {artists} - {track.name}")

        if len(tracks) > 10:
            print(f"...and {len(tracks) - 10} more")

    # Demonstrate search
    print("\nSearch Example:")
    search_term = "Daft Punk"
    print(f"Searching for: '{search_term}'")
    search_results = spotify.search_tracks(search_term, limit=5)

    for i, track in enumerate(search_results):
        artists = ", ".join(track.artist_names)
        print(f"{i + 1}. {artists} - {track.name} ({track.album_name})")

    print("\nDemo completed successfully!")


demonstrate_spotify_features()
