"""Tests for error handling functionality."""

from typing import Any

import click
import pytest
from click.testing import CliRunner

from nova.cli.main import NovaCLI
from nova.cli.utils.command import NovaCommand
from nova.cli.utils.errors import (
    RebuildErrorType,
    create_rebuild_error,
    get_recovery_strategy,
    is_recoverable_error,
)


class ErrorTestCommand(NovaCommand):
    """Test command for error handling."""

    name = "error-test"
    help = "Test error handling"

    def __init__(self) -> None:
        """Initialize test command."""
        super().__init__()
        self.error_type: str | None = None
        self.is_recoverable: bool = False
        self.recovery_hint: str | None = None

    def run(self, **kwargs: Any) -> None:
        """Run the test command."""
        try:
            error_type = kwargs.get("error_type")
            if error_type == "rebuild":
                raise create_rebuild_error(
                    error_type=RebuildErrorType.PROCESSING,
                    message="Test rebuild error",
                    context={"test": True},
                    is_recoverable=self.is_recoverable,
                    recovery_hint=self.recovery_hint,
                )
            elif error_type == "file":
                raise FileNotFoundError("test.txt")
            elif error_type == "permission":
                raise PermissionError("Permission denied")
            elif error_type == "timeout":
                raise TimeoutError("Operation timed out")
            else:
                raise Exception("Unknown error")
        except Exception as e:
            self.handle_error(e)
            # Use click.Abort to exit with error code while preserving stderr
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the test command."""

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--error-type",
            type=click.Choice(["rebuild", "file", "permission", "timeout", "unknown"]),
            required=True,
        )
        def command(**kwargs: Any) -> None:
            """Run the error test command."""
            try:
                self.run(**kwargs)
            except click.Abort:
                raise
            except Exception as e:
                self.handle_error(e)
                raise click.Abort()

        return command


def test_rebuild_error_creation() -> None:
    """Test RebuildError creation and string representation."""
    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={"test": True},
        is_recoverable=True,
        recovery_hint="Try again",
    )

    assert error.error_type == RebuildErrorType.PROCESSING
    assert error.message == "Test error"
    assert error.context == {"test": True}
    assert error.is_recoverable is True
    assert error.recovery_hint == "Try again"

    error_str = str(error)
    assert "[PROCESSING]" in error_str
    assert "Test error" in error_str
    assert "Context: {'test': True}" in error_str
    assert "Recovery hint: Try again" in error_str


def test_is_recoverable_error() -> None:
    """Test error recoverability checking."""
    # Test RebuildError
    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={},
        is_recoverable=True,
    )
    assert is_recoverable_error(error) is True

    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={},
        is_recoverable=False,
    )
    assert is_recoverable_error(error) is False

    # Test other error types
    assert is_recoverable_error(FileNotFoundError()) is True
    assert is_recoverable_error(PermissionError()) is True
    assert is_recoverable_error(TimeoutError()) is True
    assert is_recoverable_error(ValueError()) is False


def test_get_recovery_strategy() -> None:
    """Test recovery strategy retrieval."""
    # Test with recovery hint
    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={},
        is_recoverable=True,
        recovery_hint="Custom recovery hint",
    )
    assert get_recovery_strategy(error) == "Custom recovery hint"

    # Test without recovery hint
    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={},
        is_recoverable=True,
    )
    assert get_recovery_strategy(error) == "Check input files and retry failed items"

    # Test non-recoverable error
    error = create_rebuild_error(
        error_type=RebuildErrorType.PROCESSING,
        message="Test error",
        context={},
        is_recoverable=False,
    )
    assert get_recovery_strategy(error) is None


def test_handle_rebuild_error_non_recoverable(runner, capsys):
    """Test handling a non-recoverable rebuild error."""
    cmd = ErrorTestCommand()
    cmd.is_recoverable = False
    result = runner.invoke(cmd.create_command(), ["--error-type", "rebuild"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Test rebuild error" in captured.err
    assert "Context: {'test': True}" in captured.err


def test_handle_rebuild_error_recoverable(runner, capsys):
    """Test handling a recoverable rebuild error."""
    cmd = ErrorTestCommand()
    cmd.is_recoverable = True
    cmd.recovery_hint = "Try this recovery step"
    result = runner.invoke(cmd.create_command(), ["--error-type", "rebuild"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Test rebuild error" in captured.err
    assert "Context: {'test': True}" in captured.err
    assert "Recovery hint: Try this recovery step" in captured.err


def test_handle_file_not_found_error(runner, capsys):
    """Test handling a file not found error."""
    cmd = ErrorTestCommand()
    result = runner.invoke(cmd.create_command(), ["--error-type", "file"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[WARNING]" in captured.err
    assert "File not found" in captured.err
    assert "[INFO] Creating missing directories..." in captured.err


def test_handle_permission_error(runner, capsys):
    """Test handling a permission error."""
    cmd = ErrorTestCommand()
    result = runner.invoke(cmd.create_command(), ["--error-type", "permission"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[WARNING]" in captured.err
    assert "Permission denied" in captured.err
    assert "[INFO] Please check file permissions and try again" in captured.err


def test_handle_timeout_error(runner, capsys):
    """Test handling a timeout error."""
    cmd = ErrorTestCommand()
    result = runner.invoke(cmd.create_command(), ["--error-type", "timeout"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[WARNING]" in captured.err
    assert "Operation timed out" in captured.err
    assert "[INFO] You can retry the operation" in captured.err


def test_handle_unknown_error(runner, capsys):
    """Test handling an unknown error."""
    cmd = ErrorTestCommand()
    result = runner.invoke(cmd.create_command(), ["--error-type", "unknown"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Unknown error" in captured.err


@pytest.fixture
def cli():
    """Create a CLI fixture."""
    return NovaCLI().create_cli()


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner(mix_stderr=False)
