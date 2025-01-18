"""Tests for clean-vectors command."""

import logging
from pathlib import Path

import click
import pytest

from nova.cli.commands.clean_vectors import CleanVectorsCommand


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
def mock_vector_dir(tmp_path: Path) -> Path:
    """Create a mock vector store directory for testing.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path: Path to the mock vector store directory
    """
    vector_dir = tmp_path / ".nova" / "vectors"
    vector_dir.mkdir(parents=True)

    # Create some test files
    test_file = vector_dir / "test.chroma"
    test_file.write_text("Test content")

    return vector_dir


def test_clean_vectors_without_force(
    mock_vector_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command without force flag.

    Args:
        mock_vector_dir: Mock vector store directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_dir.parent.parent)

    command = CleanVectorsCommand()
    command.run(force=False)

    # Vector store should still exist
    assert mock_vector_dir.exists()
    captured = capsys.readouterr()
    assert "Use --force to actually delete the vector store" in captured.err


def test_clean_vectors_with_force(
    mock_vector_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command with force flag.

    Args:
        mock_vector_dir: Mock vector store directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_dir.parent.parent)

    command = CleanVectorsCommand()
    command.run(force=True)

    # Vector store should be deleted
    assert not mock_vector_dir.exists()
    captured = capsys.readouterr()
    assert "Vector store deleted successfully" in captured.err


def test_clean_vectors_nonexistent_store(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command with nonexistent vector store.

    Args:
        tmp_path: Pytest temporary path fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the temporary directory
    monkeypatch.chdir(tmp_path)

    command = CleanVectorsCommand()
    command.run(force=True)

    captured = capsys.readouterr()
    assert "Vector store directory does not exist" in captured.err


def test_clean_vectors_permission_error(
    mock_vector_dir: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command with permission error.

    Args:
        mock_vector_dir: Mock vector store directory fixture
        caplog: Pytest log capture fixture
        capsys: Pytest stdout/stderr capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_dir.parent.parent)

    def mock_rmtree(*args: str, **kwargs: bool) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("shutil.rmtree", mock_rmtree)

    command = CleanVectorsCommand()
    with pytest.raises(click.Abort, match="Failed to delete vector store: Permission denied"):
        command.run(force=True)

    # Vector store should still exist
    assert mock_vector_dir.exists()
    captured = capsys.readouterr()
    assert "Failed to delete vector store: Permission denied" in captured.err
