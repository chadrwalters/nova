"""Tests for attachment resource."""

import pytest
from pathlib import Path
from typing import Any

from nova.server.resources.attachment import AttachmentHandler, AttachmentStore
from nova.server.types import ResourceType


class MockStore(AttachmentStore):
    """Mock attachment store."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize mock store."""
        self.storage_path = storage_path
        self._count = 0

    def count_attachments(self) -> int:
        """Count total attachments."""
        return self._count

    def list_attachments(self) -> list[dict[str, Any]]:
        """List all attachments."""
        return []

    def add_attachment(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Add an attachment."""
        return None

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any] | None:
        """Get attachment info."""
        return None

    def update_attachment_metadata(
        self, attachment_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update attachment metadata."""
        return None

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment."""
        return False


@pytest.fixture
def mock_store(tmp_path: Path) -> MockStore:
    """Create mock attachment store."""
    return MockStore(tmp_path)


@pytest.fixture
def handler(mock_store: AttachmentStore) -> AttachmentHandler:
    """Create attachment handler."""
    return AttachmentHandler(mock_store)


def test_get_metadata(handler: AttachmentHandler, mock_store: MockStore) -> None:
    """Test getting resource metadata."""
    mock_store._count = 5
    metadata = handler.get_metadata()

    assert metadata["id"] == "attachments"
    assert metadata["type"] == ResourceType.ATTACHMENT
    assert metadata["name"] == "Attachment Store"
    assert metadata["version"] == "1.0.0"
    assert isinstance(metadata["modified"], float)
    assert metadata["attributes"]["total_attachments"] == 5
    assert metadata["attributes"]["mime_types"] == ["png", "jpg", "jpeg", "pdf", "tiff"]


def test_cleanup(handler: AttachmentHandler) -> None:
    """Test cleanup."""
    # Should not raise any errors
    handler.cleanup()
