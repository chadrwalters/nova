"""Attachment resource implementation."""

from pathlib import Path
from typing import Any, Protocol, TypedDict
import time

from nova.server.types import ResourceType, ResourceMetadata


class AttachmentAttributes(TypedDict):
    """Attachment attributes."""

    id: str
    name: str
    mime_type: str
    size: int
    created: str
    modified: str


class AttachmentMetadata(TypedDict):
    """Attachment metadata."""

    metadata: dict[str, Any]


class AttachmentInfo(AttachmentAttributes, AttachmentMetadata):
    """Attachment information."""

    pass


class AttachmentResult(AttachmentInfo):
    """Attachment result."""

    pass


class AttachmentStoreProtocol(Protocol):
    """Protocol for attachment store."""

    def list_attachments(self) -> list[dict[str, Any]]:
        ...

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        ...

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any] | None:
        ...

    def update_attachment_metadata(
        self, attachment_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        ...

    def delete_attachment(self, attachment_id: str) -> bool:
        ...

    def count_attachments(self) -> int:
        ...


class AttachmentHandler:
    """Handler for attachment resources."""

    def __init__(self, store: AttachmentStoreProtocol) -> None:
        """Initialize attachment handler.

        Args:
            store: Attachment store instance
        """
        self._store = store

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return {
            "id": "attachments",
            "type": ResourceType.ATTACHMENT,
            "name": "Attachment Store",
            "version": "1.0.0",
            "modified": time.time(),
            "attributes": {
                "total_attachments": self._store.count_attachments(),
                "mime_types": [
                    "png",
                    "jpg",
                    "jpeg",
                    "pdf",
                    "tiff",
                ],  # Hardcoded for now
            },
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        pass  # Nothing to clean up
