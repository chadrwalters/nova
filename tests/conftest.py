"""Test configuration and shared fixtures."""

import logging
import os
from pathlib import Path

import chromadb
import pytest
from fastapi.testclient import TestClient

from nova.server.mcp import app
from nova.vector_store.store import VectorStore


@pytest.fixture(scope="module")
def temp_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary directory for tests."""
    tmp_path = tmp_path_factory.mktemp("nova")
    os.chmod(tmp_path, 0o777)  # Ensure parent directory has write permissions

    # Create .nova directory with write permissions
    nova_dir = tmp_path / ".nova"
    nova_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(nova_dir, 0o777)

    # Create vectors directory with write permissions
    vectors_dir = nova_dir / "vectors"
    vectors_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(vectors_dir, 0o777)

    # Create chroma directory with write permissions
    chroma_dir = vectors_dir / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(chroma_dir, 0o777)

    # Create required subdirectories with write permissions
    for subdir in ["db", "index", "system", "data"]:
        dir_path = chroma_dir / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        os.chmod(dir_path, 0o777)

    # Create SQLite database file with write permissions if it doesn't exist
    db_file = chroma_dir / "chroma.db"
    if not db_file.exists():
        db_file.touch()
        os.chmod(db_file, 0o666)

    # Create input directory with write permissions
    input_dir = nova_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(input_dir, 0o777)

    return tmp_path


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastMCP app."""
    # FastMCP provides a FastAPI app through its asgi_app property
    return TestClient(app.asgi_app)


@pytest.fixture
def vector_store(tmp_path):
    """Create a test vector store."""
    # Create vector store in temp directory
    store = VectorStore(tmp_path / ".nova/vectors")

    # Add some test documents
    store.add(
        "note1",
        "# Python Programming\nLearn Python programming with examples and best practices.",
        {
            "title": "Python Programming",
            "date": "2024-01-15",
            "tags": ["programming", "python", "coding"],
        },
    )
    store.add(
        "note2",
        "# Data Science with Python\nUsing Python for machine learning and data analysis.",
        {
            "title": "Data Science with Python",
            "date": "2024-01-15",
            "tags": ["data-science", "python", "machine-learning"],
        },
    )
    store.add(
        "note3",
        "# Project Management\nBest practices for managing software projects.",
        {"title": "Project Management", "date": "2024-01-15", "tags": ["management", "planning"]},
    )
    store._process_batch()  # Force processing

    yield store

    # Clean up
    store.cleanup()


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@pytest.fixture(autouse=True)
def reset_chroma():
    """Reset ChromaDB between tests."""
    yield
    # Clean up any existing ChromaDB instances
    if hasattr(chromadb, "_instance"):
        delattr(chromadb, "_instance")
    if hasattr(chromadb, "_settings"):
        delattr(chromadb, "_settings")


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create a temporary directory for tests."""
    return tmp_path_factory.mktemp("test")
