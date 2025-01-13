"""Attachment resource handler implementation."""

import json
from pathlib import Path
from typing import Any, TypedDict, cast
from collections.abc import Callable
import mimetypes
import threading
import time


from nova.server.attachments import AttachmentStore
from nova.server.types import (
    ResourceError,
    ResourceHandler,
    ResourceMetadata,
    ResourceType,
)


class AttachmentAttributes(TypedDict):
    """Attachment attributes type."""

    total_attachments: int
    supported_formats: list[str]
    storage_path: str


class AttachmentMetadata(TypedDict):
    """Attachment metadata type."""

    id: str
    type: str
    name: str
    version: str
    modified: float
    attributes: AttachmentAttributes


class AttachmentInfo(TypedDict):
    """Attachment information type."""

    id: str
    name: str
    mime_type: str
    size: int
    created: str
    modified: str
    ocr_status: str
    ocr_confidence: float | None
    metadata: dict[str, Any]


class AttachmentResult(TypedDict):
    """Attachment result type."""

    id: str
    mime_type: str
    ocr_status: str
    metadata: dict[str, Any]


class AttachmentHandler(ResourceHandler):
    """Handler for attachment resource."""

    SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "attachment_resource.json"
    VERSION = "0.1.0"
    RESOURCE_ID = "attachment-handler"
    SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "pdf", "tiff"]
    VALID_OPERATIONS = ["read", "write", "delete"]

    def __init__(self, attachment_store: AttachmentStore) -> None:
        """Initialize attachment handler.

        Args:
            attachment_store: Attachment store instance to manage
        """
        self._store = attachment_store
        self._change_callbacks: list[Callable[[], None]] = []
        self._id_counter = 0
        self._id_lock = threading.Lock()

        # Load schema
        with open(self.SCHEMA_PATH) as f:
            self._schema = json.load(f)

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata.

        Returns:
            Resource metadata

        Raises:
            ResourceError: If getting metadata fails
        """
        try:
            metadata: ResourceMetadata = {
                "id": "attachment-handler",
                "type": ResourceType.ATTACHMENT,
                "name": "Attachment Handler",
                "version": "1.0.0",
                "modified": time.time(),
                "attributes": {
                    "total_attachments": self._store.count_attachments(),
                    "supported_formats": list(self._store.mime_types),
                    "storage_path": str(self._store.storage_path),
                },
            }
            return metadata
        except Exception as e:
            raise ResourceError(f"Failed to get metadata: {str(e)}")

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation.

        Args:
            operation: Operation to validate

        Returns:
            True if access is allowed, False otherwise
        """
        return operation in self.VALID_OPERATIONS

    def _generate_unique_id(self) -> str:
        """Generate a unique attachment ID.

        Returns:
            str: Unique ID
        """
        with self._id_lock:
            self._id_counter += 1
            return f"attachment-{self._id_counter}"

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Add an attachment.

        Args:
            file_path: Path to the file to attach
            metadata: Optional metadata to associate with the attachment

        Returns:
            Attachment info dictionary

        Raises:
            ResourceError: If attachment fails
        """
        try:
            if not file_path.exists():
                raise ResourceError("Failed to add attachment: File not found")

            # Check file extension
            extension = file_path.suffix.lower().lstrip(".")
            if not extension:
                raise ResourceError("Failed to add attachment: Unknown file type")

            if extension not in self.SUPPORTED_FORMATS:
                raise ResourceError(
                    f"Failed to add attachment: Unsupported file format: {extension}"
                )

            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                raise ResourceError("Failed to add attachment: Unknown file type")

            if not any(
                mime_type.startswith(f"image/{fmt}") or mime_type == "application/pdf"
                for fmt in self.SUPPORTED_FORMATS
            ):
                raise ResourceError(
                    f"Failed to add attachment: Unsupported MIME type: {mime_type}"
                )

            # Add attachment to store
            info = self._store.add_attachment(file_path, metadata or {})
            if info is None:
                raise ResourceError(f"Failed to add attachment: {file_path}")

            # Get full attachment info
            attachment_id = info["id"]
            result = self._store.get_attachment_info(attachment_id)
            if result is None:
                raise ResourceError(f"Failed to get attachment info: {attachment_id}")

            self._notify_change()
            return result

        except ResourceError:
            raise
        except Exception as e:
            raise ResourceError(f"Failed to add attachment: {str(e)}")

    def get_attachment(self, attachment_id: str) -> AttachmentInfo:
        """Get attachment information.

        Args:
            attachment_id: Unique identifier for attachment

        Returns:
            Dictionary containing attachment information

        Raises:
            ResourceError: If getting attachment fails
        """
        try:
            info = self._store.get_attachment_info(attachment_id)
            if info is None:
                raise ResourceError("Attachment not found")
            return cast(AttachmentInfo, info)
        except Exception as e:
            raise ResourceError(f"Failed to get attachment: {str(e)}")

    def update_attachment(
        self, attachment_id: str, metadata: dict[str, Any]
    ) -> AttachmentInfo:
        """Update attachment metadata.

        Args:
            attachment_id: Unique identifier for attachment
            metadata: New metadata for the attachment

        Returns:
            Updated attachment information

        Raises:
            ResourceError: If updating attachment fails
        """
        try:
            info = self._store.update_attachment_metadata(attachment_id, metadata)
            if info is None:
                raise ValueError(f"Attachment not found: {attachment_id}")
            self._notify_change()
            return cast(AttachmentInfo, info)
        except Exception as e:
            raise ResourceError(f"Failed to update attachment: {str(e)}")

    def delete_attachment(self, attachment_id: str) -> None:
        """Delete an attachment.

        Args:
            attachment_id: Unique identifier for attachment

        Raises:
            ResourceError: If deleting attachment fails
        """
        try:
            if not self._store.delete_attachment(attachment_id):
                raise ValueError(f"Attachment not found: {attachment_id}")
            self._notify_change()
        except Exception as e:
            raise ResourceError(f"Failed to delete attachment: {str(e)}")

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback.

        Args:
            callback: Function to call when resource changes
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify registered callbacks of change."""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                # Log error but continue notifying other callbacks
                print(f"Error in change callback: {str(e)}")

    def list_attachments(
        self,
        filter_mime_type: str | None = None,
        filter_ocr_status: str | None = None,
    ) -> list[AttachmentResult]:
        """List attachments with optional filters.

        Args:
            filter_mime_type: Optional MIME type to filter by
            filter_ocr_status: Optional OCR status to filter by

        Returns:
            List of attachment results

        Raises:
            ResourceError: If listing attachments fails
        """
        try:
            results = self._store.list_attachments()
            if filter_mime_type:
                results = [r for r in results if r["mime_type"] == filter_mime_type]
            if filter_ocr_status:
                results = [r for r in results if r["ocr_status"] == filter_ocr_status]
            return results
        except Exception as e:
            raise ResourceError(f"Failed to list attachments: {str(e)}")
