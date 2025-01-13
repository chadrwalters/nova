"""Unit tests for note resource handler."""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from nova.bear_parser.parser import BearNote, BearParser
from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType


class MockBearParser(BearParser):
    """Mock Bear parser for testing."""

    def __init__(self, input_dir: Path | str) -> None:
        """Initialize parser.

        Args:
            input_dir: Input directory containing Bear notes
        """
        super().__init__(input_dir)
        now = datetime.now()
        self._notes = [
            BearNote(
                title="Test Note 1",
                date=now,
                content="Test content 1",
                tags=["tag1", "tag2"],
                attachments=[],
                metadata={"original_file": "test1.md"},
            ),
            BearNote(
                title="Test Note 2",
                date=now,
                content="Test content 2",
                tags=["tag2", "tag3"],
                attachments=[],
                metadata={"original_file": "test2.md"},
            ),
        ]

    def process_notes(self, output_dir: Path | None = None) -> list[BearNote]:
        """Mock process_notes method.

        Args:
            output_dir: Optional output directory for processed notes

        Returns:
            List of processed notes
        """
        return self._notes


@pytest.fixture
def note_handler(tmp_path: Path) -> NoteHandler:
    """Create note handler fixture.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Note handler instance
    """
    # Create test notes directory
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    # Create test note files
    (notes_dir / "test1.md").write_text("Test content 1")
    (notes_dir / "test2.md").write_text("Test content 2")

    # Initialize handler with mock parser
    parser = MockBearParser(notes_dir)
    handler = NoteHandler(parser)
    return handler


def test_init_handler(tmp_path: Path) -> None:
    """Test handler initialization.

    Args:
        tmp_path: Temporary directory path
    """
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    parser = MockBearParser(notes_dir)
    handler = NoteHandler(parser)
    metadata = handler.get_metadata()
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["version"] == NoteHandler.VERSION


def test_get_note_metadata(note_handler: NoteHandler) -> None:
    """Test getting note metadata.

    Args:
        note_handler: Note handler fixture
    """
    metadata = note_handler.get_note_metadata("Test Note 1")
    assert metadata == {
        "title": "Test Note 1",
        "tags": ["tag1", "tag2"],
        "original_file": "test1.md",
    }

    with pytest.raises(HTTPException) as exc:
        note_handler.get_note_metadata("Non-existent Note")
    assert exc.value.status_code == 404


def test_get_note_content(note_handler: NoteHandler) -> None:
    """Test getting note content.

    Args:
        note_handler: Note handler fixture
    """
    content = note_handler.get_note_content("Test Note 1")
    assert content == "Test content 1"

    with pytest.raises(HTTPException) as exc:
        note_handler.get_note_content("Non-existent Note")
    assert exc.value.status_code == 404


def test_list_notes(note_handler: NoteHandler) -> None:
    """Test listing notes.

    Args:
        note_handler: Note handler fixture
    """
    notes = note_handler.list_notes()
    assert len(notes) == 2
    assert notes[0]["title"] == "Test Note 1"
    assert notes[1]["title"] == "Test Note 2"


def test_validate_access(note_handler: NoteHandler) -> None:
    """Test access validation.

    Args:
        note_handler: Note handler fixture
    """
    # Valid note title should not raise exception
    note_handler.validate_access("Test Note 1")

    # Invalid note title should raise 404
    with pytest.raises(HTTPException) as exc:
        note_handler.validate_access("Non-existent Note")
    assert exc.value.status_code == 404
