#!/usr/bin/env python3
"""Debug script for testing Discogs client methods."""

import sys
import traceback
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger

from selecta.core.data.init_db import initialize_database
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.discogs.client import DiscogsClient

# Configure logging to see more details
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> "
    "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


def debug_discogs_client():
    """Debug specific Discogs client methods."""
    print("=== Discogs Client Debug ===")

    # Initialize the database
    initialize_database()

    # Create the Discogs client
    settings_repo = SettingsRepository()
    client = DiscogsClient(settings_repo=settings_repo)

    # Check authentication
    if not client.is_authenticated():
        print("⚠️ Not authenticated with Discogs.")
        print("Run 'selecta discogs auth' to authenticate first.")
        return

    print("✓ Authenticated with Discogs")

    # Set a breakpoint here to inspect the client
    # breakpoint()

    # Add your debug code here to test specific methods
    try:
        # Example: Get user profile
        print("\n=== Testing get_user_profile ===")
        user_profile = client.get_user_profile()
        print(f"User Profile: {user_profile}")

        # Example: Get collection
        print("\n=== Testing get_collection ===")
        print("Fetching collection items...")
        collection = client.get_collection()
        print(f"Collection items count: {len(collection)}")
        if collection:
            print(f"First item: {collection[0].release.artist} - {collection[0].release.title}")

        # Example: Get wantlist
        print("\n=== Testing get_wantlist ===")
        print("Fetching wantlist items...")
        wantlist = client.get_wantlist()
        print(f"Wantlist items count: {len(wantlist)}")
        if wantlist:
            print(f"First item: {wantlist[0].release.artist} - {wantlist[0].release.title}")

        # Example: Search releases
        print("\n=== Testing search_release ===")
        query = "Daft Punk"
        print(f"Searching for: '{query}'")
        search_results = client.search_release(query, limit=3)
        print(f"Search results count: {len(search_results)}")
        for i, release in enumerate(search_results):
            print(f"{i + 1}. {release.artist} - {release.title} ({release.year or 'Unknown Year'})")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTraceback:")
        traceback.print_exc()

        # Set another breakpoint to inspect the error state
        # breakpoint()

    print("\nDebug session completed")


if __name__ == "__main__":
    debug_discogs_client()
