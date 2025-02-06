import os
from pathlib import Path


def get_token(token_file: str = ".discogs_token") -> str:
    """Get token from file or environment variable."""
    # Check environment variable first
    token = os.getenv("DISCOGS_TOKEN")
    if token:
        return token

    # Try to read from file
    token_path = Path(token_file)
    if token_path.exists():
        return token_path.read_text().strip()

    raise ValueError(
        "No token found. Set DISCOGS_TOKEN environment variable or create .discogs_token file"
    )
