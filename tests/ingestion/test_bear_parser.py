"""Tests for Bear note parser."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from nova.bear_parser.parser import BearParser, BearNote


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

    parser = BearParser(note_dir)
    parser.parse_directory()
    maybe_notes = parser._notes
    assert maybe_notes is not None
    notes = maybe_notes

    assert len(notes) == 1
    note = notes[0]
    assert isinstance(note, BearNote)
    assert note.title == "test"
    assert note.content == "Test note content"
    assert note.tags == []
    assert note.attachments == []
    assert isinstance(note.date, datetime)

    # Convert to docling document
    doc = note.to_docling()
    assert doc.name == "test"
    assert doc.content == "Test note content"
    assert doc.tags == []


def test_process_note_with_tags(note_dir: Path) -> None:
    """Test note processing with tags."""
    note_file = note_dir / "test.txt"
    note_file.write_text("Test note with #tag1 #tag2")

    parser = BearParser(note_dir)
    parser.parse_directory()
    maybe_notes = parser._notes
    assert maybe_notes is not None
    notes = maybe_notes

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "test"
    assert note.content == "Test note with #tag1 #tag2"
    assert set(note.tags) == {"tag1", "tag2"}
    assert note.attachments == []

    # Convert to docling document
    doc = note.to_docling()
    assert doc.name == "test"
    assert doc.content == "Test note with #tag1 #tag2"
    assert set(doc.tags) == {"tag1", "tag2"}


def test_process_note_with_date(note_dir: Path) -> None:
    """Test note processing with date in filename."""
    note_file = note_dir / "20240101 - Test Note.txt"
    note_file.write_text("Test note content")

    parser = BearParser(note_dir)
    parser.parse_directory()
    maybe_notes = parser._notes
    assert maybe_notes is not None
    notes = maybe_notes

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "Test Note"
    assert note.date.strftime("%Y%m%d") == "20240101"

    # Convert to docling document
    doc = note.to_docling()
    assert doc.name == "Test Note"
    assert doc.content == "Test note content"
    assert doc.date.strftime("%Y%m%d") == "20240101"


def test_process_note_invalid_file(note_dir: Path) -> None:
    """Test processing an invalid note file."""
    note_file = note_dir / "test.txt"
    note_file.write_text("")

    parser = BearParser(note_dir)
    parser.parse_directory()
    maybe_notes = parser._notes
    assert maybe_notes is not None
    notes = maybe_notes

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "test"
    assert note.content == ""
    assert note.tags == []
    assert note.attachments == []

    # Convert to docling document
    doc = note.to_docling()
    assert doc.name == "test"
    assert doc.content == ""
    assert doc.tags == []


def test_process_multiple_notes(note_dir: Path) -> None:
    """Test processing multiple notes."""
    # Create test notes
    (note_dir / "20240101 - Note 1.txt").write_text("Note 1 content #tag1")
    (note_dir / "20240102 - Note 2.txt").write_text("Note 2 content #tag2")
    (note_dir / "Note 3.txt").write_text("Note 3 content #tag3")

    parser = BearParser(note_dir)
    parser.parse_directory()
    maybe_notes = parser._notes
    assert maybe_notes is not None
    notes = maybe_notes

    assert len(notes) == 3

    # Check each note
    for note in notes:
        if note.title == "Note 1":
            assert note.content == "Note 1 content #tag1"
            assert note.tags == ["tag1"]
            assert note.date.strftime("%Y%m%d") == "20240101"
        elif note.title == "Note 2":
            assert note.content == "Note 2 content #tag2"
            assert note.tags == ["tag2"]
            assert note.date.strftime("%Y%m%d") == "20240102"
        elif note.title == "Note 3":
            assert note.content == "Note 3 content #tag3"
            assert note.tags == ["tag3"]
            assert isinstance(note.date, datetime)
        else:
            pytest.fail(f"Unexpected note title: {note.title}")

        # Convert to docling document
        doc = note.to_docling()
        assert doc.name == note.title
        assert doc.content == note.content
        assert doc.tags == note.tags
