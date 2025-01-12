"""Tests for Bear note parser."""

import pytest
from pathlib import Path
from collections.abc import Generator

from nova.ingestion.bear import BearParser


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

    parser = BearParser()
    parser.process_notes(str(note_dir), str(note_dir))

    assert (note_dir / "test.txt").exists()
    assert (note_dir / "test.txt").read_text() == "Test note content"


def test_process_note_with_tags(note_dir: Path) -> None:
    """Test note processing with tags."""
    note_file = note_dir / "test.txt"
    note_file.write_text("Test note with #tag1 #tag2")

    parser = BearParser()
    parser.process_notes(str(note_dir), str(note_dir))

    assert (note_dir / "test.txt").exists()
    assert (note_dir / "test.txt").read_text() == "Test note with #tag1 #tag2"


def test_process_note_with_output(note_dir: Path) -> None:
    """Test note processing with output directory."""
    note_file = note_dir / "test.txt"
    note_file.write_text("Test note content")

    output_dir = note_dir / "output"
    output_dir.mkdir()

    parser = BearParser()
    parser.process_notes(str(note_dir), str(output_dir))

    assert (output_dir / "test.txt").exists()
    assert (output_dir / "test.txt").read_text() == "Test note content"


def test_process_note_invalid_file(note_dir: Path) -> None:
    """Test processing an invalid note file."""
    note_file = note_dir / "test.txt"
    note_file.write_text("")

    parser = BearParser()
    parser.process_notes(str(note_dir), str(note_dir))

    assert (note_dir / "test.txt").exists()
    assert (note_dir / "test.txt").read_text() == ""
