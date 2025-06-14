"""CLI command for running integration tests with real platform connections."""

import subprocess
import sys
from pathlib import Path

import click

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.rekordbox.client import RekordboxClient
from selecta.core.platform.spotify.client import SpotifyClient
from selecta.core.platform.youtube.client import YouTubeClient


@click.command()
@click.option(
    "--platform",
    multiple=True,
    type=click.Choice(["spotify", "rekordbox", "youtube", "all"]),
    default=["all"],
    help="Which platforms to test (can specify multiple)",
)
@click.option(
    "--workflow",
    type=click.Choice(["sync", "consistency", "features", "all"]),
    default="all",
    help="Which test workflows to run",
)
@click.option("--check-auth", is_flag=True, help="Check authentication status before running tests")
@click.option("--cleanup", is_flag=True, help="Clean up test playlists after running tests")
def integration_test(platform, workflow, check_auth, cleanup):
    """Run integration tests with real platform connections.

    These tests verify cross-platform workflows by creating, importing,
    and syncing playlists between different platforms.

    Prerequisites:
    - Run 'selecta auth <platform>' for each platform first
    - Ensure Rekordbox database is accessible
    - Network connectivity required

    Examples:
        selecta integration-test --platform spotify rekordbox
        selecta integration-test --workflow sync --check-auth
        selecta integration-test --cleanup
    """
    settings_repo = SettingsRepository()

    if check_auth:
        click.echo("🔐 Checking platform authentication...")
        auth_status = check_platform_authentication(settings_repo, platform)

        if not all(auth_status.values()):
            click.echo("❌ Some platforms are not authenticated:")
            for platform_name, is_auth in auth_status.items():
                status = "✅" if is_auth else "❌"
                click.echo(f"  {status} {platform_name}")

            click.echo("\nRun authentication for missing platforms:")
            for platform_name, is_auth in auth_status.items():
                if not is_auth:
                    click.echo(f"  selecta auth {platform_name}")
            return
        else:
            click.echo("✅ All platforms authenticated!")

    # Build pytest command
    test_path = Path(__file__).parent.parent.parent / "tests" / "platform" / "integration"
    cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "-m", "integration"]

    # Add platform filtering
    if "all" not in platform:
        platform_marks = " or ".join([f"platform_{p}" for p in platform])
        cmd.extend(["-m", platform_marks])

    # Add workflow filtering
    if workflow != "all":
        cmd.extend(["-k", workflow])

    # Add cleanup flag as environment variable
    env = {"SELECTA_INTEGRATION_CLEANUP": "1"} if cleanup else {}

    click.echo("🧪 Running integration tests...")
    click.echo(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode == 0:
            click.echo("✅ Integration tests passed!")
        else:
            click.echo("❌ Some integration tests failed.")
        return result.returncode
    except Exception as e:
        click.echo(f"❌ Error running tests: {e}")
        return 1


def check_platform_authentication(settings_repo: SettingsRepository, platforms) -> dict[str, bool]:
    """Check authentication status for specified platforms."""
    auth_status = {}

    if "all" in platforms or "spotify" in platforms:
        try:
            spotify = SpotifyClient(settings_repo)
            auth_status["spotify"] = spotify.is_authenticated()
        except Exception:
            auth_status["spotify"] = False

    if "all" in platforms or "rekordbox" in platforms:
        try:
            rekordbox = RekordboxClient(settings_repo)
            auth_status["rekordbox"] = rekordbox.is_authenticated()
        except Exception:
            auth_status["rekordbox"] = False

    if "all" in platforms or "youtube" in platforms:
        try:
            youtube = YouTubeClient(settings_repo)
            auth_status["youtube"] = youtube.is_authenticated()
        except Exception:
            auth_status["youtube"] = False

    return auth_status


if __name__ == "__main__":
    integration_test()
