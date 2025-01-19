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


@pytest.fixture(autouse=True)
def cleanup_nova_dirs(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Clean up .nova directories after each test.

    This prevents the "Directory not empty" warnings from pytest.
    """
    yield

    # Get the temporary directory from the request
    if hasattr(request, "node") and hasattr(request.node, "funcargs"):
        if "tmp_path" in request.node.funcargs:
            tmp_path = request.node.funcargs["tmp_path"]

            # Force garbage collection to close any open file handles
            import gc

            gc.collect()

            def remove_path(path: Path) -> None:
                """Remove a path and its contents."""
                try:
                    if path.is_file():
                        os.chmod(path, 0o666)
                        path.unlink()
                    elif path.is_dir():
                        for item in path.iterdir():
                            remove_path(item)
                        os.chmod(path, 0o777)
                        path.rmdir()
                except (OSError, PermissionError):
                    import shutil

                    try:
                        shutil.rmtree(path, ignore_errors=True)
                    except:
                        pass

            # Find all .nova directories recursively
            for nova_dir in tmp_path.rglob(".nova"):
                if nova_dir.exists():
                    # Try to remove the .nova directory and its contents
                    remove_path(nova_dir)

                    # Clean up parent directories if they're empty
                    try:
                        parent = nova_dir.parent
                        while parent != tmp_path:
                            if not any(parent.iterdir()):
                                os.chmod(parent, 0o777)
                                parent.rmdir()
                            parent = parent.parent
                    except (OSError, PermissionError):
                        pass


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
