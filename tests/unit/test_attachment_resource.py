"""Tests for attachment resource."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast, Sequence
import uuid
import copy

import pytest
from nova.server.errors import ResourceError, ErrorCode
from nova.server.types import ResourceType
from nova.server.resources.attachment import (
    AttachmentHandler,
    AttachmentStoreProtocol,
)

class MockAttachmentStore(AttachmentStoreProtocol):
    """Mock attachment store for testing."""

    storage_path: Path

    def __init__(self) -> None:
        """Initialize the mock store."""
        self.attachments: dict[str, dict[str, Any]] = {}
        self.next_id = 1
        self.storage_path = Path(".nova/attachments")
        self._supported_formats = {
            "text/plain": "text",
            "text/markdown": "markdown",
            "image/png": "image",
            "image/jpeg": "image",
            "application/pdf": "pdf",
            "application/octet-stream": None
        }
        self._mime_type_conversions = {
            "text/markdown": "text/plain",
            "image/png": "image/jpeg"
        }

    def add_attachment(self, file_path: Path, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Add an attachment."""
        try:
            if not isinstance(metadata, dict):
                raise ResourceError("Invalid metadata type")

            if "mime_type" not in metadata:
                raise ResourceError("Missing required field: mime_type")

            if "metadata" in metadata and not isinstance(metadata["metadata"], dict):
                raise ResourceError("Invalid metadata type")

            # Initialize base metadata
            base_metadata = {
                "id": str(self.next_id),
                "name": file_path.name,
                "mime_type": metadata["mime_type"],
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat(),
                "size": 1024,  # Mock file size
                "metadata": {
                    "tags": metadata.get("tags", ["test"]),
                    "title": metadata.get("title", "Test Document"),
                    "format": self._supported_formats.get(metadata["mime_type"], "unknown")
                }
            }

            # Update with any additional metadata
            if "metadata" in metadata:
                base_metadata["metadata"].update(metadata["metadata"])

            # Store attachment
            self.attachments[base_metadata["id"]] = base_metadata
            self.next_id += 1

            return base_metadata
        except Exception:
            return None

    def get_attachment_info(self, attachment_id: str) -> dict[str, Any] | None:
        """Get attachment info."""
        try:
            if attachment_id not in self.attachments:
                return None
            return copy.deepcopy(self.attachments[attachment_id])
        except Exception:
            return None

    def update_attachment_metadata(self, attachment_id: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Update attachment metadata."""
        try:
            if attachment_id not in self.attachments:
                return None

            current_info = self.attachments[attachment_id]

            # Check for concurrent modification
            if "last_modified" in metadata and current_info["modified"] != metadata["last_modified"]:
                return None

            # Create a copy of current info to avoid direct modification
            updated_info = copy.deepcopy(current_info)

            # Update metadata
            if "metadata" in metadata:
                updated_info["metadata"].update(metadata["metadata"])
            else:
                updated_info["metadata"].update(metadata)

            # Update modified timestamp
            updated_info["modified"] = datetime.now().isoformat()

            # Store updated info
            self.attachments[attachment_id] = updated_info

            return updated_info
        except Exception:
            return None

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment."""
        try:
            if attachment_id not in self.attachments:
                return False
            del self.attachments[attachment_id]
            return True
        except Exception:
            return False

    def list_attachments(self) -> list[dict[str, Any]]:
        """List all attachments."""
        return list(self.attachments.values())

    def count_attachments(self) -> int:
        """Count total attachments."""
        return len(self.attachments)

    def cleanup(self) -> None:
        """Clean up attachments."""
        try:
            if not self.storage_path.exists():
                raise ResourceError("Storage path not accessible")
            self.attachments.clear()
        except Exception:
            pass

@pytest.fixture
def mock_store() -> MockAttachmentStore:
    """Create mock attachment store."""
    return MockAttachmentStore()

@pytest.fixture
def handler(mock_store: MockAttachmentStore) -> AttachmentHandler:
    """Create attachment handler with mock store."""
    return AttachmentHandler(mock_store)

def test_get_metadata(handler: AttachmentHandler) -> None:
    """Test getting resource metadata."""
    metadata = handler.get_metadata()
    assert metadata["id"] == "attachments"
    assert metadata["type"] == ResourceType.ATTACHMENT
    assert metadata["name"] == "Attachment Store"
    assert metadata["version"] == "1.0.0"
    assert "modified" in metadata
    assert "total_attachments" in metadata["attributes"]
    assert "mime_types" in metadata["attributes"]

def test_add_attachment(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test adding an attachment."""
    test_file = Path("test.txt")
    metadata = {"mime_type": "text/plain", "tags": ["test"]}

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None
    assert info["name"] == "test.txt"
    assert info["mime_type"] == "text/plain"
    assert "format" in info["metadata"]
    assert info["metadata"]["tags"] == ["test"]

def test_get_attachment_info(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test getting attachment info."""
    test_file = Path("test.txt")
    metadata = {"mime_type": "text/plain", "tags": ["test"]}

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    retrieved_info = mock_store.get_attachment_info(info["id"])
    assert retrieved_info is not None
    assert retrieved_info["id"] == info["id"]
    assert retrieved_info["name"] == "test.txt"
    assert retrieved_info["mime_type"] == "text/plain"
    assert "format" in retrieved_info["metadata"]
    assert retrieved_info["metadata"]["tags"] == ["test"]

def test_update_attachment_metadata(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test updating attachment metadata."""
    test_file = Path("test.txt")
    metadata = {"mime_type": "text/plain", "tags": ["test"]}

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    new_metadata = {"metadata": {"tags": ["updated"]}}
    updated_info = mock_store.update_attachment_metadata(info["id"], new_metadata)
    assert updated_info is not None
    assert updated_info["metadata"]["tags"] == ["updated"]
    assert updated_info["modified"] > info["modified"]

def test_delete_attachment(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test deleting an attachment."""
    test_file = Path("test.txt")
    metadata = {"mime_type": "text/plain", "tags": ["test"]}

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    assert mock_store.delete_attachment(info["id"]) is True
    assert mock_store.count_attachments() == 0
    assert mock_store.get_attachment_info(info["id"]) is None

def test_list_attachments(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test listing attachments."""
    # Add multiple attachments
    files = [Path(f"test{i}.txt") for i in range(3)]
    for file in files:
        mock_store.add_attachment(file, {"mime_type": "text/plain"})

    attachments = mock_store.list_attachments()
    assert len(attachments) == 3
    assert all(isinstance(a["id"], str) for a in attachments)
    assert all(a["mime_type"] == "text/plain" for a in attachments)

def test_nonexistent_attachment(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test operations with nonexistent attachment."""
    assert mock_store.get_attachment_info("nonexistent") is None
    assert mock_store.delete_attachment("nonexistent") is False
    assert mock_store.update_attachment_metadata("nonexistent", {}) is None

def test_attachment_metadata_validation(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test attachment metadata validation."""
    test_file = Path("test.txt")
    metadata = {
        "mime_type": "text/plain",
        "metadata": {
            "tags": ["test"],
            "title": "Test Document",
            "description": "Test description"
        }
    }

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    # Required fields
    assert "id" in info
    assert "name" in info
    assert "mime_type" in info
    assert "size" in info
    assert "created" in info
    assert "modified" in info
    assert "metadata" in info

    # Type validation
    assert isinstance(info["id"], str)
    assert isinstance(info["name"], str)
    assert isinstance(info["mime_type"], str)
    assert isinstance(info["size"], int)
    assert isinstance(info["metadata"], dict)

def test_attachment_update_validation(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test attachment metadata update validation."""
    test_file = Path("test.txt")
    metadata = {
        "mime_type": "text/plain",
        "metadata": {
            "tags": ["test"],
            "title": "Test Document"
        }
    }

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    # Test concurrent modification
    concurrent_metadata = {
        "last_modified": "2024-01-01T00:00:00",
        "metadata": {
            "tags": ["updated"]
        }
    }
    assert mock_store.update_attachment_metadata(info["id"], concurrent_metadata) is None

    # Test valid update
    valid_metadata = {
        "metadata": {
            "tags": ["updated"],
            "title": "Updated Document"
        }
    }
    updated_info = mock_store.update_attachment_metadata(info["id"], valid_metadata)
    assert updated_info is not None
    assert updated_info["metadata"]["tags"] == ["updated"]
    assert updated_info["metadata"]["title"] == "Updated Document"

def test_attachment_unsupported_format(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test handling of unsupported formats."""
    test_file = Path("test.xyz")
    metadata = {
        "mime_type": "application/unknown",
        "metadata": {
            "tags": ["test"]
        }
    }

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None
    assert info["metadata"]["format"] == "unknown"

def test_attachment_format_conversion(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test format conversion."""
    test_file = Path("test.md")
    metadata = {
        "mime_type": "text/markdown",
        "metadata": {
            "tags": ["test"]
        }
    }

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None
    assert info["mime_type"] == "text/markdown"
    assert info["metadata"]["format"] == "markdown"

def test_attachment_error_handling(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test error handling."""
    test_file = Path("test.txt")

    # Test invalid metadata type
    invalid_metadata: dict[str, Any] = {"metadata": "invalid"}  # Type error should be caught
    assert mock_store.add_attachment(test_file, invalid_metadata) is None

    # Test missing required field
    assert mock_store.add_attachment(test_file, {}) is None

    # Test invalid metadata structure
    assert mock_store.add_attachment(test_file, {"mime_type": "text/plain", "metadata": "invalid"}) is None

def test_attachment_storage_errors(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test storage error handling."""
    test_file = Path("test.txt")
    metadata = {
        "mime_type": "text/plain",
        "metadata": {
            "tags": ["test"]
        }
    }

    # Simulate storage path not existing
    mock_store.storage_path = Path("/nonexistent")
    mock_store.cleanup()  # Should not raise exception

def test_attachment_concurrent_access(handler: AttachmentHandler, mock_store: MockAttachmentStore) -> None:
    """Test concurrent access handling."""
    test_file = Path("test.txt")
    metadata = {
        "mime_type": "text/plain",
        "metadata": {
            "tags": ["test"]
        }
    }

    info = mock_store.add_attachment(test_file, metadata)
    assert info is not None

    # Simulate concurrent modification
    concurrent_metadata = {
        "last_modified": "2024-01-01T00:00:00",  # Different from actual modified time
        "metadata": {
            "tags": ["concurrent"]
        }
    }
    assert mock_store.update_attachment_metadata(info["id"], concurrent_metadata) is None
