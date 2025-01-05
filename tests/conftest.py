"""
Global pytest fixtures and utilities for Nova test suite.
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from nova.config.manager import ConfigManager


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--openai-api",
        action="store_true",
        default=False,
        help="Run tests that require OpenAI API access",
    )


@pytest.fixture
def nova_config(mock_fs):
    """Create a test configuration."""
    config = {
        "base_dir": str(mock_fs["root"]),
        "input_dir": str(mock_fs["input"]),
        "output_dir": str(mock_fs["output"]),
        "processing_dir": str(mock_fs["processing"]),
        "cache": {"dir": str(mock_fs["cache"]), "enabled": True, "ttl": 3600},
        "apis": {
            "openai": {"api_key": "test-key", "model": "gpt-4o", "max_tokens": 500}
        },
    }

    # Create temporary config file
    config_path = mock_fs["root"] / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return ConfigManager(config_path=config_path)


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
        "cache": cache_dir,
    }


@pytest.fixture
def test_state():
    """Manage test state across test functions."""
    return {"metrics": {}, "errors": [], "processed_files": set()}


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
    config.addinivalue_line(
        "markers", "openai_api: mark test as requiring OpenAI API access"
    )


def pytest_collection_modifyitems(config, items):
    """Skip openai_api tests unless --openai-api is specified."""
    if not config.getoption("--openai-api"):
        skip_openai = pytest.mark.skip(reason="need --openai-api option to run")
        for item in items:
            if "openai_api" in item.keywords:
                item.add_marker(skip_openai)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for image description."""

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, message):
            self.message = message

    class MockResponse:
        def __init__(self, choices):
            self.choices = choices

    return MockResponse(
        [
            MockChoice(
                MockMessage("This is a test image showing a simple geometric pattern.")
            )
        ]
    )


@pytest.fixture
def mock_openai_client(mocker, mock_openai_response):
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    return mock_client
