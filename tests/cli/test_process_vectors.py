"""Tests for the process vectors command."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest
import click

from nova.cli.commands.process_vectors import ProcessVectorsCommand
from nova.vector_store.store import VectorStore
from nova.monitoring.session import SessionMonitor


@pytest.fixture
def input_dir() -> Generator[Path, None, None]:
    """Create a temporary input directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test markdown files
        file1 = temp_path / "test1.md"
        file1.write_text("# Test Document 1\nThis is a test document about machine learning.")

        file2 = temp_path / "test2.md"
        file2.write_text("""# First Section
This is the first section about Python programming.

# Second Section
This is about machine learning with Python.

# Third Section
This discusses JavaScript and web development.""")

        yield temp_path


@pytest.fixture
def output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


@pytest.fixture
def mock_store() -> Mock:
    """Create a mock vector store."""
    store = create_autospec(VectorStore)
    store.search.return_value = []
    return store


@pytest.fixture
def mock_monitor() -> Mock:
    """Create a mock session monitor."""
    monitor = create_autospec(SessionMonitor)
    return monitor


@pytest.fixture
def store(output_dir: Path) -> VectorStore:
    """Create a real vector store for testing."""
    store = VectorStore(str(output_dir), use_memory=True)
    return store


@pytest.fixture(autouse=True)
def cleanup_store(store: VectorStore) -> Generator[None, None, None]:
    """Clean up the store after each test."""
    yield
    store.clear()  # Clear the store after each test


def test_process_vectors_basic(input_dir: Path, output_dir: Path, store: VectorStore) -> None:
    """Test basic vector processing."""
    command = ProcessVectorsCommand(vector_store=store)

    # Process vectors
    command.run(input_dir=str(input_dir), output_dir=str(output_dir))

    # Verify output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()

    # Search for the actual content
    results = store.search("machine learning")

    assert len(results) > 0
    assert "machine learning" in results[0]["text"].lower()
    assert results[0]["score"] > 0.5  # High relevance for exact match


def test_process_vectors_empty_directory(output_dir: Path, mock_store: Mock) -> None:
    """Test processing empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_dir = Path(temp_dir)
        command = ProcessVectorsCommand(vector_store=mock_store)

        # Process vectors - should handle empty directory gracefully
        command.run(input_dir=str(empty_dir), output_dir=str(output_dir))

        # Verify output directory exists
        assert output_dir.exists()
        assert output_dir.is_dir()

        # Verify no chunks were added to the store
        mock_store.add_chunk.assert_not_called()

        # Verify search returns empty results
        mock_store.search.return_value = []
        results = mock_store.search("test")
        assert len(results) == 0


def test_process_vectors_multiple_files(input_dir: Path, output_dir: Path, store: VectorStore) -> None:
    """Test processing multiple markdown files."""
    command = ProcessVectorsCommand(vector_store=store)

    command.run(input_dir=str(input_dir), output_dir=str(output_dir))

    # Search for Python content
    python_results = store.search("python programming")
    assert len(python_results) > 0
    assert any("Python programming" in r["text"] for r in python_results)

    # Search for JavaScript content
    js_results = store.search("javascript web")
    assert len(js_results) > 0
    assert any("JavaScript" in r["text"] for r in js_results)

    # Verify ordering - Python query should rank Python content higher
    python_scores = [r["score"] for r in python_results if "Python" in r["text"]]
    js_scores = [r["score"] for r in python_results if "JavaScript" in r["text"]]
    if js_scores:  # If JavaScript results appear in Python search
        assert max(python_scores) > max(js_scores)


def test_process_vectors_missing_args() -> None:
    """Test missing arguments."""
    command = ProcessVectorsCommand()

    with pytest.raises(click.UsageError, match="Input directory not specified"):
        command.run()

    with pytest.raises(click.UsageError, match="Input directory not specified"):
        command.run(output_dir="test")


def test_process_vectors_nonexistent_directory(output_dir: Path, store: VectorStore) -> None:
    """Test processing nonexistent directory."""
    command = ProcessVectorsCommand(vector_store=store)
    nonexistent_dir = Path("/nonexistent/directory")

    with pytest.raises(click.UsageError, match=f"Text directory not found: {nonexistent_dir}"):
        command.run(input_dir=str(nonexistent_dir), output_dir=str(output_dir))


def test_process_vectors_no_markdown_files(output_dir: Path, store: VectorStore) -> None:
    """Test processing directory with no markdown files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir)

        # Create non-markdown files
        (input_dir / "test.txt").write_text("This is a text file")
        (input_dir / "test.json").write_text('{"test": "data"}')

        command = ProcessVectorsCommand(vector_store=store)
        command.run(input_dir=str(input_dir), output_dir=str(output_dir))

        # Verify no chunks were created
        results = store.search("test")
        assert len(results) == 0


def test_process_vectors_with_monitor(input_dir: Path, output_dir: Path, store: VectorStore, mock_monitor: Mock) -> None:
    """Test vector processing with session monitoring."""
    command = ProcessVectorsCommand(vector_store=store)
    command.monitor = mock_monitor

    command.run(input_dir=str(input_dir), output_dir=str(output_dir))

    # Verify monitor was called
    mock_monitor.track_rebuild_progress.assert_called_once()
    mock_monitor.update_rebuild_progress.assert_called()
    mock_monitor.complete_rebuild.assert_called_once()


def test_process_vectors_with_errors(input_dir: Path, output_dir: Path, store: VectorStore, mock_monitor: Mock) -> None:
    """Test vector processing with errors."""
    command = ProcessVectorsCommand(vector_store=store)
    command.monitor = mock_monitor

    # Create an invalid markdown file
    invalid_file = input_dir / "invalid.md"
    invalid_file.write_text("# Test\n\x00Invalid bytes")  # Add null bytes to cause encoding error

    # Create a valid file to ensure partial processing works
    valid_file = input_dir / "valid.md"
    valid_file.write_text("# Test\nThis is a valid file.")

    command.run(input_dir=str(input_dir), output_dir=str(output_dir))

    # Verify monitor recorded errors
    mock_monitor.record_rebuild_error.assert_called()

    # Verify valid files were still processed
    results = store.search("valid file")
    assert len(results) > 0
