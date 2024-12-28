"""Test consolidation handler."""

import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from rich.console import Console

from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import TimingManager
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.metrics import MonitoringManager
from nova.phases.parse.handlers import ConsolidationHandler

# Mock classes for testing
class AsyncMonitorContext:
    """Async context manager for monitoring operations."""
    def __init__(self, name: str):
        self.name = name

    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

class MockMonitoringManager:
    """Mock monitoring manager for testing."""
    
    def __init__(self):
        """Initialize mock monitoring manager."""
        self.metrics = {}
        self.errors = []
        
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric."""
        self.metrics[name] = {'value': value, 'tags': tags or {}}
        
    def record_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
        
    async def async_capture_resource_usage(self) -> None:
        """Capture resource usage."""
        pass
        
    def set_threshold(self, metric: str, value: float) -> None:
        """Set a threshold for a metric."""
        self.thresholds[metric] = value
        
    def get_threshold(self, metric: str) -> float:
        """Get a threshold for a metric."""
        return self.thresholds.get(metric, 0.0)
        
    def increment_counter(self, name: str) -> None:
        """Increment a counter."""
        self.counters[name] = self.counters.get(name, 0) + 1
        
    def stop(self) -> None:
        """Stop monitoring."""
        pass
        
    def async_monitor_operation(self, name: str):
        """Context manager for monitoring async operations."""
        return AsyncMonitorContext(name)

class MockPipelineState:
    """Mock pipeline state for testing."""
    def __init__(self):
        self.state = {}
        
    def get(self, key: str, default=None):
        """Get state value."""
        return self.state.get(key, default)
        
    def set(self, key: str, value: any) -> None:
        """Set state value."""
        self.state[key] = value

@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path("tests/data/consolidate")

@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    return output

@pytest.fixture
def monitoring():
    """Create a mock monitoring manager."""
    return MockMonitoringManager()

@pytest.fixture
def pipeline_state():
    """Create a mock pipeline state."""
    return MockPipelineState()

@pytest.fixture
def handler(monitoring, pipeline_state, output_dir):
    """Create a ConsolidationHandler instance."""
    return ConsolidationHandler(
        config={"output_dir": str(output_dir)},
        timing=TimingManager(),
        metrics=MetricsTracker(),
        console=Console(force_terminal=False),
        pipeline_state=pipeline_state,
        monitoring=monitoring
    )

@pytest.mark.asyncio
async def test_can_handle(handler, test_data_dir):
    """Test can_handle method."""
    # Create test files
    md_file = test_data_dir / "test.md"
    txt_file = test_data_dir / "test.txt"
    py_file = test_data_dir / "test.py"
    
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("# Test")
    txt_file.write_text("Test")
    py_file.write_text("print('test')")
    
    assert handler.can_handle(md_file)
    assert not handler.can_handle(txt_file)
    assert not handler.can_handle(py_file)

@pytest.mark.asyncio
async def test_process_basic_markdown(handler, tmp_path):
    """Test processing a basic markdown file."""
    # Create test file
    test_file = tmp_path / "basic.md"
    test_file.write_text("# Test\nThis is a test.")

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the file
    result = await handler.process(test_file, {"output_dir": output_dir})

    assert result.success
    output_file = output_dir / "basic.md"
    assert output_file.exists()
    assert output_file.read_text() == "# Test\nThis is a test."

@pytest.mark.asyncio
async def test_process_multiple_files(handler, tmp_path):
    """Test processing multiple markdown files."""
    # Create test files
    test_files = []
    for i in range(3):
        test_file = tmp_path / f"test{i}.md"
        test_file.write_text(f"# Test {i}\nThis is test {i}.")
        test_files.append(test_file)

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each file
    for test_file in test_files:
        result = await handler.process(test_file, {"output_dir": output_dir})
        assert result.success
        output_file = output_dir / test_file.name
        assert output_file.exists()
        assert output_file.read_text() == test_file.read_text()

@pytest.mark.asyncio
async def test_process_invalid_file(handler, tmp_path):
    """Test processing an invalid file."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is not a markdown file.")

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the file
    result = await handler.process(test_file, {"output_dir": output_dir})

    assert not result.success
    assert "Cannot handle file" in result.error

@pytest.mark.asyncio
async def test_process_no_output_dir(handler, tmp_path):
    """Test processing with no output directory."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nThis is a test.")

    # Create output directory path but don't create the directory
    output_dir = tmp_path / "output"

    # Process the file
    result = await handler.process(test_file, {"output_dir": output_dir})

    assert result.success
    output_file = output_dir / "test.md"
    assert output_file.exists()
    assert output_file.read_text() == "# Test\nThis is a test."

@pytest.mark.asyncio
async def test_cleanup(handler):
    """Test cleanup method."""
    await handler.cleanup() 