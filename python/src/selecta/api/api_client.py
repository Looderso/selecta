import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from mutagen.easyid3 import EasyID3

from selecta.api.auth_token import get_token


@dataclass
class DiscogsConfig:
    token: str
    user_agent: str = "MyDiscogsClient/1.0"


class DiscogsClient:
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url="https://api.discogs.com",
            headers={
                "Authorization": f"Discogs token={config.token}",
                "User-Agent": config.user_agent,
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def search_release(
        self, artist: str, title: str, format: str = None
    ) -> list[dict[str, Any]]:
        params = {"q": f"{artist} {title}", "type": "release", "artist": artist, "track": title}
        if format:
            params["format"] = format
        response = await self.client.get("/database/search", params=params)
        response.raise_for_status()
        return response.json()["results"]


def read_metadata(filepath: str) -> dict[str, str]:
    """Read metadata from MP3 file."""
    audio = EasyID3(filepath)
    return {"artist": audio.get("artist", [""])[0], "title": audio.get("title", [""])[0]}


async def search_discogs_from_file(
    filepath: str, discogs_token: str, format: str = None
) -> list[dict[str, Any]]:
    """Read metadata from file and search Discogs."""
    metadata = read_metadata(filepath)
    config = DiscogsConfig(token=discogs_token)
    async with DiscogsClient(config) as client:
        results = await client.search_release(
            artist=metadata["artist"], title=metadata["title"], format=format
        )
    return results


async def main():
    discogs_token = get_token()
    filepath = "The Groove Regatta - Hey Brother (Groove Mix.mp3"

    # Search all formats
    results = await search_discogs_from_file(filepath, discogs_token)
    print("\nAll releases:")
    for r in results[:5]:
        print(f"- {r.get('title')} ({r.get('year', 'N/A')})")

    # Search vinyl only
    vinyl_results = await search_discogs_from_file(filepath, discogs_token, format="Vinyl")
    print("\nVinyl releases:")
    for r in vinyl_results[:5]:
        print(f"- {r.get('title')} ({r.get('year', 'N/A')})")


if __name__ == "__main__":
    asyncio.run(main())
