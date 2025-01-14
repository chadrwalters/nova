"""Tests for resource handlers."""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from nova.stubs.docling import Document, DocumentConverter

from nova.server.attachments import AttachmentStore
from nova.server.resources.attachment import AttachmentHandler
from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType


class MockDocumentConverter(DocumentConverter):
    """Mock document converter for testing."""

    def __init__(self, input_dir: str) -> None:
        """Initialize converter.

        Args:
            input_dir: Input directory containing notes
        """
        self.input_dir = input_dir
        now = datetime.now()
        self._notes = [
            self._create_document(
                "test1.md", "Test Note 1", "Test content 1", ["tag1", "tag2"], now
            ),
            self._create_document(
                "test2.md", "Test Note 2", "Test content 2", ["tag2", "tag3"], now
            ),
        ]

    def _create_document(
        self, name: str, title: str, content: str, tags: list[str], date: datetime
    ) -> Document:
        """Create a test document.

        Args:
            name: Document name
            title: Document title
            content: Document content
            tags: Document tags
            date: Document date

        Returns:
            Document instance
        """
        doc = Document(name)
        doc.text = content
        doc.metadata = {
            "title": title,
            "date": date.isoformat(),
            "tags": tags,
            "format": "text",
        }
        doc.pictures = []
        return doc

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document.

        Args:
            path: Path to file

        Returns:
            Document instance

        Raises:
            FileNotFoundError: If file not found
        """
        for note in self._notes:
            if note.name == path.name:
                return note
        raise FileNotFoundError(f"File not found: {path}")

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents.

        Args:
            paths: List of file paths

        Returns:
            List of documents
        """
        return [self.convert_file(path) for path in paths]


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

    # Initialize handler with mock converter
    converter = MockDocumentConverter(str(notes_dir))
    handler = NoteHandler(converter)
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

    converter = MockDocumentConverter(str(notes_dir))
    handler = NoteHandler(converter)
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
    metadata = note_handler.get_note_metadata("test1.md")
    assert metadata["name"] == "test1.md"
    assert metadata["title"] == "Test Note 1"
    assert metadata["tags"] == ["tag1", "tag2"]

    with pytest.raises(HTTPException) as exc:
        note_handler.get_note_metadata("nonexistent.md")
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
    assert metadata["version"] == "1.0.0"  # Version is hardcoded in AttachmentHandler
