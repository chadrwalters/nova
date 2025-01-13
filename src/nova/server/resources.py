"""Resource handlers for the Nova MCP server."""

import logging
import time
from typing import Any
from collections.abc import Callable

from nova.server.attachments import AttachmentStore
from nova.server.types import (
    ResourceHandler,
    ResourceMetadata,
    ResourceType,
)
from nova.vector_store import VectorStore

logger = logging.getLogger(__name__)


class BaseResourceHandler(ResourceHandler):
    """Base class for resource handlers."""

    def __init__(self) -> None:
        """Initialize base handler."""
        self._change_callback: Callable[[], None] | None = None
        self._last_modified: float = time.time()

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback."""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._change_callback = callback

    def _notify_change(self) -> None:
        """Notify registered callback of change."""
        if self._change_callback:
            try:
                self._change_callback()
            except Exception as e:
                logger.error("Error in change callback: %s", str(e))
        self._last_modified = time.time()

    @property
    def last_modified(self) -> float:
        """Get last modified timestamp."""
        return self._last_modified


class VectorStoreHandler(BaseResourceHandler):
    """Handler for vector store resource."""

    def __init__(self, vector_store: VectorStore):
        """Initialize vector store handler.

        Args:
            vector_store: Vector store instance
        """
        super().__init__()
        self._vector_store = vector_store

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return {
            "id": "vector-store",
            "type": ResourceType.VECTOR_STORE,
            "name": "Vector Store",
            "version": "1.0.0",  # TODO: Get from vector store
            "modified": self.last_modified,
            "attributes": {
                "count": 0,  # TODO: Get from vector store
                "store_dir": str(self._vector_store._store_dir),
            },
        }

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation."""
        valid_ops = {"search", "add", "remove", "clear"}
        return operation in valid_ops


class NoteHandler(BaseResourceHandler):
    """Handler for note resource."""

    def __init__(self, note_store: Any):  # TODO: Add proper type
        """Initialize note handler.

        Args:
            note_store: Note storage instance
        """
        super().__init__()
        self._note_store = note_store

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return {
            "id": "notes",
            "type": ResourceType.NOTE,
            "name": "Notes",
            "version": "1.0.0",  # TODO: Get from note store
            "modified": self.last_modified,
            "attributes": {
                "count": 0,  # TODO: Get from note store
                "formats": ["markdown"],
            },
        }

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation."""
        valid_ops = {"read", "write", "delete"}
        return operation in valid_ops


class AttachmentHandler(BaseResourceHandler):
    """Handler for attachment resource."""

    def __init__(self, attachment_store: AttachmentStore):
        """Initialize attachment handler.

        Args:
            attachment_store: Attachment storage instance
        """
        super().__init__()
        self._attachment_store = attachment_store

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return {
            "id": "attachments",
            "type": ResourceType.ATTACHMENT,
            "name": "Attachments",
            "version": self._attachment_store.version,
            "modified": self.last_modified,
            "attributes": {
                "count": self._attachment_store.count,
                "mime_types": self._attachment_store.mime_types,
            },
        }

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation."""
        valid_ops = {"read", "write", "delete"}
        return operation in valid_ops


class OCRHandler(BaseResourceHandler):
    """Handler for OCR resource."""

    def __init__(self, ocr_engine: Any):  # TODO: Add proper type
        """Initialize OCR handler.

        Args:
            ocr_engine: OCR engine instance
        """
        super().__init__()
        self._ocr_engine = ocr_engine

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata."""
        return {
            "id": "ocr",
            "type": ResourceType.OCR,
            "name": "OCR",
            "version": "1.0.0",  # TODO: Get from OCR engine
            "modified": self.last_modified,
            "attributes": {
                "engine": "gpt-4o",
                "supported_formats": ["png", "jpg", "pdf"],
            },
        }

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation."""
        valid_ops = {"process", "status"}
        return operation in valid_ops
