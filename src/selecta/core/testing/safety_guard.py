"""Safety system for platform testing to prevent accidental modification of real playlists.

This module provides comprehensive protection mechanisms to ensure that test scripts
can only interact with designated test playlists and never touch real user data.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class OperationType(Enum):
    """Types of operations that can be performed on playlists."""

    READ = "read"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class SafetyLevel(Enum):
    """Safety levels for test operations."""

    READ_ONLY = "read_only"  # No modifications allowed
    TEST_ONLY = "test_only"  # Only marked test playlists
    INTERACTIVE = "interactive"  # Requires user confirmation
    DISABLED = "disabled"  # No safety checks (dangerous!)


@dataclass
class SafetyConfig:
    """Configuration for safety system."""

    # Test markers (in order of preference)
    test_markers: list[str]
    safety_level: SafetyLevel
    require_confirmation: bool
    dry_run_mode: bool
    max_test_playlists: int
    emergency_stop_enabled: bool


class SafetyGuard:
    """Comprehensive safety system for platform testing.

    This class ensures that test scripts can only interact with explicitly
    marked test playlists and provides multiple layers of protection against
    accidental modification of real user data.
    """

    # Default test markers in order of preference
    DEFAULT_MARKERS = [
        "🧪",  # Test tube emoji (preferred for visual distinction)
        "[TEST]",  # Fallback for platforms that don't support emojis
        "SELECTA_TEST_",  # Legacy prefix
    ]

    def __init__(self, config: SafetyConfig | None = None):
        """Initialize the safety guard with configuration.

        Args:
            config: Safety configuration, uses defaults if None
        """
        self.config = config or self._get_default_config()
        self._emergency_stop = False
        self._operation_log: list[str] = []

        # Validate configuration
        self._validate_config()

        logger.info(f"SafetyGuard initialized with level: {self.config.safety_level.value}")
        if self.config.dry_run_mode:
            logger.warning("DRY RUN MODE: No actual changes will be made")

    def _get_default_config(self) -> SafetyConfig:
        """Get default safety configuration from environment or safe defaults."""
        return SafetyConfig(
            test_markers=self.DEFAULT_MARKERS,
            safety_level=SafetyLevel(os.getenv("SELECTA_SAFETY_LEVEL", "test_only")),
            require_confirmation=os.getenv("SELECTA_REQUIRE_CONFIRMATION", "true").lower() == "true",
            dry_run_mode=os.getenv("SELECTA_DRY_RUN", "false").lower() == "true",
            max_test_playlists=int(os.getenv("SELECTA_MAX_TEST_PLAYLISTS", "50")),
            emergency_stop_enabled=True,
        )

    def _validate_config(self) -> None:
        """Validate safety configuration."""
        if not self.config.test_markers:
            raise ValueError("At least one test marker must be configured")

        if self.config.max_test_playlists <= 0:
            raise ValueError("max_test_playlists must be positive")

    def is_test_playlist(self, playlist_name: str) -> bool:
        """Check if a playlist name matches any test marker.

        Args:
            playlist_name: The playlist name to check

        Returns:
            True if the playlist is marked as a test playlist
        """
        if not playlist_name:
            return False

        # Check each marker
        return any(playlist_name.startswith(marker) for marker in self.config.test_markers)

    def verify_test_playlist(self, playlist_name: str, operation: OperationType) -> bool:
        """Verify that an operation on a playlist is safe to perform.

        Args:
            playlist_name: Name of the playlist
            operation: Type of operation being performed

        Returns:
            True if the operation is safe to perform

        Raises:
            PermissionError: If the operation is not allowed
        """
        # Check emergency stop
        if self._emergency_stop:
            raise PermissionError("Emergency stop activated - all operations blocked")

        # Check if it's a test playlist
        is_test = self.is_test_playlist(playlist_name)

        # Apply safety level rules
        if self.config.safety_level == SafetyLevel.READ_ONLY:
            if operation != OperationType.READ:
                raise PermissionError(f"Read-only mode: {operation.value} operations not allowed")

        elif self.config.safety_level == SafetyLevel.TEST_ONLY:
            if not is_test and operation != OperationType.READ:
                raise PermissionError(
                    f"Test-only mode: {operation.value} operations only allowed on test playlists. "
                    f"Playlist '{playlist_name}' does not start with any test marker: {self.config.test_markers}"
                )

        elif self.config.safety_level == SafetyLevel.INTERACTIVE:
            should_ask = not is_test and operation != OperationType.READ
            if should_ask and not self._get_user_confirmation(playlist_name, operation):
                raise PermissionError(f"User denied {operation.value} operation on '{playlist_name}'")

        elif self.config.safety_level == SafetyLevel.DISABLED:
            logger.warning(f"Safety disabled: Allowing {operation.value} on '{playlist_name}'")

        # Log the operation
        self._log_operation(playlist_name, operation)

        return True

    def _get_user_confirmation(self, playlist_name: str, operation: OperationType) -> bool:
        """Get user confirmation for potentially dangerous operations.

        Args:
            playlist_name: Name of the playlist
            operation: Type of operation

        Returns:
            True if user confirms the operation
        """
        if not self.config.require_confirmation:
            return True

        prompt = (
            f"⚠️  SAFETY WARNING ⚠️\n"
            f"About to perform {operation.value.upper()} operation on playlist: '{playlist_name}'\n"
            f"This playlist does NOT appear to be a test playlist.\n"
            f"Test playlists should start with: {self.config.test_markers}\n\n"
            f"Are you sure you want to proceed? (yes/no): "
        )

        try:
            response = input(prompt).strip().lower()
            return response in ("yes", "y")
        except (EOFError, KeyboardInterrupt):
            return False

    def _log_operation(self, playlist_name: str, operation: OperationType) -> None:
        """Log an operation for audit trail.

        Args:
            playlist_name: Name of the playlist
            operation: Type of operation
        """
        log_entry = f"{operation.value.upper()}: {playlist_name}"
        self._operation_log.append(log_entry)

        if self.config.dry_run_mode:
            logger.info(f"DRY RUN: Would perform {log_entry}")
        else:
            logger.info(f"OPERATION: {log_entry}")

    def emergency_stop(self) -> None:
        """Activate emergency stop to block all operations."""
        self._emergency_stop = True
        logger.critical("🚨 EMERGENCY STOP ACTIVATED - All operations blocked!")

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop to allow operations again."""
        self._emergency_stop = False
        logger.info("Emergency stop reset - Operations allowed again")

    def get_operation_log(self) -> list[str]:
        """Get the log of all operations performed.

        Returns:
            List of operation log entries
        """
        return self._operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self._operation_log.clear()

    def create_test_playlist_name(self, base_name: str) -> str:
        """Create a safe test playlist name with appropriate marker.

        Args:
            base_name: Base name for the playlist

        Returns:
            Playlist name with test marker prefix
        """
        # Use the first (preferred) marker
        marker = self.config.test_markers[0]

        # Clean the base name
        clean_name = base_name.strip()

        # Add marker if not already present
        if not self.is_test_playlist(clean_name):
            return f"{marker} {clean_name}"

        return clean_name

    def validate_test_environment(self) -> bool:
        """Validate that the test environment is safe.

        Returns:
            True if environment is safe for testing

        Raises:
            EnvironmentError: If environment is not safe
        """
        # Check if we're in a test environment
        if os.getenv("SELECTA_ENVIRONMENT") == "production":
            raise OSError("Cannot run tests in production environment")

        # Warn about safety level
        if self.config.safety_level == SafetyLevel.DISABLED:
            logger.critical("⚠️  SAFETY DISABLED - This is dangerous!")
            if not self._get_user_confirmation("SAFETY SYSTEM", OperationType.MODIFY):
                raise OSError("User cancelled due to disabled safety")

        return True

    def with_operation_guard(self, playlist_name: str, operation: OperationType) -> Callable:
        """Decorator to guard playlist operations.

        Args:
            playlist_name: Name of the playlist
            operation: Type of operation

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Verify the operation is safe
                self.verify_test_playlist(playlist_name, operation)

                # If dry run, don't execute
                if self.config.dry_run_mode and operation != OperationType.READ:
                    logger.info(f"DRY RUN: Skipping {func.__name__} on '{playlist_name}'")
                    return None

                # Execute the function
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Global safety guard instance
_safety_guard: SafetyGuard | None = None


def get_safety_guard() -> SafetyGuard:
    """Get the global safety guard instance.

    Returns:
        The global SafetyGuard instance
    """
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = SafetyGuard()
    return _safety_guard


def reset_safety_guard(config: SafetyConfig | None = None) -> SafetyGuard:
    """Reset the global safety guard with new configuration.

    Args:
        config: New safety configuration

    Returns:
        New SafetyGuard instance
    """
    global _safety_guard
    _safety_guard = SafetyGuard(config)
    return _safety_guard


# Convenience functions
def is_test_playlist(playlist_name: str) -> bool:
    """Check if a playlist name is a test playlist."""
    return get_safety_guard().is_test_playlist(playlist_name)


def verify_safe_operation(playlist_name: str, operation: OperationType) -> bool:
    """Verify that an operation is safe to perform."""
    return get_safety_guard().verify_test_playlist(playlist_name, operation)


def create_test_playlist_name(base_name: str) -> str:
    """Create a safe test playlist name."""
    return get_safety_guard().create_test_playlist_name(base_name)


def emergency_stop() -> None:
    """Activate emergency stop."""
    get_safety_guard().emergency_stop()
