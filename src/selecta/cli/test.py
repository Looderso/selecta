"""Test commands for Selecta platform clients."""

import os
import subprocess
import sys
from pathlib import Path

import click


@click.group()
def test():
    """Test platform clients and functionality."""
    pass


@test.command()
@click.option(
    "--platform",
    type=click.Choice(["all", "spotify", "rekordbox", "youtube", "discogs"]),
    default="all",
    help="Platform to test (default: all)",
)
@click.option(
    "--test-type",
    type=click.Choice(["compliance", "interchangeability", "authentication", "integration", "all"]),
    default="all",
    help="Type of tests to run (default: all)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--pattern", "-k", help="Run tests matching the given pattern")
def platform(platform: str, test_type: str, verbose: bool, pattern: str) -> None:
    """Test platform client compliance and interchangeability.

    This command runs comprehensive tests to ensure all platform clients
    work interchangeably while maintaining their platform-specific features.

    Test types:
    - compliance: Test that platforms implement AbstractPlatform correctly (mocked)
    - interchangeability: Test that platforms can be swapped without breaking functionality (mocked)
    - authentication: Test consistent authentication behavior across platforms (mocked)
    - integration: Test with real authentication flows (requires credentials, opens browser)
    - all: Run all test types (excluding integration unless specified)

    Examples:
        # Test all platforms with all test types
        selecta test platform

        # Test only Spotify compliance
        selecta test platform --platform spotify --test-type compliance

        # Test authentication consistency with verbose output
        selecta test platform --test-type authentication -v

        # Run tests matching a specific pattern
        selecta test platform -k "test_playlist_operations"

        # Test with real authentication (requires credentials)
        selecta test platform --test-type integration
    """
    # Get the project root directory
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent  # Go up to selecta/
    tests_dir = project_root / "src" / "tests" / "platform"

    if not tests_dir.exists():
        click.echo(f"❌ Tests directory not found: {tests_dir}", err=True)
        sys.exit(1)

    # Build pytest command
    pytest_args = ["python", "-m", "pytest"]

    if verbose:
        pytest_args.append("-v")

    if pattern:
        pytest_args.extend(["-k", pattern])

    # Determine which test files to run
    test_files = []

    if test_type in ["compliance", "all"]:
        if platform in ["spotify", "all"]:
            test_files.append(str(tests_dir / "spotify" / "test_spotify_compliance.py"))
        if platform in ["rekordbox", "all"]:
            test_files.append(str(tests_dir / "rekordbox" / "test_rekordbox_compliance.py"))
        if platform in ["youtube", "all"]:
            test_files.append(str(tests_dir / "youtube" / "test_youtube_compliance.py"))
        if platform in ["discogs", "all"]:
            test_files.append(str(tests_dir / "discogs" / "test_discogs_compliance.py"))

    if test_type in ["interchangeability", "all"] and platform == "all":
        test_files.append(str(tests_dir / "test_platform_interchangeability.py"))

    if test_type in ["authentication", "all"] and platform == "all":
        test_files.append(str(tests_dir / "test_authentication_consistency.py"))

    if test_type == "integration":
        test_files.append(str(tests_dir / "integration" / "test_real_authentication.py"))
        # Add integration marker for pytest
        pytest_args.extend(["-m", "integration"])

    if test_type in ["all"] and platform == "all":
        test_files.append(str(tests_dir / "test_all_platforms.py"))

    if not test_files:
        click.echo("❌ No test files selected for the given options", err=True)
        sys.exit(1)

    # Add test files to pytest command
    pytest_args.extend(test_files)

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    # Run the tests
    click.echo("🧪 Running platform tests...")
    click.echo(f"   Platform: {platform}")
    click.echo(f"   Test type: {test_type}")
    click.echo(f"   Command: {' '.join(pytest_args)}")
    click.echo()

    try:
        result = subprocess.run(pytest_args, cwd=project_root, env=env, check=False)

        if result.returncode == 0:
            click.echo("✅ All tests passed!")
        else:
            click.echo(f"❌ Some tests failed (exit code: {result.returncode})", err=True)
            sys.exit(result.returncode)

    except FileNotFoundError:
        click.echo("❌ pytest not found. Make sure you're in the virtual environment.", err=True)
        click.echo("   Try: source .venv/bin/activate", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error running tests: {e}", err=True)
        sys.exit(1)


@test.command()
@click.option("--coverage", is_flag=True, help="Run with coverage reporting")
@click.option("--html", is_flag=True, help="Generate HTML coverage report")
def coverage(coverage: bool, html: bool) -> None:
    """Run platform tests with coverage reporting.

    Examples:
        # Run tests with coverage
        selecta test coverage --coverage

        # Generate HTML coverage report
        selecta test coverage --coverage --html
    """
    # Get the project root directory
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    tests_dir = project_root / "src" / "tests" / "platform"

    if not tests_dir.exists():
        click.echo(f"❌ Tests directory not found: {tests_dir}", err=True)
        sys.exit(1)

    # Build pytest command with coverage
    pytest_args = ["python", "-m", "pytest"]

    if coverage:
        pytest_args.extend(["--cov=selecta.core.platform", "--cov-report=term-missing"])

        if html:
            pytest_args.append("--cov-report=html")

    pytest_args.append(str(tests_dir))

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    # Run the tests
    click.echo("🧪 Running platform tests with coverage...")
    click.echo(f"   Command: {' '.join(pytest_args)}")
    click.echo()

    try:
        result = subprocess.run(pytest_args, cwd=project_root, env=env, check=False)

        if result.returncode == 0:
            click.echo("✅ All tests passed!")
            if html:
                html_report = project_root / "htmlcov" / "index.html"
                if html_report.exists():
                    click.echo(f"📊 HTML coverage report: {html_report}")
        else:
            click.echo(f"❌ Some tests failed (exit code: {result.returncode})", err=True)
            sys.exit(result.returncode)

    except FileNotFoundError:
        click.echo("❌ pytest or coverage not found. Make sure you're in the virtual environment.", err=True)
        click.echo("   Try: source .venv/bin/activate", err=True)
        click.echo("   Install coverage: pip install pytest-cov", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error running tests: {e}", err=True)
        sys.exit(1)


@test.command()
def info():
    """Show information about the test suite."""
    click.echo("🧪 Selecta Platform Test Suite")
    click.echo("=" * 50)
    click.echo()
    click.echo("Test Structure:")
    click.echo("├── Platform Compliance Tests (mocked)")
    click.echo("│   ├── Spotify compliance")
    click.echo("│   ├── Rekordbox compliance")
    click.echo("│   ├── YouTube compliance")
    click.echo("│   └── Discogs compliance")
    click.echo("├── Interchangeability Tests (mocked)")
    click.echo("├── Authentication Consistency Tests (mocked)")
    click.echo("├── Integration Tests (real authentication)")
    click.echo("└── Comprehensive Platform Tests")
    click.echo()
    click.echo("What the tests verify:")
    click.echo("✓ All platforms implement AbstractPlatform interface correctly")
    click.echo("✓ Platforms can be swapped without breaking functionality")
    click.echo("✓ Authentication works consistently across platforms")
    click.echo("✓ Platform-specific features work while maintaining interchangeability")
    click.echo("✓ Cross-platform playlist operations (create/sync/import)")
    click.echo("✓ Error handling is consistent across platforms")
    click.echo()
    click.echo("Usage examples:")
    click.echo("  selecta test platform                    # Run all mocked tests")
    click.echo("  selecta test platform --platform spotify # Test only Spotify (mocked)")
    click.echo("  selecta test platform --test-type compliance # Test compliance only (mocked)")
    click.echo("  selecta test platform --test-type integration # Test with real auth (opens browser)")
    click.echo("  selecta test coverage --coverage --html  # Run with coverage report")


if __name__ == "__main__":
    test()
