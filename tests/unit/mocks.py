"""Mock classes for testing."""
from pathlib import Path
from typing import Any

from nova.bear_parser.parser import BearNote, BearParser
from nova.server.types import ResourceError


class MockBearParser(BearParser):
    """Mock Bear parser."""

    def __init__(self) -> None:
        """Initialize mock parser."""
        self._notes: list[BearNote] = []
        self._tags: set[str] = set()

    def parse_directory(self) -> list[BearNote]:
        """Parse directory.

        Returns:
            List of notes
        """
        return self._notes

    def read(self, note_id: str) -> str:
        """Read note content.

        Args:
            note_id: Note ID

        Returns:
            Note content
        """
        return ""

    def count_notes(self) -> int:
        """Get total number of notes.

        Returns:
            Total number of notes
        """
        return len(self._notes)

    def count_tags(self) -> int:
        """Get total number of tags.

        Returns:
            Total number of tags
        """
        return len(self._tags)


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
            "ocr_status": "pending",
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
        filter_ocr_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List attachments with optional filters."""
        attachments = list(self._attachments.values())
        if filter_mime_type:
            attachments = [a for a in attachments if a["mime_type"] == filter_mime_type]
        if filter_ocr_status:
            attachments = [
                a for a in attachments if a["ocr_status"] == filter_ocr_status
            ]
        return attachments

    def count_attachments(self) -> int:
        """Get total number of attachments."""
        return len(self._attachments)
