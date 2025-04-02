# Client Integration Notes for Database Refactor

This document provides guidance on integrating the database refactored components into the client UI.

## Overview of Changes

The database refactor includes several key changes:

1. Enhanced platform metadata storage with JSON fields
2. Tracking of when metadata was last synced and if it needs updating
3. Storage of tags and genres
4. Storage of images (album covers) in the database with multiple sizes

## Database Image Integration

The new database schema now supports storing images directly in the database. This provides several benefits:

- Images are available offline
- Consistent image references that don't rely on external URLs
- Support for different image sizes (thumbnail, small, medium, large)
- Fallback from track to album images

### DatabaseImageLoader

A new `DatabaseImageLoader` class was created in `/src/selecta/ui/components/image_loader.py`. This component:

- Asynchronously loads images from the database
- Supports loading by track ID or album ID
- Automatically selects appropriate image sizes
- Maintains a cache of loaded images
- Emits signals when images are loaded

### Implementation Steps

1. **TrackItem Base Class**
   - Added `album_id` and `has_image` fields to track items
   - Updated display_data to include image information

2. **Track Item UI Components**
   - Updated to support loading images from database
   - Added fallbacks to URL-based loading when DB images aren't available
   - Support different image sizes based on context

3. **Tracks Table Model**
   - Updated to expose image metadata through UserRole
   - Added methods to get image information for tracks

4. **Track Image Delegate**
   - Created new delegate for rendering track images in tables
   - Supports loading from database and displaying with proper styling

5. **Track Details Panel**
   - Updated to display album art from the database
   - Shows larger images for the selected track
   - Supports fallbacks from track to album images

### Usage Guidelines

#### Loading Images in Components

```python
# Initialize the database image loader
self._db_image_loader = DatabaseImageLoader()

# Connect to signals
self._db_image_loader.track_image_loaded.connect(self._on_track_image_loaded)
self._db_image_loader.album_image_loaded.connect(self._on_album_image_loaded)

# Load track image
self._db_image_loader.load_track_image(track_id, ImageSize.THUMBNAIL)

# Load album image
self._db_image_loader.load_album_image(album_id, ImageSize.MEDIUM)
```

#### Image Signal Handling

```python
def _on_track_image_loaded(self, track_id: int, pixmap: QPixmap):
    """Handle loaded image from database for a track."""
    if track_id == self._current_track_id:
        self.image_label.setPixmap(pixmap)

def _on_album_image_loaded(self, album_id: int, pixmap: QPixmap):
    """Handle loaded image from database for an album."""
    if album_id == self._current_album_id:
        self.image_label.setPixmap(pixmap)
```

#### Setting Up Track Items with Images

When creating track items, make sure to include the image-related fields:

```python
track_item = SpotifyTrackItem(
    track_id=track_id,
    title=title,
    artist=artist,
    album=album,
    duration_ms=duration_ms,
    album_id=album_id,
    has_image=True  # Set to True if the track has an image in the database
)
```

## Platform Metadata Integration

The enhanced platform metadata storage allows for:

1. Storing structured data per platform
2. Tracking when metadata was last updated
3. Marking entries for update

### Using Platform Metadata

```python
# Getting metadata for a specific platform
metadata = track_repository.get_platform_metadata(track_id, "spotify")

# Updating platform metadata
track_repository.update_platform_metadata(
    track_id,
    "spotify",
    {"popularity": 75, "added_at": "2023-04-01"}
)

# Marking a track for update
track_repository.mark_for_update(track_id, "spotify")

# Checking if a track needs updating
if track_repository.needs_update(track_id, "spotify"):
    # Update logic here
```

## Next Steps

The following components have been updated:

1. ✅ Update track items to use the DatabaseImageLoader
2. ✅ Create TrackImageDelegate for displaying images in tables (not used since you don't want images in tables)
3. ✅ Update TrackDetailsPanel to show database images
4. ✅ The search panels already implement image downloading and storage properly

The following components still need to be updated:

1. Add support for user-defined tags UI
2. Implement UI for viewing and managing image sizes (optional)

## Summary of Implementation

1. **Database Structure**
   - Images are stored as binary BLOB data in the database
   - Multiple sizes are stored for each image (thumbnail, small, medium, large)
   - Images can be associated with either tracks or albums
   - JSON metadata includes source platform and original URL

2. **Image Loading**
   - Images are loaded asynchronously from the database
   - A caching system prevents repeated database access
   - Fallback mechanism uses album images when track images aren't available

3. **UI Integration**
   - The track details panel displays images for the selected track
   - Search panels download and store images when adding/syncing tracks
   - Image loading is handled in background threads to keep UI responsive
