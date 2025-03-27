# src/selecta/app.py
"""Main application module for Selecta."""

import sys
import traceback

from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivymd.app import MDApp
from loguru import logger

from selecta.gui.authentication_view import PlatformAuthenticationView
from selecta.gui.playlist_view.unified_playlist_browser import UnifiedPlaylistBrowser


class SelectaApp(MDApp):
    """Main Kivy application class for Selecta."""

    def build(self):
        """Build the main application layout.

        Returns:
            BoxLayout: Main application layout
        """
        try:
            logger.info("Building Selecta application")

            # Set app theme - using valid color options from KivyMD 2.0+
            self.theme_cls.primary_palette = "Blue"  # Changed from BlueGray
            self.theme_cls.accent_palette = "Teal"  # This should be valid
            self.theme_cls.theme_style = "Dark"  # "Light" or "Dark"

            # Set default window size
            Window.size = (800, 600)

            # Create the authentication view
            # Create the screen manager
            self.screen_manager = ScreenManager(transition=SlideTransition())

            # Create authentication screen
            auth_screen = Screen(name="authentication")
            auth_screen.add_widget(PlatformAuthenticationView())

            # Create your new screen
            new_screen = Screen(name="playlist_browser")
            new_screen.add_widget(UnifiedPlaylistBrowser())

            # Add screens to the manager
            self.screen_manager.add_widget(auth_screen)
            self.screen_manager.add_widget(new_screen)

            # Start with the authentication screen
            self.screen_manager.current = "playlist_browser"

            return self.screen_manager

        except Exception as e:
            # Log full traceback
            logger.error(f"Error building app: {e}")
            logger.error(traceback.format_exc())

            # Create an error view
            error_view = BoxLayout(orientation="vertical")
            error_label = Label(
                text=f"Error initializing app:\n{e}",
                color=(1, 0, 0, 1),  # Red color
            )
            error_view.add_widget(error_label)
            return error_view


def run_app(args: list[str] | None = None) -> int:
    """Entry point for running the GUI application.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        int: Exit code
    """
    if args is None:
        args = sys.argv[1:]

    try:
        # Create and run the Kivy app
        logger.info("Starting Selecta application")
        app = SelectaApp()
        app.run()
        return 0
    except Exception as e:
        logger.exception(f"Error running Selecta application: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(run_app())
