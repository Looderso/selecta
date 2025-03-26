"""Main application module for Selecta."""

import sys
import traceback

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from loguru import logger

from selecta.gui.authentication_view import PlatformAuthenticationView


class SelectaApp(App):
    """Main Kivy application class for Selecta."""

    def build(self) -> BoxLayout:
        """Build the main application layout.

        Returns:
            BoxLayout: Main application layout
        """
        try:
            logger.info("Building Selecta application")

            # Set default window size
            Window.size = (400, 600)

            # Create the authentication view
            auth_view = PlatformAuthenticationView()

            # Add a debug label if needed
            debug_label = Label(
                text="Authentication View Loaded",
                size_hint_y=None,
                height=50,
                color=(1, 0, 0, 1),  # Red color for visibility
            )
            auth_view.add_widget(debug_label)

            return auth_view
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
