"""Tests for the ConsolidationHandler."""

# Standard library imports
import os
from pathlib import Path

# Third-party imports
import pytest
from rich.console import Console

# Nova package imports
from nova.core.models.result import ProcessingResult
from nova.core.pipeline.pipeline_state import PipelineState
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.monitoring import MonitoringManager
from nova.core.utils.timing import TimingManager
from nova.phases.consolidate.handlers import ConsolidationHandler

# Mock classes for testing
class MockMonitoringManager:
    """Mock monitoring manager for testing."""
    def __init__(self):
        self.metrics = {}
        self.errors = []
        
    def record_metric(self, name: str, value: float) -> None:
        """Record a metric."""
        self.metrics[name] = value
        
    def record_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
        
    def async_capture_resource_usage(self) -> None:
        """Capture resource usage."""
        pass

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
    config = {
        'input_dir': 'input',
        'output_dir': str(output_dir),
        'base_dir': '.',
        'pipeline_config': {},
        'processor_config': {}
    }
    return ConsolidationHandler(
        config=config,
        console=Console(force_terminal=False)
    )

@pytest.mark.asyncio
async def test_can_handle():
    """Test can_handle method."""
    config = {
        'input_dir': 'input',
        'output_dir': 'output',
        'base_dir': '.',
        'pipeline_config': {},
        'processor_config': {}
    }
    handler = ConsolidationHandler(
        config=config,
        console=Console(force_terminal=False)
    )
    
    assert await handler.can_handle(Path("test.md"))
    assert not await handler.can_handle(Path("test.txt"))
    assert not await handler.can_handle(Path("test.py"))

@pytest.mark.asyncio
async def test_process_basic_markdown(handler, test_data_dir, output_dir):
    """Test processing a basic markdown file."""
    # Create test file
    test_file = test_data_dir / "basic.md"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("""# Test Document

## Summary
This is a test summary.

## Raw Notes
These are raw notes.

## Attachments
- test.png
""")
    
    # Process the file
    result = await handler.process(test_file)
    
    # Verify success
    assert result.success
    assert result.output
    assert len(result.output_files) > 0
    
    # Verify output file exists
    output_file = output_dir / test_file.name
    assert output_file.exists()
    
    # Verify sections were parsed
    assert result.metadata
    assert 'sections' in result.metadata
    assert len(result.metadata['sections']['summary']) > 0
    assert len(result.metadata['sections']['raw_notes']) > 0
    assert len(result.metadata['sections']['attachments']) > 0

@pytest.mark.asyncio
async def test_process_multiple_files(handler, test_data_dir, output_dir):
    """Test processing multiple markdown files."""
    # Create test files
    files = []
    for i in range(3):
        test_file = test_data_dir / f"test{i}.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(f"""# Test Document {i}

## Summary
This is test summary {i}.

## Raw Notes
These are raw notes {i}.

## Attachments
- test{i}.png
""")
        files.append(test_file)
    
    # Process files
    results = []
    for file in files:
        result = await handler.process(file)
        results.append(result)
    
    # Verify all succeeded
    assert all(r.success for r in results)
    assert all(r.output for r in results)
    assert all(len(r.output_files) > 0 for r in results)
    
    # Verify output files exist
    for file in files:
        output_file = output_dir / file.name
        assert output_file.exists()

@pytest.mark.asyncio
async def test_process_invalid_file(handler, output_dir):
    """Test processing an invalid file."""
    # Process nonexistent file
    result = await handler.process(Path("nonexistent.md"))
    
    # Verify failure
    assert not result.success
    assert result.error
    assert not result.output
    assert not result.output_files

@pytest.mark.asyncio
async def test_process_no_output_dir(test_data_dir):
    """Test processing with no output directory."""
    # Create handler without output directory
    config = {
        'input_dir': 'input',
        'base_dir': '.',
        'pipeline_config': {},
        'processor_config': {}
    }
    handler = ConsolidationHandler(
        config=config,
        console=Console(force_terminal=False)
    )
    
    # Create test file
    test_file = test_data_dir / "test.md"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# Test\nThis is a test.")
    
    # Process file with nonexistent output dir
    result = await handler.process(test_file)
    
    # Verify failure
    assert not result.success
    assert len(result.errors) > 0
    assert "No output directory specified" in result.errors[0]
    assert not result.output
    assert not result.output_files

@pytest.mark.asyncio
async def test_cleanup(handler):
    """Test cleanup method."""
    await handler.cleanup()
    # No assertions needed - just verify it doesn't raise exceptions 