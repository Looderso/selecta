"""Platform authentication status indicators."""

from kivy.lang import Builder
from kivy.properties import ColorProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from loguru import logger


class PlatformIndicator(BoxLayout):
    """Component to show platform authentication status."""

    platform_name = StringProperty("")
    status_color = ColorProperty((0.5, 0.5, 0.5, 1))  # Default gray
    icon_source = StringProperty("")

    def __init__(self, **kwargs):
        """Initialize the platform indicator."""
        try:
            super().__init__(**kwargs)
            self.orientation = "horizontal"
            self.spacing = 10
            self.padding = [10, 5]
            self.size_hint_y = None
            self.height = "50dp"
            self.bind(size=self._update_background)

            # Set icon source based on platform name
            icon_map = {
                "Spotify": "resources/icons/spotify.png",
                "Discogs": "resources/icons/discogs.png",
                "Rekordbox": "resources/icons/rekordbox.png",
            }
            self.icon_source = icon_map.get(self.platform_name, "")

            # Platform name label
            self.name_label = Label(
                text=self.platform_name, size_hint_x=0.5, color=(1, 1, 1, 1), bold=True
            )
            self.add_widget(self.name_label)

            # Icon image
            self.icon = Image(
                source=self.icon_source, size_hint_x=None, width="40dp", allow_stretch=True
            )
            self.add_widget(self.icon)

            # Authentication button
            self.auth_button = Button(
                text="Authenticate", size_hint_x=0.3, background_color=(0.8, 0.8, 0.8, 1)
            )
            self.add_widget(self.auth_button)

        except Exception as e:
            logger.error(f"Error initializing PlatformIndicator: {e}")

    def _update_background(self, *args):
        """Update the background color of the indicator."""
        from kivy.graphics import Color, Rectangle

        # Clear previous instructions
        self.canvas.before.clear()

        # Draw new background
        with self.canvas.before:
            Color(*self.status_color)
            Rectangle(pos=self.pos, size=self.size)

    def set_authenticated(self, is_authenticated: bool):
        """Set the authentication status color.

        Args:
            is_authenticated: Whether the platform is authenticated
        """
        self.status_color = (0, 0.7, 0, 1) if is_authenticated else (0.7, 0, 0, 1)
        self._update_background()


# Kivy language for any additional styling
Builder.load_string("""
<PlatformIndicator>:
    canvas.before:
        Color:
            rgba: self.status_color
        Rectangle:
            pos: self.pos
            size: self.size
""")
