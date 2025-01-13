"""Test resource handlers."""

from pathlib import Path
from typing import Any
import threading
import time

from nova.bear_parser.parser import BearNote, BearParser
from nova.bear_parser.ocr import EasyOcrModel
from nova.server.attachments import AttachmentStore
from nova.server.resources.note import NoteHandler
from nova.server.resources.attachment import AttachmentHandler
from nova.server.resources.ocr import OCRHandler
from nova.server.types import ResourceError, ResourceType


class MockBearParser(BearParser):
    """Mock Bear parser."""

    def __init__(self) -> None:
        """Initialize mock parser."""
        self._notes: list[BearNote] = [
            BearNote(
                title="Test Note 1",
                content="Test content 1",
                tags=["tag1"],
                attachments=[],
                metadata={},
            ),
            BearNote(
                title="Test Note 2",
                content="Test content 2",
                tags=["tag1", "tag2"],
                attachments=[],
                metadata={},
            ),
        ]
        self._tags: set[str] = {"tag1", "tag2"}

    def parse_directory(self) -> list[BearNote]:
        """Parse directory."""
        return self._notes

    def read(self, note_id: str) -> str:
        """Read note content."""
        return ""

    def count_notes(self) -> int:
        """Get total number of notes."""
        return len(self._notes)

    def count_tags(self) -> int:
        """Get total number of tags."""
        return len(self._tags)


class MockAttachmentStore(AttachmentStore):
    """Mock attachment store."""

    def __init__(self) -> None:
        """Initialize mock store."""
        self._attachments: dict[str, dict[str, Any]] = {}
        self._next_id = 1
        self._id_lock = threading.Lock()  # Add lock for thread safety
        self._mime_types: set[str] = {"image/png", "image/jpeg", "application/pdf"}

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Mock add attachment."""
        with self._id_lock:  # Use lock for thread-safe ID generation
            attachment_id = str(self._next_id)
            self._next_id += 1
            self._attachments[attachment_id] = {
                "id": attachment_id,
                "mime_type": "image/png",
                "ocr_status": "pending",
                "metadata": metadata or {},
                "size": 1000,
                "created": time.time(),
                "modified": time.time(),
                "name": file_path.name,
            }
            return self._attachments[attachment_id]

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any]:
        """Mock get attachment info."""
        if attachment_id not in self._attachments:
            raise ResourceError(f"Attachment not found: {attachment_id}")
        return self._attachments[attachment_id]

    def list_attachments(self) -> list[dict[str, Any]]:
        """Mock list attachments."""
        return list(self._attachments.values())

    def count_attachments(self) -> int:
        """Mock count attachments."""
        return len(self._attachments)

    @property
    def storage_path(self) -> Path:
        """Mock storage path."""
        return Path("/test/store")


class MockOcrModel(EasyOcrModel):
    """Mock OCR model."""

    def process(self, image_path: str) -> dict[str, Any]:
        """Process image."""
        return {
            "text": "test",
            "confidence": 0.95,
            "regions": [],
            "language": "en",
            "processing_time": 0.1,
        }


def test_note_handler() -> None:
    """Test note handler."""
    store = MockBearParser()
    handler = NoteHandler(store)

    # Test metadata
    metadata = handler.get_metadata()
    assert metadata["id"] == "notes"
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["name"] == "Note Store"


def test_attachment_handler() -> None:
    """Test attachment handler."""
    store = MockAttachmentStore()
    handler = AttachmentHandler(store)

    # Test metadata
    metadata = handler.get_metadata()
    assert metadata["id"] == "attachment-handler"
    assert metadata["type"] == ResourceType.ATTACHMENT.name
    assert metadata["version"] == "1.0.0"
    assert "modified" in metadata
    assert "attributes" in metadata
    assert isinstance(metadata["attributes"], dict)
    assert "total_attachments" in metadata["attributes"]
    assert "supported_formats" in metadata["attributes"]
    assert "storage_path" in metadata["attributes"]


def test_ocr_handler() -> None:
    """Test OCR handler."""
    engine = MockOcrModel()
    handler = OCRHandler(engine)

    # Test metadata
    metadata = handler.get_metadata()
    assert metadata["id"] == "ocr-handler"
    assert metadata["type"] == ResourceType.OCR.name
    assert metadata["version"] == "0.1.0"
    assert "modified" in metadata
    assert "attributes" in metadata
    assert isinstance(metadata["attributes"], dict)
    assert "engine" in metadata["attributes"]
    assert "languages" in metadata["attributes"]
    assert "confidence_threshold" in metadata["attributes"]
    assert "cache_enabled" in metadata["attributes"]
    assert "cache_size" in metadata["attributes"]
