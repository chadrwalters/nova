"""Unit tests for note resource handler."""

from pathlib import Path

import pytest
from nova.bear_parser.parser import BearAttachment, BearNote, BearParser
from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceError, ResourceType


class MockBearParser(BearParser):
    """Mock Bear parser for testing."""

    def __init__(self, notes_dir: Path) -> None:
        """Initialize mock parser."""
        super().__init__(notes_dir)
        self._notes: list[BearNote] = [
            BearNote(
                title="test1",
                content="Test note 1 content",
                tags=["tag1", "tag2"],
                attachments=[],
                metadata={"created": "2024-01-01"},
            ),
            BearNote(
                title="test2",
                content="Test note 2 content",
                tags=["tag2"],
                attachments=[
                    BearAttachment(
                        path=Path("test.png"), metadata={"type": "image/png"}
                    )
                ],
                metadata={"created": "2024-01-02"},
            ),
        ]
        self._content = {"test1": "Test note 1 content", "test2": "Test note 2 content"}
        self._tags: set[str] = {"tag1", "tag2"}

    def parse_directory(self) -> list[BearNote]:
        """Return mock notes."""
        if not self._notes:
            return []
        return self._notes

    def read(self, note_id: str) -> str:
        """Return mock note content."""
        if note_id not in self._content:
            raise FileNotFoundError(f"Note not found: {note_id}")
        return self._content[note_id]

    def count_notes(self) -> int:
        """Return number of notes."""
        if not self._notes:
            return 0
        return len(self._notes)

    def count_tags(self) -> int:
        """Return number of tags."""
        return len(self._tags)


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Create temporary notes directory."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    return notes_dir


@pytest.fixture
def note_store(notes_dir: Path) -> BearParser:
    """Create mock note store."""
    return MockBearParser(notes_dir)


@pytest.fixture
def note_handler(note_store: BearParser) -> NoteHandler:
    """Create note handler."""
    return NoteHandler(note_store)


def test_initialization(note_handler: NoteHandler) -> None:
    """Test note handler initialization."""
    metadata = note_handler.get_metadata()
    assert metadata["id"] == "notes"
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["version"] == "0.1.0"
    assert "modified" in metadata
    assert "attributes" in metadata
    assert isinstance(metadata["attributes"], dict)
    assert "total_notes" in metadata["attributes"]
    assert "total_tags" in metadata["attributes"]
    assert metadata["attributes"]["total_notes"] == 2
    assert metadata["attributes"]["total_tags"] == 2


def test_get_note_metadata(note_handler: NoteHandler) -> None:
    """Test getting note metadata."""
    metadata = note_handler.get_note_metadata("test1")
    assert metadata["id"] == "test1"
    assert metadata["title"] == "test1"
    assert metadata["tags"] == ["tag1", "tag2"]
    assert metadata["has_attachments"] is False
    assert metadata["metadata"] == {"created": "2024-01-01"}
    assert metadata["content_length"] == len("Test note 1 content")


def test_get_note_metadata_not_found(note_handler: NoteHandler) -> None:
    """Test getting metadata for non-existent note."""
    with pytest.raises(ResourceError, match="Note not found: nonexistent"):
        note_handler.get_note_metadata("nonexistent")


def test_get_note_content(note_handler: NoteHandler) -> None:
    """Test getting note content."""
    content = note_handler.get_note_content("test1")
    assert content == "Test note 1 content"


def test_get_note_content_streaming(note_handler: NoteHandler) -> None:
    """Test getting note content with streaming."""
    content = note_handler.get_note_content("test1", start=0, end=4)
    assert content == "Test"


def test_get_note_content_invalid_range(note_handler: NoteHandler) -> None:
    """Test getting note content with invalid range."""
    with pytest.raises(ResourceError, match="Invalid content range"):
        note_handler.get_note_content("test1", start=-1, end=100)


def test_get_note_content_not_found(note_handler: NoteHandler) -> None:
    """Test getting content for non-existent note."""
    with pytest.raises(ResourceError, match="Failed to get note content"):
        note_handler.get_note_content("nonexistent")


def test_list_notes(note_handler: NoteHandler) -> None:
    """Test listing all notes."""
    notes = note_handler.list_notes()
    assert len(notes) == 2
    assert notes[0]["id"] == "test1"
    assert notes[1]["id"] == "test2"


def test_list_notes_with_tag(note_handler: NoteHandler) -> None:
    """Test listing notes filtered by tag."""
    notes = note_handler.list_notes(tag="tag1")
    assert len(notes) == 1
    assert notes[0]["id"] == "test1"


def test_validate_access(note_handler: NoteHandler) -> None:
    """Test access validation."""
    assert note_handler.validate_access("read")
    assert note_handler.validate_access("write")
    assert note_handler.validate_access("delete")
    assert not note_handler.validate_access("invalid")


def test_change_notification(note_handler: NoteHandler) -> None:
    """Test change notifications."""
    changes: list[bool] = []
    note_handler.on_change(lambda: changes.append(True))

    # Force a change notification
    note_handler._notify_change()

    # Verify changes
    assert len(changes) == 1

    # Verify cache invalidation
    metadata = note_handler.get_metadata()
    assert metadata["attributes"]["total_notes"] == 2
