"""Tests for Bear note parser."""

import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from docling.datamodel.base_models import InputFormat

from nova.bear_parser.parser import BearParser


@pytest.fixture
def note_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory with test notes.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path: Path to the temporary directory
    """
    note_dir = tmp_path / "notes"
    note_dir.mkdir()
    yield note_dir


def test_process_note_basic(note_dir: Path) -> None:
    """Test basic note processing."""
    note_file = note_dir / "test.txt"
    note_file.write_text("Test note content")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser(note_dir)
    notes = parser.process_notes(output_dir)

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "test"
    assert note.content == "Test note content"
    assert note.tags == []
    assert note.attachments == []
    assert isinstance(note.date, datetime)

    # Check output files
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test.metadata.json").exists()

    # Verify metadata
    with open(output_dir / "test.metadata.json") as f:
        metadata = json.load(f)
        assert metadata["title"] == "test"
        assert metadata["tags"] == []
        assert metadata["attachments"] == []
        assert "date" in metadata
        assert "processed_date" in metadata["metadata"]
        assert metadata["metadata"]["original_file"] == "test.txt"
        assert metadata["metadata"]["format"] == InputFormat.MD


def test_process_note_with_tags(note_dir: Path) -> None:
    """Test note processing with tags."""
    note_file = note_dir / "test.txt"
    note_file.write_text("Test note with #tag1 #tag2")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser(note_dir)
    notes = parser.process_notes(output_dir)

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "test"
    assert note.content == "Test note with #tag1 #tag2"
    assert set(note.tags) == {"tag1", "tag2"}
    assert note.attachments == []

    # Check output files
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test.metadata.json").exists()

    # Verify metadata
    with open(output_dir / "test.metadata.json") as f:
        metadata = json.load(f)
        assert metadata["title"] == "test"
        assert set(metadata["tags"]) == {"tag1", "tag2"}
        assert metadata["metadata"]["format"] == InputFormat.MD


def test_process_note_with_date(note_dir: Path) -> None:
    """Test note processing with date in filename."""
    note_file = note_dir / "20240101 - Test Note.txt"
    note_file.write_text("Test note content")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser(note_dir)
    notes = parser.process_notes(output_dir)

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "Test Note"
    assert note.date.strftime("%Y%m%d") == "20240101"

    # Check output files
    note_dir = output_dir / "Test Note"
    assert note_dir.is_dir()
    assert (note_dir / "20240101 - Test Note.md").exists()
    assert (note_dir / "metadata.json").exists()

    # Verify metadata
    with open(note_dir / "metadata.json") as f:
        metadata = json.load(f)
        assert metadata["title"] == "Test Note"
        assert metadata["metadata"]["format"] == InputFormat.MD
        assert metadata["metadata"]["original_file"] == "20240101 - Test Note.txt"


def test_process_note_invalid_file(note_dir: Path) -> None:
    """Test processing an invalid note file."""
    note_file = note_dir / "test.txt"
    note_file.write_text("")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser(note_dir)
    notes = parser.process_notes(output_dir)

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "test"
    assert note.content == ""
    assert note.tags == []
    assert note.attachments == []

    # Check output files
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test.metadata.json").exists()

    # Verify metadata
    with open(output_dir / "test.metadata.json") as f:
        metadata = json.load(f)
        assert metadata["title"] == "test"
        assert metadata["metadata"]["format"] == InputFormat.MD


def test_process_multiple_notes(note_dir: Path) -> None:
    """Test processing multiple notes."""
    # Create test notes
    (note_dir / "20240101 - Note 1.txt").write_text("Note 1 content #tag1")
    (note_dir / "20240102 - Note 2.txt").write_text("Note 2 content #tag2")
    (note_dir / "Note 3.txt").write_text("Note 3 content #tag3")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser(note_dir)
    notes = parser.process_notes(output_dir)

    assert len(notes) == 3

    # Check dated notes
    assert (output_dir / "Note 1" / "20240101 - Note 1.md").exists()
    assert (output_dir / "Note 1" / "metadata.json").exists()
    assert (output_dir / "Note 2" / "20240102 - Note 2.md").exists()
    assert (output_dir / "Note 2" / "metadata.json").exists()

    # Check undated note
    assert (output_dir / "Note 3.md").exists()
    assert (output_dir / "Note 3.metadata.json").exists()

    # Verify all notes have correct tags and format
    for note in notes:
        assert note.metadata["format"] == InputFormat.MD
        if note.title == "Note 1":
            assert note.tags == ["tag1"]
        elif note.title == "Note 2":
            assert note.tags == ["tag2"]
        elif note.title == "Note 3":
            assert note.tags == ["tag3"]
