"""Unit tests for note resource handler."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from nova.stubs.docling import Document, DocumentConverter

from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType


class MockDocumentConverter(DocumentConverter):
    """Mock document converter for testing."""

    def __init__(self, input_dir: str) -> None:
        """Initialize mock document converter."""
        self.input_dir = input_dir
        doc = Document("test1.md")
        doc.text = "Test note content"
        doc.metadata = {
            "title": "Test Note 1",
            "date": "2024-01-01T00:00:00",
            "tags": ["test1", "test2"],
            "format": "text",
            "modified": "2024-01-01T00:00:00",
            "size": 17,
        }
        doc.pictures = []
        self.doc = doc

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        if path.name == "nonexistent.md":
            raise FileNotFoundError(f"File not found: {path}")
        return self.doc

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents."""
        return [self.doc]  # Always return a document for testing


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for notes."""
    notes = tmp_path / "notes"
    notes.mkdir(exist_ok=True)
    test_file = notes / "test1.md"
    test_file.write_text("Test note content")
    return notes


@pytest.fixture
def note_handler(notes_dir: Path) -> NoteHandler:
    """Create a note handler for testing."""
    converter = MockDocumentConverter(str(notes_dir))
    return NoteHandler(converter)


def test_init_handler(notes_dir: Path) -> None:
    """Test initializing the handler."""
    converter = MockDocumentConverter(str(notes_dir))
    handler = NoteHandler(converter)
    assert handler is not None


def test_get_note_metadata(note_handler: NoteHandler) -> None:
    """Test getting note metadata."""
    metadata = note_handler.get_metadata()
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["version"] == "1.0.0"


def test_get_note_content(note_handler: NoteHandler) -> None:
    """Test getting note content."""
    content = note_handler.get_note_content("test1.md")
    assert content == "Test note content"


def test_list_notes(note_handler: NoteHandler) -> None:
    """Test listing notes."""
    notes = note_handler.list_notes()
    assert len(notes) == 1
    note = notes[0]
    assert note["name"] == "test1.md"
    assert note["title"] == "Test Note 1"
    assert note["tags"] == ["test1", "test2"]
    assert note["modified"] == "2024-01-01T00:00:00"
    assert note["size"] == 17


def test_validate_access(note_handler: NoteHandler) -> None:
    """Test validating note access."""
    with pytest.raises(HTTPException) as exc_info:
        note_handler.get_note_content("nonexistent.md")
    assert exc_info.value.status_code == 404


def test_cleanup(note_handler: NoteHandler) -> None:
    """Test cleanup."""
    note_handler.cleanup()


def test_on_change(note_handler: NoteHandler) -> None:
    """Test change notification."""

    def callback() -> None:
        pass

    note_handler.on_change(callback)
