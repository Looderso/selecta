"""Main entry point for the Selecta application.

This module forwards to the appropriate entry point based on how it was invoked.
"""

import sys

if __name__ == "__main__":
    # Check if being run directly
    if len(sys.argv) > 1 and sys.argv[1] in [
        "env",
        "install-completion",
        "--help",
        "-h",
    ]:
        # If CLI arguments are provided, run the CLI
        from selecta.cli.main import cli

        sys.exit(cli())
    else:
        # Otherwise, run the GUI app
        from selecta.app import run_app

        sys.exit(run_app())
