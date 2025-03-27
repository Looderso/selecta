# src/selecta/app.py
"""Main application module for Selecta."""

import sys
import traceback

from loguru import logger


# Modify src/selecta/app.py
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
        # Import and run the PyQt app
        logger.info("Starting Selecta application with PyQt6")
        from selecta.core.data.init_db import initialize_database
        from selecta.ui.app import run_app as run_pyqt_app

        # Initialize the database
        initialize_database()

        # Run the app
        return run_pyqt_app()
    except Exception as e:
        logger.exception(f"Error running Selecta application: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(run_app())
