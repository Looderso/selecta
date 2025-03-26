#!/usr/bin/env python3
"""Example script demonstrating Discogs integration.

This script shows how to use the Discogs client to:
1. Get user profile information
2. List collection items
3. List wantlist items
4. Search for releases

Run this after authenticating with 'selecta discogs auth'.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from selecta.data.init_db import initialize_database
from selecta.platform.discogs.client import DiscogsClient
from selecta.platform.platform_factory import PlatformFactory


def demonstrate_discogs_features():
    """Demonstrate key features of the Discogs client."""
    print("=== Selecta Discogs Integration Demo ===")

    # Initialize the database first
    initialize_database()

    # Create a Discogs client using the factory
    discogs = PlatformFactory.create("discogs")
    assert isinstance(discogs, DiscogsClient)

    if not discogs:
        print("Error: Failed to create Discogs client.")
        return

    # Check if authenticated
    if not discogs.is_authenticated():
        print("Not authenticated with Discogs.")
        print("Please run 'selecta discogs auth' to authenticate first.")
        return

    # Display user info
    user_profile = discogs.get_user_profile()
    print(f"\nConnected as: {user_profile['username']}")
    print(f"Discogs user ID: {user_profile['id']}")

    # Retrieve and display collection
    try:
        collection = discogs.get_collection()
        print(f"\nYour Collection ({len(collection)} items):")

        for i, vinyl in enumerate(collection[:5]):
            release = vinyl.release
            print(f"{i + 1}. {release.artist} - {release.title} ({release.year or 'Unknown Year'})")
            if release.label:
                print(f"   Label: {release.label}, Cat#: {release.catno or 'N/A'}")
            if release.format:
                print(f"   Format: {', '.join(release.format)}")

        if len(collection) > 5:
            print(f"...and {len(collection) - 5} more")
    except Exception as e:
        print(f"Error retrieving collection: {e}")

    # Retrieve and display wantlist
    try:
        wantlist = discogs.get_wantlist()
        print(f"\nYour Wantlist ({len(wantlist)} items):")

        for i, vinyl in enumerate(wantlist[:5]):
            release = vinyl.release
            print(f"{i + 1}. {release.artist} - {release.title} ({release.year or 'Unknown Year'})")
            if release.label:
                print(f"   Label: {release.label}, Cat#: {release.catno or 'N/A'}")

        if len(wantlist) > 5:
            print(f"...and {len(wantlist) - 5} more")
    except Exception as e:
        print(f"Error retrieving wantlist: {e}")

    # Demonstrate search
    print("\nSearch Example:")
    search_term = "Daft Punk"
    print(f"Searching for: '{search_term}'")

    try:
        search_results = discogs.search_release(search_term, limit=5)
        for i, release in enumerate(search_results):
            print(f"{i + 1}. {release.artist} - {release.title} ({release.year or 'Unknown Year'})")
            if release.label:
                print(f"   Label: {release.label}, Cat#: {release.catno or 'N/A'}")
            if release.format:
                print(f"   Format: {', '.join(release.format) if release.format else 'N/A'}")
    except Exception as e:
        print(f"Error searching Discogs: {e}")

    print("\nDemo completed successfully!")


if __name__ == "__main__":
    demonstrate_discogs_features()
