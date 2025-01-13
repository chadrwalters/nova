"""Test configuration and shared fixtures."""

import logging
import shutil
from pathlib import Path
from collections.abc import Generator

import pytest
from nova.server.types import ServerConfig


@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for tests.

    Args:
        tmp_path: Pytest's temporary path fixture

    Yields:
        Path to temporary directory
    """
    nova_dir = tmp_path / ".nova"
    nova_dir.mkdir(parents=True)
    yield tmp_path
    shutil.rmtree(tmp_path)


@pytest.fixture
def server_config(temp_dir: Path) -> ServerConfig:
    """Create a server configuration for tests.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Server configuration
    """
    return ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
