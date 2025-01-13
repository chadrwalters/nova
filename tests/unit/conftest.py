"""Unit test configuration and fixtures."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from nova.server.types import ResourceMetadata, ResourceType, ToolMetadata, ToolType
from nova.vector_store import VectorStore


@pytest.fixture
def mock_vector_store(temp_dir: Path) -> MagicMock:
    """Create a mock vector store.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Mock vector store
    """
    mock = MagicMock(spec=VectorStore)
    mock.store_dir = temp_dir / ".nova" / "vector_store"
    mock.client = MagicMock()
    mock.version = "1.0.0"
    return mock


@pytest.fixture
def mock_note_store(temp_dir: Path) -> MagicMock:
    """Create a mock note store.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Mock note store
    """
    mock = MagicMock()
    mock.storage_path = temp_dir / ".nova" / "notes"
    mock.version = "1.0.0"
    mock.count.return_value = 0
    return mock


@pytest.fixture
def mock_attachment_store(temp_dir: Path) -> MagicMock:
    """Create a mock attachment store.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Mock attachment store
    """
    mock = MagicMock()
    mock.storage_path = temp_dir / ".nova" / "attachments"
    mock.version = "1.0.0"
    mock.count_attachments.return_value = 0
    return mock


@pytest.fixture
def mock_ocr_engine() -> MagicMock:
    """Create a mock OCR engine.

    Returns:
        Mock OCR engine
    """
    return MagicMock()


@pytest.fixture
def sample_resource_metadata() -> ResourceMetadata:
    """Create sample resource metadata.

    Returns:
        Sample resource metadata
    """
    return {
        "id": "test_resource",
        "type": ResourceType.VECTOR_STORE,
        "name": "Test Resource",
        "version": "1.0.0",
        "modified": 1234567890.0,
        "attributes": {"test_attr": "test_value"},
    }


@pytest.fixture
def sample_tool_metadata() -> ToolMetadata:
    """Create sample tool metadata.

    Returns:
        Sample tool metadata
    """
    return {
        "id": "test_tool",
        "type": ToolType.SEARCH,
        "name": "Test Tool",
        "version": "1.0.0",
        "parameters": {
            "test_param": {"type": "string", "description": "Test parameter"}
        },
        "capabilities": ["test_capability"],
    }
