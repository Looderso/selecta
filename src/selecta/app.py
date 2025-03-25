"""Main application module for Selecta."""

import sys

from loguru import logger


class SelectaApp:
    """Main application class for Selecta."""

    def __init__(self) -> None:
        """Initialize the Selecta application."""
        logger.info("Initializing Selecta application")

    def run(self) -> int:
        """Run the Selecta application.

        Returns:
            int: Exit code
        """
        logger.info("Running Selecta application")
        # Placeholder for actual application logic
        return 0


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
        app = SelectaApp()
        return app.run()
    except Exception as e:
        logger.exception(f"Error running Selecta application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_app())
