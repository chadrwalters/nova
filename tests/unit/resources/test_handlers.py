"""Tests for resource handlers."""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from nova.bear_parser.parser import BearNote, BearParser
from nova.server.attachments import AttachmentStore
from nova.server.resources.attachment import AttachmentHandler
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


class MockAttachmentStore(AttachmentStore):
    """Mock attachment store for testing."""

    def __init__(self, store_dir: Path) -> None:
        """Initialize store.

        Args:
            store_dir: Directory for storing attachments
        """
        super().__init__(store_dir)
        self._attachments: dict[str, bytes] = {}
        self._metadata: dict[str, dict] = {}

    def read(self, attachment_id: str) -> bytes:
        """Read attachment data.

        Args:
            attachment_id: Attachment ID

        Returns:
            Attachment data

        Raises:
            FileNotFoundError: If attachment not found
        """
        if attachment_id not in self._attachments:
            raise FileNotFoundError(f"Attachment not found: {attachment_id}")
        return self._attachments[attachment_id]

    def write(self, attachment_id: str, content: bytes) -> None:
        """Write attachment data.

        Args:
            attachment_id: Attachment ID
            content: Attachment data
        """
        self._attachments[attachment_id] = content
        if attachment_id not in self._metadata:
            self._metadata[attachment_id] = {
                "id": attachment_id,
                "name": attachment_id,
                "mime_type": "application/octet-stream",
                "size": len(content),
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat(),
                "metadata": {},
            }

    def get_attachment_info(self, attachment_id: str) -> dict | None:
        """Get attachment metadata.

        Args:
            attachment_id: Attachment ID

        Returns:
            Attachment metadata or None if not found
        """
        return self._metadata.get(attachment_id)

    def update_attachment_metadata(
        self, attachment_id: str, metadata: dict
    ) -> dict | None:
        """Update attachment metadata.

        Args:
            attachment_id: Attachment ID
            metadata: New metadata

        Returns:
            Updated metadata or None if not found
        """
        if attachment_id not in self._metadata:
            return None
        self._metadata[attachment_id]["metadata"].update(metadata)
        return self._metadata[attachment_id]

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete attachment.

        Args:
            attachment_id: Attachment ID

        Returns:
            True if deleted, False if not found
        """
        if attachment_id not in self._attachments:
            return False
        del self._attachments[attachment_id]
        del self._metadata[attachment_id]
        return True

    def list_attachments(self) -> list[dict]:
        """List all attachments.

        Returns:
            List of attachment metadata
        """
        return list(self._metadata.values())


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


@pytest.fixture
def attachment_handler(tmp_path: Path) -> AttachmentHandler:
    """Create attachment handler fixture.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Attachment handler instance
    """
    # Create test attachments directory
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()

    # Initialize handler with mock store
    store = MockAttachmentStore(attachments_dir)
    handler = AttachmentHandler(store)
    return handler


def test_note_handler_init(tmp_path: Path) -> None:
    """Test note handler initialization.

    Args:
        tmp_path: Temporary directory path
    """
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    parser = BearParser(notes_dir)
    handler = NoteHandler(parser)
    metadata = handler.get_metadata()
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["version"] == NoteHandler.VERSION


def test_note_handler_list_notes(note_handler: NoteHandler) -> None:
    """Test listing notes.

    Args:
        note_handler: Note handler fixture
    """
    notes = note_handler.list_notes()
    assert len(notes) == 2
    assert notes[0]["title"] == "Test Note 1"
    assert notes[1]["title"] == "Test Note 2"


def test_note_handler_get_metadata(note_handler: NoteHandler) -> None:
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


def test_attachment_handler_init(tmp_path: Path) -> None:
    """Test attachment handler initialization.

    Args:
        tmp_path: Temporary directory path
    """
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()

    store = MockAttachmentStore(attachments_dir)
    handler = AttachmentHandler(store)
    metadata = handler.get_metadata()
    assert metadata["type"] == ResourceType.ATTACHMENT
    assert metadata["version"] == AttachmentHandler.VERSION


def test_attachment_handler_get(attachment_handler: AttachmentHandler) -> None:
    """Test getting attachment.

    Args:
        attachment_handler: Attachment handler fixture
    """
    # Store test attachment
    test_data = b"Test attachment data"
    attachment_handler.add_attachment(
        Path("test.txt"), {"content": test_data.decode("utf-8")}
    )

    # Get attachment
    info = attachment_handler.get_attachment("test.txt")
    assert info["name"] == "test.txt"
    assert info["mime_type"] == "text/plain"

    with pytest.raises(HTTPException) as exc:
        attachment_handler.get_attachment("non-existent.txt")
    assert exc.value.status_code == 404
