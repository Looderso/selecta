# Task

I want to update my database structure to make the platform metadata a bit more flexible.
Let's start with a use case:
I have a track in the local database with one or many platforms synched.
I would like to update the cover image using the discogs info (gui for updating metadata is not implemented yet, i am only interested in the local database structure)
I would have one ground truth (local database) which i would like to update using one of the platforms which can contain different entries for e.g. genre

My suggestion for required fields in the local track table are the following:

* Icon (not handled yet, how do we add images to the sqlite db?)
* Title
* Artist
* Album
* Genres (might be multiple, we should have a table for them)
* Year
* Bpm
* Tags (defined by the user, not the platforms)
* Platforms (discogs, spotify, rekordbox, we might want to add a "local" platform tag showing if the track is actually in the local_db_folder)
* Platform metadata (we should store all available metadata for each platform once we retrieve/synch it, in the future there could be a update method which checks if the metadata stored in our db matches the API response of the platform and lets us update it if necessary. this could avoid a lot of unnecessary requests)
* Vinyl info(in collection/wantlist)

## Overall Approach

1. **Review Current Database Schema**: First, understand the existing database models and relationships.

2. **Enhance Track Model**: Modify the Track model to better support multiple platforms and metadata types.

3. **Create Flexible Platform Metadata Storage**: Design a structure that can store arbitrary metadata from different platforms while maintaining relationships.

4. **Implement Genre and Tag Support**: Create proper tables for genres and tags, with many-to-many relationships.

5. **Add Vinyl Information**: Link tracks to vinyl records with collection/wishlist status.

6. **Consider Image Storage**: Discuss approaches for storing cover images in SQLite.

## Key Components

Based on the files you've shared, I see you already have a solid foundation with models like `Track`, `Album`, `TrackPlatformInfo`, etc. We'll enhance these models to better support your use case.

### For Platform Metadata

I recommend using a dedicated `TrackPlatformInfo` table that can store:

* Platform identifier (spotify, discogs, rekordbox)
* Platform-specific ID
* Platform-specific URI/URL
* JSON or serialized metadata for flexible storage

### For Genres and Tags

Use many-to-many relationships:

* Create a Genres table with name and source (spotify, discogs, user)
* Create a Tags table for user-defined tags
* Use association tables to link tracks to genres and tags

### For Vinyl Information

* Create a Vinyl model that can link to albums/tracks
* Include fields for collection status, wishlist status
* Store Discogs-specific fields (release ID, etc.)

### For Cover Images

If we are storing images in SQLite:

1. **File Storage Option**: Store image files on disk and keep paths in the database (efficient)
2. **BLOB Storage Option**: Store the actual image data in the database (portable but less efficient)

We wouldn't want to display the images of e.g. all tracks in the tracklist but mainly of the currently selected track. This means we don't need to fetch it for displaying the tracklist but only in certain scenarios. This would improve performance.

# JSON structure

outline of how the JSON structure could look for each platform:

### Spotify Metadata JSON

```json
{
  "popularity": 65,
  "explicit": false,
  "preview_url": "https://p.scdn.co/mp3-preview/...",
  "album_type": "album",
  "release_date": "2022-05-20",
  "total_tracks": 12,
  "available_markets": ["US", "GB", "DE", ...],
  "external_urls": {
    "spotify": "https://open.spotify.com/track/..."
  },
  "audio_features": {
    "danceability": 0.735,
    "energy": 0.578,
    "key": 5,
    "loudness": -11.84,
    "mode": 0,
    "speechiness": 0.0461,
    "acousticness": 0.514,
    "instrumentalness": 0.00234,
    "liveness": 0.159,
    "valence": 0.624,
    "tempo": 98.002,
    "time_signature": 4
  }
}
```

### Discogs Metadata JSON

```json
{
  "release_id": 12345678,
  "master_id": 1122334,
  "year": 1997,
  "format": ["Vinyl", "12\"", "33 ⅓ RPM"],
  "label": "Warp Records",
  "catno": "WARP92",
  "country": "UK",
  "notes": "Limited Edition",
  "media_condition": "Very Good Plus (VG+)",
  "sleeve_condition": "Very Good (VG)",
  "styles": ["IDM", "Experimental", "Ambient"],
  "credits": [
    {"role": "Producer", "name": "John Smith"},
    {"role": "Mastering", "name": "Jane Doe"}
  ],
  "images": [
    {"type": "primary", "uri": "https://img.discogs.com/..."},
    {"type": "secondary", "uri": "https://img.discogs.com/..."}
  ]
}
```

### Rekordbox Metadata JSON

```json
{
  "rating": 4,
  "bpm": 128.5,
  "key": "5A",
  "beat_grid": "1.025,2.050,3.075,...",
  "cue_points": [
    {"position": 16.5, "color": "red", "name": "Intro"},
    {"position": 32.7, "color": "blue", "name": "Break"}
  ],
  "play_count": 12,
  "comments": "Great transition track",
  "color_tag": "pink",
  "my_tag": ["Energy", "Peak Time"],
  "date_added": "2023-04-15",
  "last_played": "2023-09-30"
}
```

For the database implementation:

1. The `TrackPlatformInfo` table would store this JSON in a text column (SQLite doesn't have a native JSON type)
2. We'd have application code to parse and validate the JSON when retrieving/storing it
3. We could create type-safe helper functions for accessing specific properties
