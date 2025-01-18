"""Tests for Bear note processing."""

import shutil
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from nova.bear_parser.processing import BearNoteProcessing
from nova.bear_parser.parser import BearDocument


@pytest.fixture
def test_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory with test notes.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path: Path to the temporary directory
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create test notes
    note1 = input_dir / "20240101 - Note 1.txt"
    note1.write_text("Note 1 content #tag1")

    note2 = input_dir / "20240102 - Note 2.md"
    note2.write_text("# Note 2\nNote 2 content #tag2")

    # Create note with attachments
    note3 = input_dir / "Note 3.md"
    note3.write_text("Note 3 content #tag3\n![Image](test.jpg)")

    # Create attachment directory
    attachment_dir = input_dir / "Note 3"
    attachment_dir.mkdir()
    (attachment_dir / "test.jpg").write_text("test image content")

    yield input_dir


def test_process_bear_notes_basic(test_dir: Path, tmp_path: Path) -> None:
    """Test basic Bear note processing."""
    output_dir = tmp_path / "output"
    processor = BearNoteProcessing(input_dir=test_dir, output_dir=output_dir)
    documents = processor.process_bear_notes()

    # Verify documents were processed
    assert len(documents) == 3
    assert all(isinstance(doc, BearDocument) for doc in documents)

    # Verify document content
    doc_map = {doc.name: doc for doc in documents}

    # Check Note 1
    note1 = doc_map["Note 1"]
    assert note1.content == "Note 1 content #tag1"
    assert "tag1" in note1.tags
    assert note1.date.strftime("%Y%m%d") == "20240101"

    # Check Note 2
    note2 = doc_map["Note 2"]
    assert note2.content == "# Note 2\nNote 2 content #tag2"
    assert "tag2" in note2.tags
    assert note2.date.strftime("%Y%m%d") == "20240102"

    # Check Note 3
    note3 = doc_map["Note 3"]
    assert note3.content == "Note 3 content #tag3\n![Image](test.jpg)"
    assert "tag3" in note3.tags
    assert isinstance(note3.date, datetime)


def test_process_bear_notes_file_copying(test_dir: Path, tmp_path: Path) -> None:
    """Test file copying during Bear note processing."""
    output_dir = tmp_path / "output"
    processor = BearNoteProcessing(input_dir=test_dir, output_dir=output_dir)
    processor.process_bear_notes()

    # Verify files were copied
    assert (output_dir / "20240101 - Note 1.txt").exists()
    assert (output_dir / "20240102 - Note 2.md").exists()
    assert (output_dir / "Note 3.md").exists()

    # Verify attachments were copied
    attachment_dir = output_dir / "Note 3"
    assert attachment_dir.exists()
    assert (attachment_dir / "test.jpg").exists()
    assert (attachment_dir / "test.jpg").read_text() == "test image content"


def test_process_bear_notes_no_output_dir(test_dir: Path) -> None:
    """Test processing without output directory."""
    processor = BearNoteProcessing(input_dir=test_dir)
    documents = processor.process_bear_notes()

    # Verify documents were processed
    assert len(documents) == 3
    assert all(isinstance(doc, BearDocument) for doc in documents)


def test_process_bear_notes_empty_directory(tmp_path: Path) -> None:
    """Test processing empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    processor = BearNoteProcessing(input_dir=empty_dir)
    documents = processor.process_bear_notes()

    # Verify no documents were processed
    assert len(documents) == 0


def test_process_bear_notes_invalid_input(tmp_path: Path) -> None:
    """Test processing with invalid input directory."""
    invalid_dir = tmp_path / "nonexistent"

    processor = BearNoteProcessing(input_dir=invalid_dir)
    documents = processor.process_bear_notes()

    # Verify no documents were processed
    assert len(documents) == 0


def test_process_bear_notes_permission_error(test_dir: Path, tmp_path: Path) -> None:
    """Test handling of permission errors."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Make output directory read-only
    output_dir.chmod(0o444)

    processor = BearNoteProcessing(input_dir=test_dir, output_dir=output_dir)

    try:
        # Should still process documents even if copying fails
        documents = processor.process_bear_notes()
        assert len(documents) == 3
    finally:
        # Restore permissions for cleanup
        output_dir.chmod(0o755)
