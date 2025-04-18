# Resources Documentation

## Overview
This directory contains static resources used by the Selecta application, including icons, fonts, and other visual assets. These resources are crucial for the UI presentation and overall user experience.

## Resource Types

### Icons
- **Location**: `icons/`
- **Purpose**: Platform icons, control buttons, and UI elements
- **Resolution Variants**: Multiple sizes for different display densities (0.25x, 0.5x, 1x)
- **Formats**: PNG and SVG

#### Platform Icons
- `spotify.png`: Spotify platform icon
- `rekordbox.png`: Rekordbox platform icon
- `discogs.png`: Discogs platform icon
- `youtube.png`: YouTube platform icon
- `collection.png`: Local collection icon
- `wantlist.png`: Discogs wantlist icon
- `Doggo.png`: Application logo

#### Control Icons
- `play.png/svg`: Play button
- `pause.png/svg`: Pause button
- `stop.png/svg`: Stop button
- `volume.png/svg`: Volume control

### Animation Resources
- `spinner.gif`: Loading spinner animation

### Fonts
- **Location**: `fonts/`
- **Purpose**: Custom typography for the application

## Usage
These resources are accessed in the application through the `path_helper.py` utility:

```python
from selecta.core.utils.path_helper import get_resource_path

# Get path to a specific resource
icon_path = get_resource_path("icons/1x/spotify.png")

# Use in UI components
pixmap = QPixmap(str(icon_path))
```

## Resource Loading Strategy
Selecta implements a multi-tier resource loading strategy:

1. First checks project-level resources directory
2. Then checks package-embedded resources
3. Finally falls back to executable-relative resources

This ensures resources can be found regardless of how the application is deployed (development, installed package, or frozen executable).

## Resolution Handling
Icon resources are provided in multiple resolutions to support different display densities:

- **1x**: Base resolution (standard density displays)
- **0.5x**: Half resolution
- **0.25x**: Quarter resolution

The application automatically selects the appropriate resolution based on the display's DPI and scaling settings.

## File Naming Conventions
- Platform icons use the platform name: `platformname.png`
- Control icons use the control action: `action.png`
- Resolution variants use the format: `name@resolution.png`

## Adding New Resources
When adding new resources:

1. Provide all resolution variants where appropriate
2. Use consistent naming conventions
3. Prefer SVG for vector graphics when possible
4. Ensure proper licensing for all resources
5. Compress PNG files to optimize size

## Resource Management
Resources should be managed using the following guidelines:

1. Keep resources organized by type and purpose
2. Use appropriate formats (SVG for vector graphics, PNG for raster)
3. Optimize file sizes for performance
4. Maintain consistent styling across all resources
5. Ensure all resources work with both light and dark themes
