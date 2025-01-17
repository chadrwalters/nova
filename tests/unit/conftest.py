"""Unit test configuration and fixtures."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
    mock.count.return_value = 0
    return mock


@pytest.fixture
def mock_ocr_engine() -> MagicMock:
    """Create a mock OCR engine.

    Returns:
        Mock OCR engine
    """
    mock = MagicMock()
    mock.version = "1.0.0"
    return mock
