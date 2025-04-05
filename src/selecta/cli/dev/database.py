"""Development database commands for Selecta CLI."""

import random
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click
from loguru import logger
from mutagen.id3 import ID3
from mutagen.id3._frames import TALB, TCON, TDRC, TIT2, TPE1, TRCK

from selecta.core.data.database import get_engine, get_session, init_database
from selecta.core.data.models.db import (
    Album,
    Genre,
    Playlist,
    PlaylistTrack,
    Track,
    TrackPlatformInfo,
    Vinyl,
)
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.data.repositories.track_repository import TrackRepository
from selecta.core.data.repositories.vinyl_repository import VinylRepository
from selecta.core.utils.path_helper import get_project_root
from selecta.core.utils.type_helpers import column_to_bool, column_to_int

# Sample data for development
ARTISTS = [
    "Daft Punk",
    "Disclosure",
    "Bonobo",
    "Caribou",
    "Jamie xx",
    "Four Tet",
    "Bicep",
    "Peggy Gou",
    "Floating Points",
    "Jon Hopkins",
]

TITLES = [
    "Around the World",
    "Deep Inside",
    "Ketto",
    "Can't Do Without You",
    "Gosh",
    "Baby",
    "Glue",
    "Starry Night",
    "LesAlpx",
    "Emerald Rush",
]

ALBUMS = [
    "Homework",
    "Settle",
    "Black Sands",
    "Our Love",
    "In Colour",
    "There Is Love in You",
    "Bicep",
    "Moment",
    "Crush",
    "Singularity",
]

GENRES = [
    "House",
    "Techno",
    "Ambient",
    "Disco",
    "Deep House",
    "Electronica",
    "UK Garage",
    "Downtempo",
    "Breakbeat",
    "Minimal",
]

LABELS = [
    "Ninja Tune",
    "Warp Records",
    "XL Recordings",
    "Ghostly International",
    "Innervisions",
    "Anjunadeep",
    "Kompakt",
    "Hyperdub",
    "R&S Records",
    "PIAS",
]

PLAYLIST_NAMES = [
    "Morning Chill",
    "Workout Mix",
    "Late Night Vibes",
    "Focus Flow",
    "Party Starters",
    "Sunday Selection",
    "Vinyl Classics",
    "New Discoveries",
    "Summer Jams",
    "Deep Cuts",
]

VINYL_CONDITIONS = [
    "Mint (M)",
    "Near Mint (NM or M-)",
    "Very Good Plus (VG+)",
    "Very Good (VG)",
    "Good Plus (G+)",
    "Good (G)",
]


@click.group(name="dev")
def dev_database():
    """Development database commands for Selecta."""
    pass


@dev_database.command(name="add-quality-column")
@click.option(
    "--path",
    type=click.Path(),
    help="Custom database path (default: app data directory)",
)
def add_quality_column(path: str | None) -> None:
    """Add quality column to tracks table.

    Args:
        path: Optional custom database path
    """
    from pathlib import Path

    from sqlalchemy import text

    from selecta.core.data.database import get_engine, get_session
    from selecta.core.utils.path_helper import get_app_data_path

    db_path = Path(path) if path else get_app_data_path() / "selecta.db"

    if not db_path.exists():
        click.echo(f"No database found at {db_path}")
        return

    click.echo(f"Adding quality column to tracks table in {db_path}")

    try:
        # Get engine and session
        engine = get_engine(db_path)
        session = get_session(engine)

        # Check if quality column exists
        try:
            session.execute(text("SELECT quality FROM tracks LIMIT 1"))
            click.echo("Quality column already exists in tracks table")
            return
        except Exception:
            # Column doesn't exist, continue with adding it
            pass

        # Add quality column with default of -1 (NOT_RATED)
        session.execute(text("ALTER TABLE tracks ADD COLUMN quality INTEGER NOT NULL DEFAULT -1"))

        # Create index for faster filtering
        session.execute(text("CREATE INDEX ix_tracks_quality ON tracks (quality)"))

        # Commit changes
        session.commit()
        click.echo("Quality column added successfully!")

    except Exception as e:
        logger.exception(f"Error adding quality column: {e}")
        click.echo(f"Error adding quality column: {e}")


@dev_database.command(name="init", help="Initialize a database with sample data")
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path for the database (default: application data directory)",
)
@click.option(
    "--audio-path",
    type=click.Path(),
    default="./sample-audio/",
    help="Path for sample audio files",
)
@click.option(
    "--num-files",
    type=int,
    default=10,
    help="Number of sample audio files to create",
)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force initialization even if database already exists",
)
def init_dev_database(
    db_path: str | None,
    audio_path: str | None,
    num_files: int,
    force: bool,
) -> None:
    """Initialize a development database with sample data.

    Args:
        db_path: Path to the database file
        audio_path: Path for sample audio files
        num_files: Number of sample audio files to create
        force: Whether to force initialization if database already exists
    """
    # Use the application data directory if db_path is not specified
    from selecta.core.data.database import get_db_path

    if db_path is None:
        db_path_pathlib = get_db_path()
    else:
        db_path_pathlib = Path(db_path)

    # Check if database already exists
    if (
        db_path_pathlib.exists()
        and not force
        and not click.confirm(
            f"Database already exists at {db_path_pathlib}. Overwrite?", default=False
        )
    ):
        click.echo("Database initialization cancelled.")
        return

    # Determine audio path
    if audio_path is None:
        audio_path_pathlib = get_project_root() / "audio_files"
    else:
        audio_path_pathlib = Path(audio_path)

    click.echo(f"Initializing development database at {db_path_pathlib}")
    click.echo(f"Creating sample audio files at {audio_path_pathlib}")

    # Create audio folder and sample files
    audio_files = create_sample_audio_files(audio_path_pathlib, num_files)

    # Initialize and seed the database
    seed_database(db_path_pathlib, audio_files)

    click.secho(f"Development database initialized successfully at {db_path_pathlib}", fg="green")
    click.secho(
        f"Created {len(audio_files)} sample audio files at {audio_path_pathlib}", fg="green"
    )
    click.echo("Run 'selecta database dev verify' to check the database contents")


@dev_database.command(name="verify", help="Verify database contents")
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database (default: application data directory)",
)
@click.option(
    "--audio-path",
    type=click.Path(exists=True),
    default="./sample-audio/",
    help="Path to sample audio files",
)
def verify_dev_database(db_path: str | None, audio_path: str | None) -> None:
    """Verify the contents of a database.

    Args:
        db_path: Path to the database file
        audio_path: Path to the audio files
    """
    # Use the application data directory if db_path is not specified
    from selecta.core.data.database import get_db_path

    if db_path is None:
        db_path_pathlib = get_db_path()
    else:
        db_path_pathlib = Path(db_path)

    # Determine audio path
    if audio_path is None:
        audio_path_pathlib = get_project_root() / "audio_files"
    else:
        audio_path_pathlib = Path(audio_path)

    click.echo(f"Verifying development database at {db_path_pathlib}")

    # Verify the database
    verify_database(db_path_pathlib)

    # Verify audio files
    verify_audio_files(audio_path_pathlib)

    click.secho("Development database verification completed", fg="green")


@dev_database.command(name="clean", help="Remove database and sample files")
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    default=None,
    help="Path to the database (default: application data directory)",
)
@click.option(
    "--audio-path",
    type=click.Path(exists=True),
    default="./sample-audio/",
    help="Path to sample audio files",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clean_dev_database(db_path: str | None, audio_path: str | None, yes: bool) -> None:
    """Remove database and sample files.

    Args:
        db_path: Path to the database file
        audio_path: Path to the audio files
        yes: Skip confirmation prompt
    """
    # Use the application data directory if db_path is not specified
    from selecta.core.data.database import get_db_path

    if db_path is None:
        db_path_pathlib = get_db_path()
    else:
        db_path_pathlib = Path(db_path)

    # Determine audio path
    if audio_path is None:
        audio_path_pathlib = get_project_root() / "audio_files"
    else:
        audio_path_pathlib = Path(audio_path)

    if not yes and not click.confirm(
        f"Are you sure you want to remove the database at {db_path} and audio "
        f"files at {audio_path}?",
        default=False,
    ):
        click.echo("Clean operation cancelled.")
        return

    # Remove database file
    if db_path_pathlib.exists():
        click.echo(f"Removing database file: {db_path_pathlib}")
        db_path_pathlib.unlink()

    # Remove audio folder
    if audio_path_pathlib.exists():
        click.echo(f"Removing audio folder: {audio_path_pathlib}")
        shutil.rmtree(audio_path_pathlib)

    click.secho("Development files cleaned up successfully", fg="green")


def create_sample_audio_files(audio_path: Path, num_files: int) -> list[tuple[Path, dict]]:
    """Create sample audio files with metadata.

    Args:
        audio_path: Path to the audio folder
        num_files: Number of files to create

    Returns:
        List of tuples with (file_path, metadata_dict)
    """
    # Create the directory if it doesn't exist
    audio_path.mkdir(parents=True, exist_ok=True)

    audio_files = []
    years = list(range(2010, 2024))

    for _ in range(num_files):
        artist = random.choice(ARTISTS)
        title = random.choice(TITLES)
        album = random.choice(ALBUMS)
        genre = random.choice(GENRES)
        year = random.choice(years)
        track_number = random.randint(1, 12)

        # Create unique filename using artist and title
        safe_artist = artist.replace(" ", "_").lower()
        safe_title = title.replace(" ", "_").lower()
        filename = f"{safe_artist}-{safe_title}.mp3"
        file_path = audio_path / filename

        # Create and populate the file
        create_empty_mp3(file_path)
        add_metadata_to_mp3(file_path, title, artist, album, genre, year, track_number)

        # Store metadata for later database insertion
        metadata = {
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
            "year": year,
            "track_number": track_number,
            "file_path": str(file_path),
        }

        audio_files.append((file_path, metadata))
        logger.debug(f"Created sample audio file: {filename}")

    return audio_files


def create_empty_mp3(path: Path) -> Path:
    """Create an empty MP3 file with minimal size.

    Args:
        path: Path where the MP3 file should be created

    Returns:
        Path to the created MP3 file
    """
    # Create a minimal valid MP3 file (essentially empty)
    with open(path, "wb") as f:
        # ID3v2 header (10 bytes) + minimal valid MP3 frame
        f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00")
        # MP3 frame header (MPEG-1 Layer 3, 128kbps, 44100Hz)
        f.write(b"\xff\xfb\x90\x44\x00\x00\x00\x00")

    return path


def add_metadata_to_mp3(
    file_path: Path,
    title: str,
    artist: str,
    album: str,
    genre: str,
    year: int,
    track_number: int = 1,
) -> None:
    """Add metadata to an MP3 file.

    Args:
        file_path: Path to the MP3 file
        title: Track title
        artist: Artist name
        album: Album name
        genre: Genre name
        year: Release year
        track_number: Track number
    """
    try:
        # Create ID3 tag if it doesn't exist
        try:
            tags = ID3(file_path)
        except:
            tags = ID3()

        # Add metadata
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.add(TCON(encoding=3, text=genre))
        tags.add(TDRC(encoding=3, text=str(year)))
        tags.add(TRCK(encoding=3, text=str(track_number)))

        # Save to file
        tags.save(file_path)

        logger.debug(f"Added metadata to {file_path}")
    except Exception as e:
        logger.error(f"Error adding metadata to {file_path}: {e}")


def seed_database(db_path: Path, audio_files: list[tuple[Path, dict]]) -> None:
    """Seed the database with sample data.

    Args:
        db_path: Path to the database file
        audio_files: List of tuples with (file_path, metadata_dict)
    """
    # Initialize database
    if db_path.exists():
        db_path.unlink()

    init_database(db_path)

    # Create engine and session
    engine = get_engine(db_path)
    session = get_session(engine)

    try:
        # Seed data in a specific order to maintain relationships
        _seed_genres(session)
        _seed_tracks_and_albums(session, audio_files)
        _seed_playlists(session)
        _seed_vinyl_records(session)
        _seed_platform_credentials(session)
        _seed_user_settings(session)

        logger.success("Database seeded successfully!")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def _seed_genres(session) -> list[Genre]:
    """Seed genre data.

    Args:
        session: Database session

    Returns:
        List of created genre objects
    """
    logger.info("Seeding genres...")
    genres = []

    for genre_name in GENRES:
        genre = Genre(name=genre_name, source="user")
        session.add(genre)
        genres.append(genre)

    session.commit()
    logger.info(f"Created {len(genres)} genres")
    return genres


def _seed_tracks_and_albums(
    session, audio_files: list[tuple[Path, dict]]
) -> tuple[list[Track], list[Album]]:
    """Seed tracks and albums from audio files.

    Args:
        session: Database session
        audio_files: List of tuples with (file_path, metadata_dict)

    Returns:
        Tuple of (tracks list, albums list)
    """
    logger.info("Seeding tracks and albums...")

    # Get genres from the database
    genres = session.query(Genre).all()

    # Create a track repository
    track_repo = TrackRepository(session)

    tracks = []
    albums = {}  # Use dict to avoid duplicates

    for _, metadata in audio_files:
        # Check if album already exists
        album_name = metadata["album"]
        artist_name = metadata["artist"]
        album_key = f"{album_name}|{artist_name}"

        if album_key not in albums:
            # Create album
            album = Album(
                title=album_name,
                artist=artist_name,
                release_year=metadata["year"],
                label=random.choice(LABELS),
                catalog_number=f"CAT-{random.randint(1000, 9999)}",
            )
            session.add(album)
            session.flush()  # To get the ID
            albums[album_key] = album
        else:
            album = albums[album_key]

        # Create track
        track = Track(
            title=metadata["title"],
            artist=metadata["artist"],
            album_id=album.id,
            duration_ms=random.randint(120000, 420000),  # 2-7 minutes
            local_path=metadata["file_path"],
        )
        session.add(track)
        session.flush()  # To get the ID

        # Add random genre to track
        track_genre = random.choice(genres)
        track.genres.append(track_genre)

        # Add platform info
        # 50% chance to have Spotify
        if random.random() > 0.5:
            spotify_id = f"spotify{random.randint(10000000, 99999999)}"

            # Create platform info directly to ensure last_synced and needs_update are set
            spotify_info = TrackPlatformInfo(
                track_id=column_to_int(track.id),
                platform="spotify",
                platform_id=spotify_id,
                uri=f"spotify:track:{spotify_id}",
                platform_data=f'{{"popularity": {random.randint(20, 80)}, "explicit": false,'
                f' "preview_url": "https://spotify-preview/{spotify_id}"}}',
                last_synced=datetime.now(UTC),
                needs_update=False,
            )
            session.add(spotify_info)
            session.flush()

            # Add Spotify audio features
            _add_spotify_audio_features(track_repo, column_to_int(track.id))

        # 70% chance to have Rekordbox
        if random.random() > 0.3:
            rekordbox_id = random.randint(10000, 99999)

            # Create platform info directly to ensure last_synced and needs_update are set
            rekordbox_info = TrackPlatformInfo(
                track_id=column_to_int(track.id),
                platform="rekordbox",
                platform_id=str(rekordbox_id),
                uri=None,
                platform_data=f'{{"bpm": {round(random.uniform(80, 140), 1)}, "key": "{random.choice(["1A", "2A", "3A", "4A", "5A", "6A", "7A", "8A", "9A", "10A", "11A", "12A"])}", "rating": {random.randint(1, 5)}}}',  # noqa: E501
                last_synced=datetime.now(UTC),
                needs_update=False,
            )
            session.add(rekordbox_info)
            session.flush()

        tracks.append(track)

    session.commit()
    logger.info(f"Created {len(tracks)} tracks and {len(albums)} albums")
    return tracks, list(albums.values())


def _add_spotify_audio_features(track_repo: TrackRepository, track_id: int) -> None:
    """Add Spotify audio features to a track.

    Args:
        track_repo: Track repository
        track_id: Track ID
    """
    # Add common audio features
    features = {
        "danceability": round(random.uniform(0.2, 0.9), 2),
        "energy": round(random.uniform(0.2, 0.9), 2),
        "valence": round(random.uniform(0.1, 0.9), 2),
        "tempo": round(random.uniform(80, 140), 2),
        "acousticness": round(random.uniform(0.01, 0.8), 2),
        "instrumentalness": round(random.uniform(0.01, 0.8), 2),
    }

    for name, value in features.items():
        track_repo.add_attribute(track_id, name, value, "spotify")


def _seed_playlists(session) -> list[Playlist]:
    """Seed playlist data without using parent-child relationships directly.

    Args:
        session: Database session

    Returns:
        List of created playlist objects
    """
    logger.info("Seeding playlists...")

    # Get all tracks
    tracks = session.query(Track).all()

    playlists = []

    # Create folder playlists first
    dj_folder = Playlist(
        name="DJ Sets",
        description="Playlists organized for DJ sets",
        is_local=True,
        is_folder=True,
    )
    session.add(dj_folder)

    mood_folder = Playlist(
        name="Moods",
        description="Playlists organized by mood",
        is_local=True,
        is_folder=True,
    )
    session.add(dj_folder)
    session.add(mood_folder)

    # Flush to get IDs
    session.flush()
    dj_folder_id = column_to_int(dj_folder.id)
    mood_folder_id = column_to_int(mood_folder.id)

    # Add folders to playlists list
    playlists.append(dj_folder)
    playlists.append(mood_folder)

    # Create regular playlists
    for _, name in enumerate(PLAYLIST_NAMES[:5]):
        # First half in DJ folder
        playlist = Playlist(
            name=name,
            description=f"A collection of {name.lower()} tracks",
            is_local=True,
            is_folder=False,
            parent_id=dj_folder_id,
        )
        session.add(playlist)
        session.flush()

        # Add tracks after flushing to get playlist ID
        playlist_id = column_to_int(playlist.id)

        # Add 4-8 random tracks to each playlist
        num_tracks = random.randint(4, min(8, len(tracks)))
        playlist_tracks = random.sample(tracks, num_tracks)

        # Create playlist-track associations directly
        for position, track in enumerate(playlist_tracks):
            track_id = column_to_int(track.id)
            playlist_track = PlaylistTrack(
                playlist_id=playlist_id,
                track_id=track_id,
                position=position,
                added_at=datetime.now(UTC),
            )
            session.add(playlist_track)

        playlists.append(playlist)

    for _, name in enumerate(PLAYLIST_NAMES[5:]):
        # Second half in moods folder
        playlist = Playlist(
            name=name,
            description=f"A collection of {name.lower()} tracks",
            is_local=True,
            is_folder=False,
            parent_id=mood_folder_id,
        )
        session.add(playlist)
        session.flush()

        # Add tracks after flushing to get playlist ID
        playlist_id = column_to_int(playlist.id)

        # Add 4-8 random tracks to each playlist
        num_tracks = random.randint(4, min(8, len(tracks)))
        playlist_tracks = random.sample(tracks, num_tracks)

        # Create playlist-track associations directly
        for position, track in enumerate(playlist_tracks):
            track_id = column_to_int(track.id)
            playlist_track = PlaylistTrack(
                playlist_id=playlist_id,
                track_id=track_id,
                position=position,
                added_at=datetime.now(UTC),
            )
            session.add(playlist_track)

        playlists.append(playlist)

    # Create a few platform-specific playlists
    spotify_playlist = Playlist(
        name="Discover Weekly Archive",
        description="Archive of interesting tracks from Discover Weekly",
        is_local=False,
        source_platform="spotify",
        platform_id=f"spotify_playlist_{random.randint(1000000, 9999999)}",
    )
    session.add(spotify_playlist)
    session.flush()

    spotify_playlist_id = column_to_int(spotify_playlist.id)

    # Add 5-6 random tracks to the Spotify playlist
    spotify_tracks = random.sample(tracks, min(random.randint(5, 6), len(tracks)))
    for position, track in enumerate(spotify_tracks):
        track_id = column_to_int(track.id)
        playlist_track = PlaylistTrack(
            playlist_id=spotify_playlist_id,
            track_id=track_id,
            position=position,
            added_at=datetime.now(UTC),
        )
        session.add(playlist_track)

    playlists.append(spotify_playlist)

    # A Rekordbox playlist
    rekordbox_playlist = Playlist(
        name="Recent Mixes",
        description="Tracks used in recent DJ mixes",
        is_local=False,
        source_platform="rekordbox",
        platform_id=f"rekordbox_playlist_{random.randint(1000, 9999)}",
    )
    session.add(rekordbox_playlist)
    session.flush()

    rekordbox_playlist_id = column_to_int(rekordbox_playlist.id)

    # Add 4-7 random tracks to the Rekordbox playlist
    rekordbox_tracks = random.sample(tracks, min(random.randint(4, 7), len(tracks)))
    for position, track in enumerate(rekordbox_tracks):
        track_id = column_to_int(track.id)
        playlist_track = PlaylistTrack(
            playlist_id=rekordbox_playlist_id,
            track_id=track_id,
            position=position,
            added_at=datetime.now(UTC),
        )
        session.add(playlist_track)

    playlists.append(rekordbox_playlist)

    # Commit everything at once
    session.commit()
    logger.info(f"Created {len(playlists)} playlists (including 2 folders)")
    return playlists


def _seed_vinyl_records(session) -> list[Vinyl]:
    """Seed vinyl record data.

    Args:
        session: Database session

    Returns:
        List of created vinyl objects
    """
    logger.info("Seeding vinyl records...")

    # Get existing albums to associate some with vinyl
    albums = session.query(Album).all()
    vinyl_repo = VinylRepository(session)

    vinyl_records = []

    # Associate vinyls with some existing albums (3 owned records)
    for i in range(min(3, len(albums))):
        album = albums[i]

        vinyl = vinyl_repo.create(
            {
                "discogs_id": random.randint(100000, 999999),
                "discogs_release_id": random.randint(1000000, 9999999),
                "is_owned": True,
                "is_wanted": False,
                "media_condition": random.choice(VINYL_CONDITIONS),
                "sleeve_condition": random.choice(VINYL_CONDITIONS),
                "purchase_date": datetime.now(UTC) - timedelta(days=random.randint(1, 730)),
                "purchase_price": round(random.uniform(10, 50), 2),
                "purchase_currency": "USD",
                "notes": "This is a great pressing with excellent sound quality.",
            },
            None,  # No need to create a new album, it's already associated
        )

        # Associate with the existing album
        vinyl.album_id = album.id
        session.add(vinyl)

        vinyl_records.append(vinyl)

    # Create 2 wanted vinyls
    for _ in range(2):
        vinyl = vinyl_repo.create(
            {
                "discogs_id": random.randint(100000, 999999),
                "discogs_release_id": random.randint(1000000, 9999999),
                "is_owned": False,
                "is_wanted": True,
            },
            {
                "title": random.choice(ALBUMS),
                "artist": random.choice(ARTISTS),
                "release_year": random.randint(1970, 2023),
                "label": random.choice(LABELS),
                "catalog_number": f"DISC-{random.randint(1000, 9999)}",
            },
        )
        vinyl_records.append(vinyl)

    session.commit()
    logger.info(f"Created {len(vinyl_records)} vinyl records")
    return vinyl_records


def _seed_platform_credentials(session) -> None:
    """Seed dummy platform credentials.

    Args:
        session: Database session
    """
    logger.info("Seeding platform credentials...")

    settings_repo = SettingsRepository(session)

    # Add Spotify credentials
    settings_repo.set_credentials(
        "spotify",
        {
            "client_id": "dummy_spotify_client_id",
            "client_secret": "dummy_spotify_client_secret",
            "access_token": "dummy_spotify_access_token",
            "refresh_token": "dummy_spotify_refresh_token",
            "token_expiry": datetime.now(UTC) + timedelta(hours=1),
        },
    )

    # Add Discogs credentials
    settings_repo.set_credentials(
        "discogs",
        {
            "client_id": "dummy_discogs_consumer_key",
            "client_secret": "dummy_discogs_consumer_secret",
            "access_token": "dummy_discogs_access_token",
            "refresh_token": "dummy_discogs_oauth_token_secret",
        },
    )

    # Add Rekordbox credentials
    settings_repo.set_credentials(
        "rekordbox",
        {
            "client_id": "rekordbox",
            "client_secret": "402fd3318daad642cc53f05f5e5d88d9e9ef9405",  # Dummy key
        },
    )

    logger.info("Created dummy platform credentials")


def _seed_user_settings(session) -> None:
    """Seed user settings.

    Args:
        session: Database session
    """
    logger.info("Seeding user settings...")

    settings_repo = SettingsRepository(session)

    # Add some basic settings
    settings_repo.set_setting("dark_mode", True, "boolean", "Use dark mode theme")
    settings_repo.set_setting(
        "sync_interval_minutes", 60, "integer", "Interval for automatic synchronization"
    )
    settings_repo.set_setting(
        "auto_sync_enabled", True, "boolean", "Whether automatic synchronization is enabled"
    )
    settings_repo.set_setting(
        "default_import_folder",
        str(Path.home() / "Music"),
        "string",
        "Default folder for importing music",
    )
    settings_repo.set_setting(
        "last_sync_time", datetime.now(UTC).isoformat(), "string", "Last time data was synchronized"
    )

    # Add some playlist display preferences
    display_prefs = {
        "show_duration": True,
        "show_bpm": True,
        "show_key": True,
        "sort_by": "artist",
        "sort_direction": "asc",
    }
    settings_repo.set_setting(
        "playlist_display", display_prefs, "json", "Playlist display preferences"
    )

    logger.info("Created user settings")


def verify_database(db_path: Path) -> None:
    """Verify database contents and display summary.

    Args:
        db_path: Path to the database file
    """
    # Create engine and session
    engine = get_engine(db_path)
    session = get_session(engine)

    try:
        # Check tracks and albums
        tracks = session.query(Track).all()
        click.echo(f"Found {len(tracks)} tracks in the database")

        albums = session.query(Album).all()
        click.echo(f"Found {len(albums)} albums in the database")

        # Check playlists
        playlists = session.query(Playlist).all()
        folders = [p for p in playlists if column_to_bool(p.is_folder)]
        regular_playlists = [p for p in playlists if not column_to_bool(p.is_folder)]

        click.echo(
            f"Found {len(playlists)} playlists"
            f" ({len(folders)} folders, {len(regular_playlists)} regular)"
        )

        # Check vinyl records
        vinyl_records = session.query(Vinyl).all()
        owned = [v for v in vinyl_records if column_to_bool(v.is_owned)]
        wanted = [v for v in vinyl_records if column_to_bool(v.is_wanted)]

        click.echo(
            f"Found {len(vinyl_records)} vinyl records ({len(owned)} owned, {len(wanted)} wanted)"
        )

        # Check platform integration
        spotify_tracks = (
            session.query(TrackPlatformInfo).filter(TrackPlatformInfo.platform == "spotify").count()
        )
        rekordbox_tracks = (
            session.query(TrackPlatformInfo)
            .filter(TrackPlatformInfo.platform == "rekordbox")
            .count()
        )

        click.echo(
            f"Platform integration: {spotify_tracks} "
            f"Spotify tracks, {rekordbox_tracks} Rekordbox tracks"
        )

        # Check settings - FIX: use proper import and query
        from selecta.core.data.models.db import UserSettings

        settings_count = session.query(UserSettings).count()
        click.echo(f"Found {settings_count} user settings")

        # If the database has data in all major tables, consider it valid
        if (
            tracks
            and albums
            and playlists
            and vinyl_records
            and spotify_tracks
            and rekordbox_tracks
        ):
            click.secho(
                "Database verification successful: All major tables contain data", fg="green"
            )
        else:
            click.secho("Database verification failed: One or more tables are empty", fg="red")
    except Exception as e:
        click.secho(f"Error verifying database: {e}", fg="red")
    finally:
        session.close()


def verify_audio_files(audio_path: Path) -> None:
    """Verify audio files.

    Args:
        audio_path: Path to the audio files
    """
    if not audio_path.exists():
        click.secho(f"Audio folder not found at {audio_path}", fg="red")
        return

    audio_files = list(audio_path.glob("*.mp3"))
    click.echo(f"Found {len(audio_files)} audio files in {audio_path}")

    if audio_files:
        click.echo("Checking metadata in sample files:")
        for file in audio_files[:3]:  # Check just a few files
            try:
                tags = ID3(file)
                artist = tags.get("TPE1")
                title = tags.get("TIT2")
                album = tags.get("TALB")

                artist_text = artist.text[0] if artist and artist.text else "Unknown"
                title_text = title.text[0] if title and title.text else "Unknown"
                album_text = album.text[0] if album and album.text else "Unknown"

                click.echo(f"  - {file.name}: {artist_text} - {title_text} ({album_text})")
            except Exception as e:
                click.echo(f"  - {file.name}: Error reading metadata: {e}")

        if len(audio_files) > 3:
            click.echo(f"  ... and {len(audio_files) - 3} more files")

        click.secho("Audio files verification completed successfully", fg="green")
    else:
        click.secho("No audio files found in the directory", fg="yellow")
