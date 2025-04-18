# UI Themes Module Documentation

## Overview
The themes module provides styling and theming capabilities for the Selecta application. It ensures a consistent visual appearance across all UI components and provides theme switching functionality.

## Key Components
- **ThemeManager**: Static class that handles theme application and switching
- **Theme**: Enum that defines available themes (LIGHT, DARK)
- **Style definitions**: Constants and color schemes for UI elements

## File Structure
- `__init__.py`: Module initialization
- `theme_manager.py`: Core theme management functionality
- `style.py`: Style constants, colors, and theme-specific values

## Dependencies
- Internal: None
- External: PyQt6 for styling application

## Common Tasks
- **Changing application colors**: Modify color definitions in style.py
- **Adding a new theme**: Add a new enum value to Theme and update style definitions
- **Styling specific components**: Update or add style methods in ThemeManager
- **Making UI elements theme-aware**: Ensure components use theme constants instead of hardcoded values

## Implementation Notes
- Themes are applied using Qt stylesheets (CSS-like syntax)
- The ThemeManager provides both global application styling and component-specific styling
- Color constants should be used instead of hardcoding colors directly in components
- The dark theme is the default and primary theme

## Style Guidelines
- **Consistency**: All similar UI elements should have consistent appearance
- **Color usage**: Stick to the theme's color palette
- **Contrast**: Ensure enough contrast for text readability
- **Component spacing**: Use consistent padding and margins

## Change History
- Initial implementation with dark theme
- Added light theme option
- Improved styling for playlist components
- Added specialized styling for platform-specific elements
