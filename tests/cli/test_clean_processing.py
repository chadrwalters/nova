"""Tests for clean-processing command."""

import logging
from pathlib import Path

import click
import pytest

from nova.cli.commands.clean_processing import CleanProcessingCommand


@pytest.fixture(autouse=True)
def setup_logging(caplog: pytest.LogCaptureFixture):
    """Configure logging for tests."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Configure caplog
    caplog.set_level(logging.INFO)

    # Configure nova loggers
    for logger_name in ["nova.cli", "nova.vector_store", "nova.monitoring"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = True

    # Clear any existing handlers
    root_logger.handlers = []

    # Add a basic stream handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    return root_logger


@pytest.fixture
def mock_processing_dir(tmp_path: Path) -> Path:
    """Create a mock processing directory for testing.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path: Path to the mock processing directory
    """
    processing_dir = tmp_path / ".nova" / "processing"
    processing_dir.mkdir(parents=True)

    # Create some test files
    test_file = processing_dir / "test.md"
    test_file.write_text("Test content")

    return processing_dir


def test_clean_processing_without_force(
    mock_processing_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-processing command without force flag.

    Args:
        mock_processing_dir: Mock processing directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock processing dir
    monkeypatch.chdir(mock_processing_dir.parent.parent)

    command = CleanProcessingCommand()
    command.run(force=False)

    # Processing directory should still exist
    assert mock_processing_dir.exists()
    captured = capsys.readouterr()
    assert "Use --force to actually delete the processing directory" in captured.err


def test_clean_processing_with_force(
    mock_processing_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-processing command with force flag.

    Args:
        mock_processing_dir: Mock processing directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock processing dir
    monkeypatch.chdir(mock_processing_dir.parent.parent)

    command = CleanProcessingCommand()
    command.run(force=True)

    # Processing directory should be deleted
    assert not mock_processing_dir.exists()
    captured = capsys.readouterr()
    assert "Processing directory deleted successfully" in captured.err


def test_clean_processing_nonexistent_dir(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-processing command with nonexistent directory.

    Args:
        tmp_path: Pytest temporary path fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the temporary directory
    monkeypatch.chdir(tmp_path)

    command = CleanProcessingCommand()
    command.run(force=True)

    captured = capsys.readouterr()
    assert "Processing directory does not exist" in captured.err


def test_clean_processing_permission_error(
    mock_processing_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-processing command with permission error.

    Args:
        mock_processing_dir: Mock processing directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock processing dir
    monkeypatch.chdir(mock_processing_dir.parent.parent)

    def mock_rmtree(*args: str, **kwargs: bool) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("shutil.rmtree", mock_rmtree)

    command = CleanProcessingCommand()
    with pytest.raises(
        click.Abort, match="Failed to delete processing directory: Permission denied"
    ):
        command.run(force=True)

    # Processing directory should still exist
    assert mock_processing_dir.exists()
    captured = capsys.readouterr()
    assert "Failed to delete processing directory: Permission denied" in captured.err
