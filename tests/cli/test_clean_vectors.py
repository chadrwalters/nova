"""Tests for clean-vectors command."""

import logging
import pytest
from pathlib import Path
from collections.abc import Sequence

import click
import chromadb

from nova.cli.commands.clean_vectors import CleanVectorsCommand


@pytest.fixture
def mock_vector_store(tmp_path: Path) -> Path:
    """Create a mock vector store for testing.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path: Path to the mock vector store
    """
    vector_dir = tmp_path / ".nova" / "vectors"
    vector_dir.mkdir(parents=True)

    # Create a Chroma collection
    client = chromadb.PersistentClient(path=str(vector_dir))
    collection = client.create_collection("nova")

    # Create a test embedding
    embedding: Sequence[float] = [1.0, 2.0, 3.0]
    collection.add(
        embeddings=[embedding],
        metadatas=[{"test": "data"}],
        ids=["test_id"],
    )

    return vector_dir


def test_clean_vectors_without_force(
    mock_vector_store: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command without force flag.

    Args:
        mock_vector_store: Mock vector store fixture
        caplog: Pytest log capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    caplog.set_level(logging.WARNING)

    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_store.parent.parent)

    command = CleanVectorsCommand()
    command.run(force=False)

    # Vector store should still exist
    assert mock_vector_store.exists()
    assert "Use --force to actually delete the vector store" in caplog.text


def test_clean_vectors_with_force(
    mock_vector_store: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command with force flag.

    Args:
        mock_vector_store: Mock vector store fixture
        caplog: Pytest log capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    caplog.set_level(logging.INFO)

    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_store.parent.parent)

    command = CleanVectorsCommand()
    command.run(force=True)

    # Vector store should be deleted
    assert not mock_vector_store.exists()
    assert "Vector store deleted successfully" in caplog.text


def test_clean_vectors_nonexistent_store(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test clean-vectors command with nonexistent vector store.

    Args:
        tmp_path: Pytest temporary path fixture
        caplog: Pytest log capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    caplog.set_level(logging.INFO)

    # Change to the temporary directory
    monkeypatch.chdir(tmp_path)

    command = CleanVectorsCommand()
    command.run(force=True)

    assert "Vector store directory does not exist" in caplog.text


def test_clean_vectors_permission_error(
    mock_vector_store: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test clean-vectors command with permission error.

    Args:
        mock_vector_store: Mock vector store fixture
        caplog: Pytest log capture fixture
        monkeypatch: Pytest monkeypatch fixture
    """
    caplog.set_level(logging.ERROR)

    # Change to the directory containing the mock vector store
    monkeypatch.chdir(mock_vector_store.parent.parent)

    def mock_rmtree(*args: str, **kwargs: bool) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("shutil.rmtree", mock_rmtree)

    command = CleanVectorsCommand()
    with pytest.raises(
        click.Abort, match="Failed to delete vector store: Permission denied"
    ):
        command.run(force=True)

    # Vector store should still exist
    assert mock_vector_store.exists()
    assert "Failed to delete vector store: Permission denied" in caplog.text
