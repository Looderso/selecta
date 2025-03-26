"""Environment management commands for Selecta development."""

import shutil
import subprocess
import sys
from pathlib import Path

import click
import click_completion
from loguru import logger

# Setup click_completion
click_completion.init()


def get_project_root() -> Path:
    """Find the project root directory based on pyproject.toml location.

    Returns:
        Path: The project root directory path
    """
    # Start from the current directory and look upwards for pyproject.toml
    current_dir = Path.cwd()

    while True:
        if (current_dir / "pyproject.toml").exists():
            return current_dir

        # Move up one directory
        parent_dir = current_dir.parent

        # If we've reached the root of the filesystem, stop searching
        if parent_dir == current_dir:
            # If not found, default to current directory with a warning
            logger.warning(
                "Could not find project root (no pyproject.toml found). Using current directory."
            )
            return Path.cwd()

        current_dir = parent_dir


def run_command(command: str, cwd: Path | None = None) -> int:
    """Run a shell command and display its output.

    Args:
        command: The command to run
        cwd: The directory to run the command in (default: current directory)

    Returns:
        int: The return code of the command
    """
    logger.info(f"Running: {command}")

    try:
        # Use shell=True for complex commands with pipes, redirects, etc.
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=cwd,
        )

        # Stream output to console
        for line in process.stdout:
            sys.stdout.write(line)

        return_code = process.wait()
        return return_code

    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


@click.group()
def env():
    """Environment management commands for Selecta development."""
    pass


@env.command(name="reinstall", help="Reinstall the development environment from scratch")
@click.option(
    "--force/--no-force",
    default=False,
    help="Force reinstallation without confirmation",
)
def reinstall_environment(force: bool) -> None:
    """Reinstall the development environment from scratch.

    Args:
        force: Skip confirmation prompt if True
    """
    project_root = get_project_root()
    venv_path = project_root / ".venv"

    if (
        venv_path.exists()
        and not force
        and not click.confirm(
            "This will delete the existing virtual environment and reinstall. Continue?",
            default=True,
        )
    ):
        logger.info("Operation cancelled")
        return

    # Delete existing virtual environment if it exists
    if venv_path.exists():
        logger.info("Removing existing virtual environment...")
        try:
            shutil.rmtree(venv_path)
            logger.success("Removed existing virtual environment")
        except Exception as e:
            logger.error(f"Failed to remove virtual environment: {e}")
            return

    # Run the dev_setup.sh script
    setup_script = project_root / "scripts" / "dev_setup.sh"

    if not setup_script.exists():
        logger.error(f"Setup script not found at {setup_script}")
        return

    logger.info("Running dev_setup.sh script...")
    result = run_command(f"bash {setup_script}", cwd=project_root)

    if result == 0:
        logger.success("Environment reinstalled successfully")
    else:
        logger.error("Failed to reinstall environment")


@env.command(name="activate", help="Print the command to activate the virtual environment")
def activate_environment() -> None:
    """Print the command to activate the virtual environment.

    Since a subprocess cannot modify the parent shell's environment,
    this command prints the activation command for the user to execute.
    """
    project_root = get_project_root()
    venv_path = project_root / ".venv"

    if not venv_path.exists():
        logger.error("Virtual environment not found. Please run 'selecta env reinstall' first.")
        return

    # Determine the appropriate activation script based on the platform
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate"
        cmd = f"source {activate_script}"
        ps_cmd = f"& {activate_script.with_suffix('.ps1')}"

        click.echo("\nTo activate the environment in CMD:")
        click.echo(f"{activate_script.with_name('activate.bat')}")
        click.echo("\nTo activate the environment in PowerShell:")
        click.echo(f"{ps_cmd}")
        click.echo("\nTo activate the environment in Git Bash / WSL:")
        click.echo(f"{cmd}")
    else:
        # For Unix-like systems (Linux, macOS)
        activate_script = venv_path / "bin" / "activate"
        cmd = f"source {activate_script}"

        click.echo("\nTo activate the environment, run:")
        click.echo(f"{cmd}")

    click.echo(
        "\nNote: You need to run this command in your shell; copying "
        "and pasting the above command is recommended."
    )


if __name__ == "__main__":
    env()
