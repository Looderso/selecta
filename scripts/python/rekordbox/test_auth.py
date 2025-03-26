# scripts/python/rekordbox/test_auth.py
#!/usr/bin/env python3
"""Example script demonstrating Rekordbox integration.

This script shows how to use the Rekordbox client to:
1. Get all tracks
2. Get all playlists
3. Search for tracks

Run this after setting up the Rekordbox database key with either:
- 'selecta rekordbox setup'
- 'selecta rekordbox download-key'
"""

import sys
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from selecta.data.init_db import initialize_database
from selecta.platform.platform_factory import PlatformFactory
from selecta.platform.rekordbox.client import RekordboxClient


def demonstrate_rekordbox_features():
    """Demonstrate key features of the Rekordbox client."""
    print("=== Selecta Rekordbox Integration Demo ===")

    # Initialize the database first
    initialize_database()

    # Create a Rekordbox client using the factory
    rekordbox = PlatformFactory.create("rekordbox")
    if not isinstance(rekordbox, RekordboxClient):
        print("Error: Failed to create Rekordbox client.")
        return

    # Check if authenticated
    if not rekordbox.is_authenticated():
        print("Not authenticated with Rekordbox.")
        print(
            "Please run 'selecta rekordbox setup' or 'selecta rekordbox download-key' to "
            "configure Rekordbox integration."
        )
        return

    # Get and display tracks
    try:
        tracks = rekordbox.get_all_tracks()
        print(f"\nYour Rekordbox Library ({len(tracks)} tracks):")

        for i, track in enumerate(tracks[:5]):
            print(f"{i + 1}. {track.artist_name} - {track.title}")
            if track.album_name:
                print(f"   Album: {track.album_name}")
            if track.genre:
                print(f"   Genre: {track.genre}")
            if track.bpm:
                print(f"   BPM: {track.bpm}")
            if track.key:
                print(f"   Key: {track.key}")

        if len(tracks) > 5:
            print(f"...and {len(tracks) - 5} more")
    except Exception as e:
        print(f"Error retrieving tracks: {e}")

    # Get and display playlists
    try:
        playlists = rekordbox.get_all_playlists()

        # Count actual playlists (not folders)
        actual_playlists = [p for p in playlists if not p.is_folder]

        print(f"\nYour Rekordbox Playlists ({len(actual_playlists)} playlists):")

        # Group playlists by parent
        children = {}
        for pl in playlists:
            if pl.parent_id not in children:
                children[pl.parent_id] = []
            children[pl.parent_id].append(pl)

        # Print first 5 root playlists
        root_playlists = sorted(children.get("root", []), key=lambda x: x.position)[:5]

        for i, playlist in enumerate(root_playlists):
            prefix = "📁 " if playlist.is_folder else "📄 "
            track_count = f" ({len(playlist.tracks)} tracks)" if not playlist.is_folder else ""
            print(f"{i + 1}. {prefix}{playlist.name}{track_count}")

        if len(children.get("root", [])) > 5:
            print(f"...and {len(children.get('root', [])) - 5} more top-level playlists/folders")
    except Exception as e:
        print(f"Error retrieving playlists: {e}")

    # Demonstrate search
    print("\nSearch Example:")
    search_term = "house"
    print(f"Searching for: '{search_term}'")

    try:
        search_results = rekordbox.search_tracks(search_term)
        for i, track in enumerate(search_results[:5]):
            print(f"{i + 1}. {track.artist_name} - {track.title}")
            if track.album_name:
                print(f"   Album: {track.album_name}")

        if len(search_results) > 5:
            print(f"...and {len(search_results) - 5} more results")
    except Exception as e:
        print(f"Error searching Rekordbox: {e}")

    print("\nDemo completed successfully!")


if __name__ == "__main__":
    demonstrate_rekordbox_features()
