"""Unit tests for attachment resource handler."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast, TypedDict
from collections.abc import Callable
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from nova.server.resources.attachment import AttachmentHandler
from nova.server.types import ResourceError, ResourceType


class AttachmentResult(TypedDict):
    """Attachment result type."""

    id: str
    mime_type: str
    ocr_status: str


@pytest.fixture
def mock_store() -> Mock:
    """Create mock attachment store."""
    store = Mock()
    store.storage_path = Path("/tmp/attachments")
    store.count_attachments.return_value = 0
    store.version = "1.0.0"
    return store


@pytest.fixture
def handler(mock_store: Mock) -> AttachmentHandler:
    """Create attachment handler instance."""
    return AttachmentHandler(mock_store)


def test_get_metadata(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test getting resource metadata."""
    mock_store.count_attachments.return_value = 5
    mock_store.mime_types = ["image/png", "image/jpeg", "application/pdf"]
    mock_store.storage_path = Path("/test/store")
    metadata = handler.get_metadata()

    assert metadata["id"] == "attachment-handler"
    assert metadata["type"] == ResourceType.ATTACHMENT.name
    assert metadata["name"] == "Attachment Handler"
    assert metadata["version"] == "1.0.0"
    assert isinstance(metadata["modified"], float)
    assert metadata["attributes"]["total_attachments"] == 5
    assert metadata["attributes"]["supported_formats"] == [
        "image/png",
        "image/jpeg",
        "application/pdf",
    ]
    assert metadata["attributes"]["storage_path"] == "/test/store"


def test_validate_access(handler: AttachmentHandler) -> None:
    """Test access validation."""
    assert handler.validate_access("read") is True
    assert handler.validate_access("write") is True
    assert handler.validate_access("delete") is True
    assert handler.validate_access("invalid") is False


def test_add_attachment_success(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test successful attachment addition."""
    # Create test file
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"test data")

    # Mock store responses
    mock_info = {
        "id": "test-id",
        "name": "test.png",
        "mime_type": "image/png",
        "size": 9,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "ocr_status": "pending",
        "ocr_confidence": None,
        "metadata": {},
    }
    mock_store.add_attachment.return_value = mock_info
    mock_store.get_attachment_info.return_value = mock_info

    # Add attachment
    result = handler.add_attachment(test_file, {"key": "value"})

    # Verify result
    assert isinstance(result, dict)
    assert result["id"] == "test-id"
    assert result["name"] == "test.png"
    assert result["mime_type"] == "image/png"
    assert result["ocr_status"] == "pending"

    # Verify store calls
    mock_store.add_attachment.assert_called_once_with(test_file, {"key": "value"})
    mock_store.get_attachment_info.assert_called_once_with("test-id")


def test_add_attachment_invalid_file(
    handler: AttachmentHandler, tmp_path: Path
) -> None:
    """Test adding invalid file."""
    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(tmp_path / "nonexistent.png")
    assert "File not found" in str(exc.value)


def test_add_attachment_unsupported_format(
    handler: AttachmentHandler, tmp_path: Path
) -> None:
    """Test adding unsupported file format."""
    test_file = tmp_path / "test.xyz"
    test_file.write_bytes(b"test data")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Unsupported file format" in str(exc.value)


def test_get_attachment_success(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test successful attachment retrieval."""
    mock_info = {
        "id": "test-id",
        "name": "test.png",
        "mime_type": "image/png",
        "size": 100,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "ocr_status": "completed",
        "ocr_confidence": 0.95,
        "metadata": {"key": "value"},
    }
    mock_store.get_attachment_info.return_value = mock_info

    result = handler.get_attachment("test-id")
    assert result == mock_info
    mock_store.get_attachment_info.assert_called_once_with("test-id")


def test_get_attachment_not_found(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test getting non-existent attachment."""
    mock_store.get_attachment_info.return_value = None

    with pytest.raises(ResourceError) as exc:
        handler.get_attachment("nonexistent-id")
    assert "Attachment not found" in str(exc.value)


def test_update_attachment_success(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test successful attachment update."""
    mock_info = {"id": "test-id", "name": "test.png", "metadata": {"key": "updated"}}
    mock_store.update_attachment_metadata.return_value = mock_info

    result = handler.update_attachment("test-id", {"key": "updated"})
    assert result == mock_info
    mock_store.update_attachment_metadata.assert_called_once_with(
        "test-id", {"key": "updated"}
    )


def test_update_attachment_not_found(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test updating non-existent attachment."""
    mock_store.update_attachment_metadata.return_value = None

    with pytest.raises(ResourceError) as exc:
        handler.update_attachment("nonexistent-id", {})
    assert "Attachment not found" in str(exc.value)


def test_delete_attachment_success(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test successful attachment deletion."""
    mock_store.delete_attachment.return_value = True

    handler.delete_attachment("test-id")
    mock_store.delete_attachment.assert_called_once_with("test-id")


def test_delete_attachment_not_found(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test deleting non-existent attachment."""
    mock_store.delete_attachment.return_value = False

    with pytest.raises(ResourceError) as exc:
        handler.delete_attachment("nonexistent-id")
    assert "Attachment not found" in str(exc.value)


def test_list_attachments_no_filter(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test listing attachments without filters."""
    mock_attachments = [
        {"id": "1", "mime_type": "image/png", "ocr_status": "completed"},
        {"id": "2", "mime_type": "image/jpeg", "ocr_status": "pending"},
    ]
    mock_store.list_attachments.return_value = mock_attachments

    result = handler.list_attachments()
    assert result == mock_attachments
    mock_store.list_attachments.assert_called_once()


def test_list_attachments_with_filters(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test listing attachments with filters."""
    mock_attachments: list[AttachmentResult] = [
        {"id": "1", "mime_type": "image/png", "ocr_status": "completed"},
        {"id": "2", "mime_type": "image/jpeg", "ocr_status": "pending"},
    ]
    mock_store.list_attachments.return_value = mock_attachments

    # Test MIME type filter
    result = handler.list_attachments(filter_mime_type="image/png")
    assert len(result) == 1
    first_result = result[0]
    assert first_result["id"] == "1"

    # Test OCR status filter
    result = handler.list_attachments(filter_ocr_status="pending")
    assert len(result) == 1
    first_result = result[0]
    assert first_result["id"] == "2"


def test_on_change_registration(handler: AttachmentHandler) -> None:
    """Test change callback registration."""
    callback = Mock()
    handler.on_change(callback)

    # Trigger change
    mock_add = MagicMock()
    with patch.object(handler, "add_attachment", mock_add):
        handler._notify_change()

    callback.assert_called_once()


def test_on_change_invalid_callback(handler: AttachmentHandler) -> None:
    """Test registering invalid change callback."""
    with pytest.raises(ValueError) as exc:
        handler.on_change("not a callable")  # type: ignore[arg-type]
    assert "Callback must be callable" in str(exc.value)


def test_notify_change_error_handling(handler: AttachmentHandler) -> None:
    """Test error handling in change notifications."""

    def failing_callback() -> None:
        raise Exception("Test error")

    handler.on_change(failing_callback)
    # Should not raise exception
    handler._notify_change()


def test_mime_type_detection(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test MIME type detection for different file types."""
    test_files = {
        "test.png": (b"PNG data", "image/png"),
        "test.jpg": (b"JPEG data", "image/jpeg"),
        "test.pdf": (b"PDF data", "application/pdf"),
        "test.tiff": (b"TIFF data", "image/tiff"),
    }

    for filename, (data, expected_mime) in test_files.items():
        # Create test file
        test_file = tmp_path / filename
        test_file.write_bytes(data)

        # Mock store responses
        mock_info = {
            "id": "test-id",
            "name": filename,
            "mime_type": expected_mime,
            "size": len(data),
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "ocr_status": "pending",
            "ocr_confidence": None,
            "metadata": {},
        }
        mock_store.add_attachment.return_value = mock_info
        mock_store.get_attachment_info.return_value = mock_info

        # Add attachment
        result = handler.add_attachment(test_file)
        assert isinstance(result, dict), "Expected dictionary result"
        assert result.get("mime_type") == expected_mime


def test_mime_type_validation(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test validation of MIME types against supported formats."""
    # Test valid MIME types
    valid_files = {
        "test.png": "image/png",
        "test.jpg": "image/jpeg",
        "test.jpeg": "image/jpeg",
        "test.pdf": "application/pdf",
        "test.tiff": "image/tiff",
    }

    for filename, mime_type in valid_files.items():
        test_file = tmp_path / filename
        test_file.write_bytes(b"test data")
        mock_info = {
            "id": "test-id",
            "name": filename,
            "mime_type": mime_type,
            "size": 9,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "ocr_status": "pending",
            "ocr_confidence": None,
            "metadata": {},
        }
        mock_store.add_attachment.return_value = mock_info
        mock_store.get_attachment_info.return_value = mock_info
        result = handler.add_attachment(test_file)
        assert isinstance(result, dict), "Expected dictionary result"
        assert result.get("mime_type") == mime_type

    # Test invalid MIME types
    invalid_files = {
        "test.txt": "text/plain",
        "test.doc": "application/msword",
        "test.gif": "image/gif",
    }

    for filename, _ in invalid_files.items():
        test_file = tmp_path / filename
        test_file.write_bytes(b"test data")
        with pytest.raises(ResourceError) as exc:
            handler.add_attachment(test_file)
        assert "Unsupported file format" in str(exc.value)


def test_mime_type_filtering(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test filtering attachments by MIME type."""
    mock_attachments = [
        {"id": "1", "mime_type": "image/png", "ocr_status": "completed"},
        {"id": "2", "mime_type": "image/jpeg", "ocr_status": "pending"},
        {"id": "3", "mime_type": "application/pdf", "ocr_status": "completed"},
        {"id": "4", "mime_type": "image/png", "ocr_status": "failed"},
    ]
    mock_store.list_attachments.return_value = mock_attachments

    # Test filtering by specific MIME type
    png_results = handler.list_attachments(filter_mime_type="image/png")
    assert len(png_results) == 2
    assert all(r["mime_type"] == "image/png" for r in png_results)

    # Test filtering by different MIME type
    pdf_results = handler.list_attachments(filter_mime_type="application/pdf")
    assert len(pdf_results) == 1
    assert pdf_results[0]["mime_type"] == "application/pdf"

    # Test filtering with non-existent MIME type
    empty_results = handler.list_attachments(filter_mime_type="image/gif")
    assert len(empty_results) == 0


def test_mime_type_edge_cases(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test edge cases in MIME type handling."""
    # Test file with no extension
    no_ext_file = tmp_path / "testfile"
    no_ext_file.write_bytes(b"test data")
    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(no_ext_file)
    assert "Unknown file type" in str(exc.value)

    # Test file with mixed case extension
    mixed_case_file = tmp_path / "test.PNG"
    mixed_case_file.write_bytes(b"test data")
    mock_info = {
        "id": "test-id",
        "name": "test.PNG",
        "mime_type": "image/png",
        "size": 9,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "ocr_status": "pending",
        "ocr_confidence": None,
        "metadata": {},
    }
    mock_store.add_attachment.return_value = mock_info
    mock_store.get_attachment_info.return_value = mock_info
    result = handler.add_attachment(mixed_case_file)
    assert result["mime_type"] == "image/png"

    # Test file with double extension
    double_ext_file = tmp_path / "test.tar.pdf"
    double_ext_file.write_bytes(b"test data")
    mock_info = {
        "id": "test-id",
        "name": "test.tar.pdf",
        "mime_type": "application/pdf",
        "size": 9,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "ocr_status": "pending",
        "ocr_confidence": None,
        "metadata": {},
    }
    mock_store.add_attachment.return_value = mock_info
    mock_store.get_attachment_info.return_value = mock_info
    result = handler.add_attachment(double_ext_file)
    assert result["mime_type"] == "application/pdf"


def mock_add_attachment(
    file_path: str | Path, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Mock function for add_attachment."""
    name = file_path.name if isinstance(file_path, Path) else str(file_path)
    return {
        "id": f"test-id-{time.time_ns()}",  # Use timestamp for unique IDs
        "name": name,
        "mime_type": "image/png",
        "size": 100,
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "ocr_status": "pending",
        "ocr_confidence": None,
        "metadata": metadata or {},
    }


def test_concurrent_add_attachments(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test concurrent addition of attachments."""
    # Create test files
    test_files = []
    for i in range(5):
        test_file = tmp_path / f"test{i}.png"
        test_file.write_bytes(b"test data")
        test_files.append(test_file)

    # Mock store responses
    mock_store.add_attachment.side_effect = mock_add_attachment
    mock_store.get_attachment_info.side_effect = mock_add_attachment

    # Add attachments concurrently
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(handler.add_attachment, file) for file in test_files]
        results = [future.result() for future in futures]

    # Verify results
    assert len(results) == 5
    assert len({r["id"] for r in results}) == 5  # All IDs should be unique
    assert all(r["mime_type"] == "image/png" for r in results)


def test_concurrent_updates(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test concurrent updates to the same attachment."""
    attachment_id = "test-id"

    # Mock store responses
    def mock_update(aid: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {"id": aid, "name": "test.png", "metadata": metadata}

    mock_store.update_attachment_metadata.side_effect = mock_update

    # Perform concurrent updates
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(
                handler.update_attachment, attachment_id, {"key": f"value{i}"}
            )
            for i in range(3)
        ]
        results = [future.result() for future in futures]

    # Verify results
    assert len(results) == 3
    assert all(r["id"] == attachment_id for r in results)
    assert (
        len({r["metadata"]["key"] for r in results}) == 3
    )  # All updates should be processed


def test_concurrent_read_write(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test concurrent read and write operations."""
    # Set up initial attachment
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"test data")

    # Mock store responses
    def mock_get_info(attachment_id: str) -> dict[str, Any]:
        return {
            "id": attachment_id,
            "name": "test.png",
            "mime_type": "image/png",
            "size": 9,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "ocr_status": "pending",
            "ocr_confidence": None,
            "metadata": {},
        }

    def mock_update(aid: str, metadata: dict[str, Any]) -> dict[str, Any]:
        info = mock_get_info(aid)
        info["metadata"] = metadata
        return info

    def mock_add(
        file_path: Path, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return mock_get_info("test-id")

    mock_store.add_attachment.side_effect = mock_add
    mock_store.get_attachment_info.side_effect = mock_get_info
    mock_store.update_attachment_metadata.side_effect = mock_update

    # Add initial attachment
    handler.add_attachment(test_file)

    # Perform concurrent reads and writes
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=5) as executor:
        read_futures = [
            executor.submit(handler.get_attachment, "test-id") for _ in range(3)
        ]
        write_futures = [
            executor.submit(handler.update_attachment, "test-id", {"key": f"value{i}"})
            for i in range(2)
        ]

        results = [f.result() for f in read_futures + write_futures]

    # Verify results
    assert len(results) == 5
    assert all(r["id"] == "test-id" for r in results)
    assert all(r["mime_type"] == "image/png" for r in results)


def test_concurrent_list_and_modify(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test concurrent list and modify operations."""
    # Mock initial attachments
    mock_attachments = [
        {
            "id": str(i),
            "mime_type": "image/png",
            "ocr_status": "completed",
            "metadata": {},
        }
        for i in range(5)
    ]

    def mock_list() -> list[dict[str, Any]]:
        return mock_attachments

    def mock_update(aid: str, metadata: dict[str, Any]) -> dict[str, Any]:
        for attachment in mock_attachments:
            if attachment["id"] == aid:
                updated = attachment.copy()
                updated["metadata"] = metadata
                return updated
        raise ResourceError(f"Attachment not found: {aid}")

    mock_store.list_attachments.side_effect = mock_list
    mock_store.update_attachment_metadata.side_effect = mock_update

    # Perform concurrent list and modify operations
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as executor:
        list_futures = [executor.submit(handler.list_attachments) for _ in range(2)]
        modify_futures = [
            executor.submit(handler.update_attachment, "0", {"key": f"value{i}"})
            for i in range(2)
        ]

        # Split and type the results appropriately
        all_results = [f.result() for f in list_futures + modify_futures]
        list_results = cast(list[list[dict[str, Any]]], all_results[:2])
        update_results = cast(list[dict[str, Any]], all_results[2:])

    # Verify results
    assert len(all_results) == 4
    assert all(isinstance(r, list) for r in list_results)  # List results
    assert all(isinstance(r, dict) for r in update_results)  # Update results
    assert all(len(r) == 5 for r in list_results)  # List results have all items
    assert all(r["id"] == "0" for r in update_results)  # Update results have correct ID


def test_concurrent_delete(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test concurrent deletion of attachments."""
    # Mock successful deletion
    mock_store.delete_attachment.return_value = True

    # Perform concurrent deletions
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(handler.delete_attachment, f"test-id-{i}") for i in range(3)
        ]

        # All deletions should complete without errors
        [f.result() for f in futures]

    # Verify delete calls
    assert mock_store.delete_attachment.call_count == 3


def test_concurrent_callbacks(handler: AttachmentHandler) -> None:
    """Test concurrent execution of change callbacks."""
    from threading import Event

    # Create events to track callback execution
    events = [Event() for _ in range(3)]

    # Register callbacks that set events
    def create_callback(event: Event) -> Callable[[], None]:
        def callback() -> None:
            event.set()

        return callback

    for event in events:
        handler.on_change(create_callback(event))

    # Trigger notifications from multiple threads
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as executor:
        [executor.submit(handler._notify_change) for _ in range(3)]

    # Verify all callbacks were executed
    assert all(event.is_set() for event in events)


def test_storage_path_errors(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test handling of storage path errors."""
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"test data")

    # Test non-existent storage path
    mock_store.storage_path = Path("/nonexistent/path")
    mock_store.add_attachment.side_effect = FileNotFoundError("Storage path not found")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "Storage path not found" in str(exc.value)

    # Test invalid storage path
    mock_store.storage_path = Path("/dev/null")  # Invalid storage location
    mock_store.add_attachment.side_effect = OSError("Invalid storage location")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "Invalid storage location" in str(exc.value)

    # Test storage path without write permissions
    mock_store.storage_path = Path("/root/readonly")  # No write permission
    mock_store.add_attachment.side_effect = PermissionError("Permission denied")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "Permission denied" in str(exc.value)


def test_file_system_errors(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test handling of file system errors."""
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"test data")

    # Test disk full error
    mock_store.add_attachment.side_effect = OSError("No space left on device")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "No space left on device" in str(exc.value)

    # Test file too large error
    mock_store.add_attachment.side_effect = OSError("File too large")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "File too large" in str(exc.value)

    # Test I/O error during file copy
    mock_store.add_attachment.side_effect = IOError("I/O error during file copy")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "I/O error during file copy" in str(exc.value)

    # Test file system read-only error
    mock_store.add_attachment.side_effect = OSError("Read-only file system")

    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file)
    assert "Failed to add attachment" in str(exc.value)
    assert "Read-only file system" in str(exc.value)


def test_metadata_validation_errors(
    handler: AttachmentHandler, mock_store: Mock, tmp_path: Path
) -> None:
    """Test handling of metadata validation errors."""
    test_file = tmp_path / "test.png"
    test_file.write_bytes(b"test data")

    # Test invalid metadata type
    mock_store.add_attachment.side_effect = ValueError("Invalid metadata type")
    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file, metadata="invalid")  # type: ignore[arg-type]
    assert "Failed to add attachment" in str(exc.value)
    assert "Invalid metadata type" in str(exc.value)

    # Test metadata with invalid values
    invalid_metadata = {
        "key": object(),  # Non-serializable object
        "timestamp": "invalid-date",
    }
    mock_store.add_attachment.side_effect = ValueError("Invalid metadata values")
    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file, metadata=invalid_metadata)
    assert "Failed to add attachment" in str(exc.value)
    assert "Invalid metadata values" in str(exc.value)

    # Test metadata size limit
    large_metadata = {
        f"key{i}": "x" * 1000  # Large string value
        for i in range(1000)  # Many key-value pairs
    }
    mock_store.add_attachment.side_effect = ValueError("Metadata size exceeds limit")
    with pytest.raises(ResourceError) as exc:
        handler.add_attachment(test_file, metadata=large_metadata)
    assert "Failed to add attachment" in str(exc.value)
    assert "Metadata size exceeds limit" in str(exc.value)


def test_store_operation_errors(handler: AttachmentHandler, mock_store: Mock) -> None:
    """Test handling of store operation errors."""
    # Test get_attachment_info error
    mock_store.get_attachment_info.side_effect = Exception("Store operation failed")

    with pytest.raises(ResourceError) as exc:
        handler.get_attachment("test-id")
    assert "Failed to get attachment" in str(exc.value)
    assert "Store operation failed" in str(exc.value)

    # Test list_attachments error
    mock_store.list_attachments.side_effect = Exception("Store listing failed")

    with pytest.raises(ResourceError) as exc:
        handler.list_attachments()
    assert "Failed to list attachments" in str(exc.value)
    assert "Store listing failed" in str(exc.value)

    # Test update_attachment_metadata error
    mock_store.update_attachment_metadata.side_effect = Exception(
        "Metadata update failed"
    )

    with pytest.raises(ResourceError) as exc:
        handler.update_attachment("test-id", {})
    assert "Failed to update attachment" in str(exc.value)
    assert "Metadata update failed" in str(exc.value)

    # Test delete_attachment error
    mock_store.delete_attachment.side_effect = Exception("Delete operation failed")

    with pytest.raises(ResourceError) as exc:
        handler.delete_attachment("test-id")
    assert "Failed to delete attachment" in str(exc.value)
    assert "Delete operation failed" in str(exc.value)


def test_store_initialization_errors(
    handler: AttachmentHandler, mock_store: Mock
) -> None:
    """Test handling of store initialization errors."""
    # Test count_attachments error during metadata retrieval
    mock_store.count_attachments.side_effect = Exception("Store initialization failed")
    mock_store.mime_types = ["image/png", "image/jpeg", "application/pdf"]
    mock_store.storage_path = Path("/test/store")

    with pytest.raises(ResourceError) as exc:
        handler.get_metadata()
    assert "Failed to get metadata" in str(exc.value)
    assert "Store initialization failed" in str(exc.value)

    # Test storage path error during metadata retrieval
    mock_store.count_attachments.side_effect = None
    mock_store.mime_types = None

    with pytest.raises(ResourceError) as exc:
        handler.get_metadata()
    assert "Failed to get metadata" in str(exc.value)
    assert "'NoneType' object is not iterable" in str(
        exc.value
    )  # This is the actual error we get
