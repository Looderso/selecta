# src/selecta/gui/widgets/platform_indicators.py
"""Platform authentication status indicators."""

import traceback
from pathlib import Path

from kivy.properties import ColorProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from loguru import logger


class PlatformIndicator(MDCard):
    """Component to show platform authentication status."""

    platform_name = StringProperty("")
    status_color = ColorProperty((0.5, 0.5, 0.5, 1))  # Default gray
    icon_source = StringProperty("")

    def __init__(self, **kwargs):
        """Initialize the platform indicator."""
        try:
            super().__init__(**kwargs)
            self.orientation = "horizontal"
            self.size_hint_y = None
            self.height = "100dp"
            self.size_hint_x = 1
            self.md_bg_color = (0.2, 0.2, 0.2, 1)  # Dark card background
            self.radius = [10, 10, 10, 10]
            self.elevation = 2
            self.padding = [20, 20]
            self.spacing = 20

            # Set icon source based on platform name - create the icons directory if needed
            self._setup_icons()

            # Add icon image first (on the left)
            if self.icon_source and Path(self.icon_source).exists():
                self.icon = Image(
                    source=self.icon_source,
                    size_hint=(None, None),
                    size=("40dp", "40dp"),
                    pos_hint={"center_y": 0.5},
                )
                self.add_widget(self.icon)
            else:
                # Use a placeholder if icon not found
                logger.warning(f"Icon not found: {self.icon_source}")
                self.icon = MDLabel(
                    text=self.platform_name[0],
                    font_style="Title",
                    role="large",
                    size_hint=(None, None),
                    size=("40dp", "40dp"),
                    halign="center",
                    pos_hint={"center_y": 0.5},
                )
                self.add_widget(self.icon)

            # Create a boxlayout for the text content (center portion)
            content_layout = BoxLayout(orientation="vertical", size_hint_x=0.6, padding=[10, 0])

            # Platform name label
            self.name_label = MDLabel(
                text=self.platform_name,
                font_style="Title",
                role="medium",
                theme_text_color="Primary",
                size_hint_y=None,
                height="30dp",
            )
            content_layout.add_widget(self.name_label)

            # Status label - FIXED: use "Error" instead of "Secondary" theme color
            self.status_label = MDLabel(
                text="Not Authenticated",
                font_style="Body",
                role="medium",
                theme_text_color="Error",  # Valid theme_text_color in KivyMD 2.0
                size_hint_y=None,
                height="20dp",
            )
            content_layout.add_widget(self.status_label)

            # Add the content layout
            self.add_widget(content_layout)

            # Authentication button (on the right)
            self.auth_button = MDButton(
                style="filled",
                size_hint=(None, None),
                size=("130dp", "50dp"),
                pos_hint={"center_y": 0.5},
            )
            self.auth_button.add_widget(MDButtonText(text="Authenticate"))
            self.add_widget(self.auth_button)

        except Exception as e:
            logger.error(f"Error initializing PlatformIndicator: {e}")
            logger.error(traceback.format_exc())

    def _setup_icons(self):
        """Set up icon paths and create directories if needed."""
        # Create directories for icons if they don't exist
        from selecta.utils.path_helper import get_project_root

        icons_dir = get_project_root() / "resources" / "icons"
        icons_dir.mkdir(exist_ok=True, parents=True)

        # Map platform names to icon file names
        icon_files = {
            "Spotify": "spotify_logo.png",
            "Discogs": "discogs_logo.png",
            "Rekordbox": "rekordbox_logo.png",
        }

        if self.platform_name in icon_files:
            self.icon_source = str(icons_dir / icon_files[self.platform_name])

            # If icons don't exist, log a warning but don't crash
            if not Path(self.icon_source).exists():
                logger.warning(f"Icon file not found: {self.icon_source}")
                self.icon_source = ""

    def set_authenticated(self, is_authenticated: bool):
        """Set the authentication status.

        Args:
            is_authenticated: Whether the platform is authenticated
        """
        if is_authenticated:
            self.status_label.text = "Authenticated"
            # FIXED: Use "Primary" instead of "Success" theme color
            self.status_label.theme_text_color = "Primary"

            # Get the button text widget and update it
            for child in self.auth_button.children:
                if isinstance(child, MDButtonText):
                    child.text = "Disconnect"
                    break

            self.md_bg_color = (0.1, 0.25, 0.1, 1)  # Darker green background
        else:
            self.status_label.text = "Not Authenticated"
            self.status_label.theme_text_color = "Error"  # Valid theme_text_color

            # Get the button text widget and update it
            for child in self.auth_button.children:
                if isinstance(child, MDButtonText):
                    child.text = "Authenticate"
                    break

            self.md_bg_color = (0.25, 0.1, 0.1, 1)  # Darker red background
