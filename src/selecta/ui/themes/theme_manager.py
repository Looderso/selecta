# src/selecta/ui/themes/theme_manager.py
from enum import Enum

import qdarktheme
from PyQt6.QtWidgets import QApplication


class Theme(Enum):
    """Enum for the theme."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeManager:
    """Manages application theming."""

    @staticmethod
    def apply_theme(app: QApplication, theme: Theme = Theme.SYSTEM):
        """Apply the selected theme to the application."""
        if theme == Theme.LIGHT:
            app.setStyleSheet(qdarktheme.load_stylesheet("light"))
        elif theme == Theme.DARK:
            app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        else:
            # Auto-detect system theme
            app.setStyleSheet(qdarktheme.load_stylesheet())

        # Configure global app style here (e.g., button rounding)
        app.setStyle("Fusion")  # Base style
