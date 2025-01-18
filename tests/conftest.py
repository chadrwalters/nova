"""Test fixtures for Nova system."""

import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nova.cli.commands.nova_mcp_server import app
from nova.logging import configure_logging
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore


@pytest.fixture
def configured_logging(tmp_path: Path) -> Generator[None, None, None]:
    """Configure logging for tests.

    Args:
        tmp_path: Temporary directory for test

    Yields:
        None
    """
    # Change to temp dir so .nova/logs is created there
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    configure_logging()
    yield
    # Reset logging
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    # Restore directory
    os.chdir(original_dir)


@pytest.fixture
def vector_store(tmp_path: Path) -> VectorStore:
    """Create a test vector store.

    Args:
        tmp_path: Temporary directory for test

    Returns:
        Test vector store instance
    """
    return VectorStore(base_path=str(tmp_path / "vectors"), use_memory=True)


@pytest.fixture
def session_monitor(vector_store: VectorStore) -> SessionMonitor:
    """Create a test session monitor.

    Args:
        vector_store: Test vector store instance

    Returns:
        Test session monitor instance
    """
    return SessionMonitor(vector_store=vector_store)


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    # FastAPI provides a TestClient for testing HTTP endpoints
    return TestClient(app)
