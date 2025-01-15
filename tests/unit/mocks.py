"""Mock classes for testing."""
from datetime import datetime
from pathlib import Path
from typing import Any

from nova.stubs.docling import Document, DocumentConverter, InputFormat
from nova.server.types import ResourceError


class MockDocumentConverter(DocumentConverter):
    """Mock document converter for testing."""

    def __init__(self) -> None:
        """Initialize mock converter."""
        self._documents: dict[str, Document] = {}
        self._create_test_documents()

    def _create_test_documents(self) -> None:
        """Create test documents."""
        # Basic document
        basic_doc = Document("test1.md")
        basic_doc.text = "# Test Document 1\n\nBasic test content"
        basic_doc.metadata = {
            "title": "Test Document 1",
            "date": datetime.now().isoformat(),
            "tags": ["test", "basic"],
            "format": "markdown",
            "modified": datetime.now().isoformat(),
            "size": 35,
        }
        self._documents[basic_doc.name] = basic_doc

        # Document with attachments
        attachment_doc = Document("test2.md")
        attachment_doc.text = "# Test Document 2\n\n![Image](test.png)\n\nContent with image"
        attachment_doc.metadata = {
            "title": "Test Document 2",
            "date": datetime.now().isoformat(),
            "tags": ["test", "attachments"],
            "format": "markdown",
            "modified": datetime.now().isoformat(),
            "size": 72,
        }
        attachment_doc.pictures = [{
            "image": {
                "uri": "test.png",
                "mime_type": "image/png",
                "size": 1024
            }
        }]
        self._documents[attachment_doc.name] = attachment_doc

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        if path.name not in self._documents:
            raise FileNotFoundError(f"File not found: {path}")
        return self._documents[path.name]

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents."""
        return [self.convert_file(path) for path in paths]

    def count_documents(self) -> int:
        """Get total number of documents."""
        return len(self._documents)


class MockAttachmentStore:
    """Mock attachment store for testing."""

    def __init__(self) -> None:
        """Initialize mock store."""
        super().__init__()
        self._attachments: dict[str, dict[str, Any]] = {}
        self._mime_types = {"image/png", "image/jpeg", "application/pdf"}
        self._storage_path = Path("/test/store")

    @property
    def mime_types(self) -> set[str]:
        """Get supported MIME types."""
        return self._mime_types

    @property
    def storage_path(self) -> Path:
        """Get storage path."""
        return self._storage_path

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Add an attachment."""
        attachment_id = "test-id"
        self._attachments[attachment_id] = {
            "id": attachment_id,
            "mime_type": "image/png",
            "metadata": metadata or {},
        }
        return self._attachments[attachment_id]

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any]:
        """Get attachment info."""
        if attachment_id not in self._attachments:
            raise ResourceError("Attachment not found")
        return self._attachments[attachment_id]

    def list_attachments(
        self,
        filter_mime_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List attachments with optional filters."""
        attachments = list(self._attachments.values())
        if filter_mime_type:
            attachments = [a for a in attachments if a["mime_type"] == filter_mime_type]
        return attachments

    def count_attachments(self) -> int:
        """Get total number of attachments."""
        return len(self._attachments)
