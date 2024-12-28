"""Test fixtures for parse phase tests."""

# Standard library imports
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import Mock

# Third-party imports
import pytest

# Nova package imports
from nova.core.utils.metrics import MetricsTracker, MonitoringManager, TimingManager


@pytest.fixture
def mock_markitdown(monkeypatch):
    """Mock the markitdown module."""
    mock_parser = Mock()
    mock_parser.parse.return_value = 'Parsed content'
    
    mock_module = Mock()
    mock_module.Parser.return_value = mock_parser
    
    monkeypatch.setattr('nova.phases.parse.processor.markitdown', mock_module)
    return mock_module 


@pytest.fixture
def test_data_dir():
    """Get test data directory."""
    return Path("tests/data/markdown")


@pytest.fixture
def output_dir(tmp_path):
    """Create temporary output directory."""
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    return output


@pytest.fixture
def monitoring():
    """Create monitoring manager."""
    return MonitoringManager() 