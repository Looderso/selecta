#!/usr/bin/env python3
"""Test script for direct Discogs API requests."""

import os
import sys
import time
from pathlib import Path

import requests
from loguru import logger

# Add the src directory to the Python path to allow imports
src_path = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from selecta.core.data.database import get_db_path
from selecta.core.data.init_db import initialize_database
from selecta.core.data.repositories.settings_repository import SettingsRepository


def test_discogs_search_api(artist: str, track: str):
    """Test direct Discogs API search to check response times.

    Args:
        artist: Artist name to search for
        track: Track title to search for

    Returns:
        Response data and timing information
    """
    # Get Discogs credentials from database
    settings_repo = SettingsRepository()
    discogs_creds = settings_repo.get_credentials("discogs")

    if not discogs_creds:
        logger.error("No Discogs credentials found in database")
        return None

    # Extract tokens
    consumer_key = discogs_creds.client_id
    consumer_secret = discogs_creds.client_secret
    access_token = discogs_creds.access_token
    access_secret = (
        discogs_creds.refresh_token
    )  # In our DB, we use refresh_token to store Discogs token_secret

    print(f"Consumer Key: {consumer_key}")
    print(f"Access Token: {access_token}")

    if not consumer_key or not access_token:
        logger.error("Missing Discogs credentials")
        return None

    # Search parameters
    params = {"artist": artist, "track": track, "type": "release"}

    # Headers with authentication
    headers = {
        "Authorization": f"Discogs token={access_token}",
        "User-Agent": "SelectaApp/1.0 +http://looderso.com",  # Discogs requires a proper User-Agent
    }

    logger.info(f"Testing Discogs API search for '{artist} - {track}'")

    try:
        # Make the request
        start_time = time.time()

        response = requests.get(
            "https://api.discogs.com/database/search", params=params, headers=headers
        )

        # If that fails, try with OAuth1 authentication
        if response.status_code == 401:
            print("Token authentication failed, trying OAuth1...")
            try:
                from requests_oauthlib import OAuth1

                auth = OAuth1(
                    consumer_key,
                    client_secret=consumer_secret,
                    resource_owner_key=access_token,
                    resource_owner_secret=access_secret,
                )

                # Remove auth from headers for OAuth1
                headers.pop("Authorization", None)

                response = requests.get(
                    "https://api.discogs.com/database/search",
                    params=params,
                    headers=headers,
                    auth=auth,
                )
            except ImportError:
                print("Could not import OAuth1. Install with: pip install requests-oauthlib")
                return {"status": "error", "error": "OAuth1 module not available"}

        end_time = time.time()
        elapsed = end_time - start_time

        logger.info(f"API request time: {elapsed:.2f} seconds")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Found {len(data.get('results', []))} results")
            return {
                "status": "success",
                "time": elapsed,
                "results_count": len(data.get("results", [])),
                "data": data,
            }
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return {
                "status": "error",
                "time": elapsed,
                "status_code": response.status_code,
                "error": response.text,
            }
    except Exception as e:
        logger.exception(f"Error testing Discogs API: {e}")
        return {"status": "exception", "error": str(e)}


def main():
    """Run tests of the Discogs API."""
    # Configure logger
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    # Set environment variable for dev mode
    os.environ["SELECTA_DEV_MODE"] = "true"
    os.environ["SELECTA_DEV_DB_PATH"] = str(Path("./dev-database/dev_selecta.db").resolve())

    # Check which database will be used
    db_path = get_db_path()
    print(f"Using database at: {db_path}")

    # Initialize database with explicit path to dev database
    dev_db_path = Path("./dev-database/dev_selecta.db").resolve()
    print(f"Initializing database at: {dev_db_path}")
    initialize_database(dev_db_path)

    # Test some searches
    test_cases = [
        ("Daft Punk", "Around The World"),
        ("Radiohead", "Karma Police"),
        ("The Beatles", "Let It Be"),
    ]

    # Allow command line arguments to specify artist and track
    if len(sys.argv) >= 3:
        artist = sys.argv[1]
        track = sys.argv[2]
        test_cases = [(artist, track)]
        print(f"Using command line arguments to search for: {artist} - {track}")

    for artist, track in test_cases:
        result = test_discogs_search_api(artist, track)
        print(f"\n{artist} - {track}:")
        if result:
            print(f"  Status: {result['status']}")
            if "time" in result:
                print(f"  Time: {result['time']:.2f} seconds")
            print(f"  Results: {result.get('results_count', 'N/A')}")

            # Print the first few results if available
            if result["status"] == "success" and result.get("data", {}).get("results"):
                results = result["data"]["results"]
                print(f"\nFirst {min(3, len(results))} results:")
                for i, release in enumerate(results[:3]):
                    print(
                        f"  {i + 1}. {release.get('title', 'Unknown')} "
                        f"({release.get('year', 'Unknown')})"
                    )
                    if "format" in release:
                        print(f"     Format: {', '.join(release['format'])}")
                    if "label" in release:
                        print(f"     Label: {', '.join(release['label'])}")


if __name__ == "__main__":
    main()
