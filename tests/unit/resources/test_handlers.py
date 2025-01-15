"""Tests for resource handlers."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from nova.stubs.docling import Document, DocumentConverter, InputFormat

from nova.server.attachments import AttachmentStore
from nova.server.resources.attachment import AttachmentHandler
from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType


class MockDocumentConverter(DocumentConverter):
    """Mock document converter for testing."""

    def __init__(self) -> None:
        """Initialize the mock converter."""
        super().__init__()
        self._documents: dict[str, Document] = {}
        self.input_dir = ".nova/test_input"

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        if str(path) == self.input_dir or str(path).endswith(self.input_dir):
            # Return a special document that contains all documents in its metadata
            listing_doc = Document("listing.md")
            listing_doc.metadata["documents"] = list(self._documents.values())
            return listing_doc

        if path.name not in self._documents:
            raise FileNotFoundError(f"File not found: {path}")
        return self._documents[path.name]

    def add_document(self, doc: Document) -> None:
        """Add a document to the mock store."""
        self._documents[doc.name] = doc


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
def notes_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for notes.

    Args:
        tmp_path: Temporary directory fixture

    Returns:
        Path to notes directory
    """
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    return notes_dir


@pytest.fixture
def note_handler(notes_dir: Path) -> NoteHandler:
    """Create a note handler for testing."""
    # Create test input directory
    test_input = notes_dir / ".nova" / "test_input"
    test_input.parent.mkdir(parents=True, exist_ok=True)
    test_input.mkdir(exist_ok=True)

    # Create test documents
    converter = MockDocumentConverter()
    docs = [
        Document("test1.md"),
        Document("test2.md"),
        Document("test3.md"),
    ]

    # Set up test1.md
    docs[0].text = "# Test Document 1\nTest content 1"
    docs[0].metadata = {
        "title": "Test Note 1",
        "format": InputFormat.MD,
        "tags": ["tag1", "tag2"],
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "date": datetime.now().isoformat(),
        "size": len(docs[0].text),
    }

    # Set up test2.md
    docs[1].text = "# Test Document 2\nTest content 2"
    docs[1].metadata = {
        "title": "Test Note 2",
        "format": InputFormat.MD,
        "tags": ["tag2", "tag3"],
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "date": datetime.now().isoformat(),
        "size": len(docs[1].text),
    }

    # Set up test3.md
    docs[2].text = "# Test Document 3\nTest content 3"
    docs[2].metadata = {
        "title": "Test Note 3",
        "format": InputFormat.MD,
        "tags": ["tag3", "tag4"],
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "date": datetime.now().isoformat(),
        "size": len(docs[2].text),
    }

    # Add documents to converter
    for doc in docs:
        converter._documents[doc.name] = doc

    # Create listing document
    listing = Document("listing.md")
    listing.metadata = {
        "format": InputFormat.MD,
        "documents": docs,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "date": datetime.now().isoformat(),
        "title": "Document Listing",
        "tags": [],
        "size": 0,
    }
    converter._documents[".nova/test_input"] = listing

    return NoteHandler(converter)


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

    converter = MockDocumentConverter()
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
    assert len(notes) == 4  # test1.md, test2.md, test3.md, listing.md
    assert all(note["type"] == ResourceType.NOTE for note in notes)
    assert all("title" in note["metadata"] for note in notes)
    assert all("date" in note["metadata"] for note in notes)
    assert all("format" in note["metadata"] for note in notes)
    assert all("modified" in note["metadata"] for note in notes)
    assert all("size" in note["metadata"] for note in notes)


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
