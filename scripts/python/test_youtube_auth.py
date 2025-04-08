#!/usr/bin/env python3
"""Test script for YouTube authentication.

This script tests the YouTube OAuth authentication flow by:
1. Opening a browser window for the user to authorize the application
2. Capturing the callback with authorization code
3. Exchanging the code for access and refresh tokens
4. Displaying the access token if successful
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from loguru import logger

from selecta.core.platform.youtube.auth import YouTubeAuthManager


def main():
    """Run the YouTube authentication test."""
    logger.info("Starting YouTube authentication test")

    # Create YouTube auth manager
    auth_manager = YouTubeAuthManager()

    # Check if credentials are loaded
    if not auth_manager.client_id or not auth_manager.client_secret:
        logger.error("YouTube API credentials not found in .env file.")
        logger.error("Please add YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to your .env file.")
        return False

    logger.info("Starting YouTube OAuth authentication flow...")
    # Start the OAuth flow
    token_info = auth_manager.start_auth_flow()

    if not token_info:
        logger.error("YouTube authentication failed.")
        return False

    # Successfully authenticated
    logger.info("YouTube authentication successful!")
    logger.info(f"Access token: {token_info.get('access_token')[:20]}...")
    logger.info(f"Refresh token available: {'refresh_token' in token_info}")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
