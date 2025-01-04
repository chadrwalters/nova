"""
Global pytest fixtures and utilities for Nova test suite.
"""
import os
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_fs(temp_dir):
    """Provide a mock filesystem with basic structure."""
    # Create basic directory structure
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    processing_dir = temp_dir / "processing"
    cache_dir = temp_dir / "cache"
    
    for dir_path in [input_dir, output_dir, processing_dir, cache_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    yield {
        "root": temp_dir,
        "input": input_dir,
        "output": output_dir,
        "processing": processing_dir,
        "cache": cache_dir
    }


@pytest.fixture
def test_state():
    """Manage test state across test functions."""
    return {
        "metrics": {},
        "errors": [],
        "processed_files": set()
    }


@pytest.fixture
def async_test_state(test_state):
    """Additional state management for async tests."""
    test_state["tasks"] = []
    test_state["events"] = []
    return test_state


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "core: mark test as testing core functionality")
    config.addinivalue_line("markers", "handlers: mark test as testing handlers")
    config.addinivalue_line("markers", "phases: mark test as testing pipeline phases") 