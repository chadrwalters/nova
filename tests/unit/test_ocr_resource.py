"""Unit tests for OCR resource handler."""

from pathlib import Path
from unittest.mock import Mock
import pytest

from nova.bear_parser.ocr import EasyOcrModel
from nova.server.resources.ocr import OCRHandler
from nova.server.types import ResourceError, ResourceType


@pytest.fixture
def mock_engine() -> Mock:
    """Create mock OCR engine."""
    engine = Mock(spec=EasyOcrModel)
    engine.process_image.return_value = ("test text", 0.95, [])
    return engine


@pytest.fixture
def handler(mock_engine: Mock) -> OCRHandler:
    """Create OCR handler instance."""
    return OCRHandler(mock_engine)


def test_get_metadata(handler: OCRHandler) -> None:
    """Test getting resource metadata."""
    metadata = handler.get_metadata()

    # Test basic metadata fields
    assert isinstance(metadata, dict)
    assert all(
        key in metadata
        for key in ["id", "type", "name", "version", "modified", "attributes"]
    )

    # Test specific values
    assert metadata["id"] == "ocr-handler"
    assert metadata["type"] == ResourceType.OCR.name
    assert metadata["name"] == "OCR Handler"  # type: ignore[unreachable]
    assert metadata["version"] == "0.1.0"
    assert isinstance(metadata["modified"], float)

    # Test attributes
    attributes = metadata["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["engine"] == "gpt-4o"
    assert attributes["languages"] == ["en"]
    assert attributes["confidence_threshold"] == handler.CONFIDENCE_THRESHOLD
    assert attributes["cache_enabled"] is True
    assert attributes["cache_size"] == 0


def test_validate_access(handler: OCRHandler) -> None:
    """Test access validation."""
    assert handler.validate_access("read") is True
    assert handler.validate_access("write") is True
    assert handler.validate_access("delete") is True
    assert handler.validate_access("invalid") is False


def test_process_image_success(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test successful image processing."""
    # Create test image
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Mock engine response
    mock_engine.process_image.return_value = (
        "test text",
        0.95,
        [{"text": "test text", "confidence": 0.95, "bbox": [0, 0, 100, 100]}],
    )

    # Process image
    result = handler.process_image(test_image)

    # Verify result
    assert result["text"] == "test text"
    assert result["confidence"] == 0.95
    assert len(result["regions"]) == 1
    assert result["language"] == "en"
    assert isinstance(result["processing_time"], float)

    # Verify engine call
    mock_engine.process_image.assert_called_once_with(str(test_image))


def test_process_image_with_cache(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test image processing with caching."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # First call should use engine
    result1 = handler.process_image(test_image, cache_key="test1")
    assert result1["text"] == "test text"
    mock_engine.process_image.assert_called_once()

    # Second call with same cache key should use cache
    result2 = handler.process_image(test_image, cache_key="test1")
    assert result2 == result1
    mock_engine.process_image.assert_called_once()  # No additional calls


def test_process_image_force_reprocess(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test forced reprocessing of cached image."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Process with cache
    handler.process_image(test_image, cache_key="test1")
    assert mock_engine.process_image.call_count == 1

    # Force reprocess
    handler.process_image(test_image, cache_key="test1", force_reprocess=True)
    assert mock_engine.process_image.call_count == 2


def test_process_image_invalid_file(handler: OCRHandler, tmp_path: Path) -> None:
    """Test processing invalid image file."""
    with pytest.raises(ResourceError) as exc:
        handler.process_image(tmp_path / "nonexistent.png")
    assert "Image not found" in str(exc.value)


def test_process_image_not_file(handler: OCRHandler, tmp_path: Path) -> None:
    """Test processing directory instead of file."""
    with pytest.raises(ResourceError) as exc:
        handler.process_image(tmp_path)
    assert "Not a file" in str(exc.value)


def test_get_cached_result(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test retrieving cached OCR result."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Process and cache
    result = handler.process_image(test_image, cache_key="test1")

    # Get from cache
    cached = handler.get_cached_result("test1")
    assert cached == result

    # Try non-existent key
    assert handler.get_cached_result("nonexistent") is None


def test_clear_cache(handler: OCRHandler, mock_engine: Mock, tmp_path: Path) -> None:
    """Test clearing OCR result cache."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Add some results to cache
    handler.process_image(test_image, cache_key="test1")
    handler.process_image(test_image, cache_key="test2")
    assert len(handler._result_cache) == 2

    # Clear cache
    handler.clear_cache()
    assert len(handler._result_cache) == 0


def test_cache_size_limit(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test cache size limit enforcement."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Fill cache to limit
    for i in range(handler.MAX_CACHE_SIZE + 1):
        handler.process_image(test_image, cache_key=f"test{i}")

    # Verify cache size doesn't exceed limit
    assert len(handler._result_cache) == handler.MAX_CACHE_SIZE


def test_on_change_registration(handler: OCRHandler) -> None:
    """Test change callback registration."""
    callback = Mock()
    handler.on_change(callback)

    # Trigger change
    handler.clear_cache()

    callback.assert_called_once()


def test_on_change_invalid_callback(handler: OCRHandler) -> None:
    """Test registering invalid change callback."""
    with pytest.raises(ValueError) as exc:
        handler.on_change("not a callable")  # type: ignore[arg-type]
    assert "Callback must be callable" in str(exc.value)


def test_notify_change_error_handling(handler: OCRHandler) -> None:
    """Test error handling in change notifications."""

    def failing_callback() -> None:
        raise Exception("Test error")

    handler.on_change(failing_callback)
    # Should not raise exception
    handler.clear_cache()


def test_engine_errors(handler: OCRHandler, mock_engine: Mock, tmp_path: Path) -> None:
    """Test OCR engine error handling."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Test engine initialization error
    mock_engine.process_image.side_effect = RuntimeError("OCR model is disabled")
    with pytest.raises(ResourceError) as exc:
        handler.process_image(test_image)
    assert "Failed to process image" in str(exc.value)

    # Test corrupted image error
    mock_engine.process_image.side_effect = ValueError("Invalid image data")
    with pytest.raises(ResourceError) as exc:
        handler.process_image(test_image)
    assert "Failed to process image" in str(exc.value)

    # Test memory error
    mock_engine.process_image.side_effect = MemoryError("Out of memory")
    with pytest.raises(ResourceError) as exc:
        handler.process_image(test_image)
    assert "Failed to process image" in str(exc.value)


def test_confidence_values(
    handler: OCRHandler, mock_engine: Mock, tmp_path: Path
) -> None:
    """Test handling of different confidence values."""
    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"test image data")

    # Test high confidence result
    mock_engine.process_image.return_value = (
        "high confidence text",
        0.95,
        [
            {
                "text": "high confidence text",
                "confidence": 0.95,
                "bbox": [0, 0, 100, 100],
            }
        ],
    )
    result = handler.process_image(test_image)
    assert result["text"] == "high confidence text"
    assert result["confidence"] == 0.95

    # Test low confidence result
    mock_engine.process_image.return_value = (
        "low confidence text",
        0.45,
        [{"text": "low confidence text", "confidence": 0.45, "bbox": [0, 0, 100, 100]}],
    )
    result = handler.process_image(test_image)
    assert result["text"] == "low confidence text"
    assert result["confidence"] == 0.45
