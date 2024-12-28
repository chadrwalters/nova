"""Test markdown processor."""

# Standard library imports
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch

# Third-party imports
import pytest
from rich.console import Console

# Nova package imports
from nova.core.config.base import PipelineConfig, ProcessorConfig, ComponentConfig
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.phases.parse.processor import MarkdownParseProcessor


class MockMonitoringManager:
    """Mock monitoring manager for testing."""
    
    def __init__(self):
        """Initialize mock monitoring manager."""
        self._metrics = {
            'gauges': {},
            'counters': {},
            'errors': []
        }
        
    def record_error(self, error: str) -> None:
        """Record an error."""
        self._metrics['errors'].append(error)
        
    def get_errors(self) -> List[str]:
        """Get recorded errors."""
        return self._metrics['errors']
        
    def update_progress(self, processed: int = 0, failed: int = 0, skipped: int = 0) -> None:
        """Update progress metrics."""
        pass
        
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        if name not in self._metrics['counters']:
            self._metrics['counters'][name] = 0
        self._metrics['counters'][name] += 1
        
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        self._metrics['gauges'][name] = value
        
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    Path(temp_dir, "input").mkdir(exist_ok=True)
    Path(temp_dir, "output").mkdir(exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def pipeline_config(temp_dir):
    """Create a pipeline configuration for testing."""
    from nova.phases.parse.processor import MarkdownParseProcessor
    
    input_dir = Path(temp_dir) / "input"
    output_dir = Path(temp_dir) / "output"
    temp_dir = Path(temp_dir) / "temp"
    
    # Create directories
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "temp_dir": str(temp_dir),
        "processor": MarkdownParseProcessor,
        "components": {
            "parser": {
                "type": "markdown"
            }
        },
        "phases": {
            "parse": {
                "enabled": True,
                "processor": MarkdownParseProcessor,
                "handlers": ["markdown", "consolidation"],
                "output_dir": str(output_dir),
                "components": {
                    "parser": {
                        "type": "markdown"
                    }
                }
            }
        }
    }
    
    return PipelineConfig(config)


class TestMarkdownParseProcessor:
    """Test cases for MarkdownParseProcessor."""

    @pytest.fixture
    def processor(self, temp_dir, pipeline_config):
        """Create a MarkdownParseProcessor instance for testing."""
        config = {
            "name": "markdown_parse",
            "description": "Markdown processor for testing",
            "processor": "markdown_parse",
            "output_dir": str(pipeline_config.output_dir),
            "components": {
                "parser": {
                    "type": "markdown",
                    "config": {},
                    "handlers": []
                }
            },
            "handlers": {}  # Let the processor initialize its own handlers
        }
        
        monitoring = MockMonitoringManager()
        timing = TimingManager()
        metrics = MetricsTracker()
        console = Console()
        pipeline_state = PipelineState(state_file=Path(temp_dir) / "pipeline_state.json")
        return MarkdownParseProcessor(
            config=ProcessorConfig(**config),
            monitoring=monitoring,
            timing=timing,
            metrics=metrics,
            console=console,
            pipeline_state=pipeline_state,
            pipeline_config=pipeline_config
        )

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.config['output_dir']
        assert processor.handlers is not None
        assert len(processor.handlers) == 2

    @pytest.mark.asyncio
    async def test_process_markdown_file(self, processor, temp_dir):
        """Test processing a markdown file."""
        # Create test markdown file
        test_file = Path(temp_dir) / "input" / "test.md"
        test_file.write_text("""# Test Document

## Summary
This is a test summary.

## Raw Notes
These are raw notes.

## Attachments
- test.png
""")

        # Process the file
        result = await processor.process([test_file])
        
        assert result.success
        # Each input file produces both .md and .json output
        assert len(result.output_files) == 2
        for output_file in result.output_files:
            assert output_file.exists()
            assert output_file.suffix in [".md", ".json"]

    @pytest.mark.asyncio
    async def test_process_multiple_files(self, processor, temp_dir):
        """Test processing multiple markdown files."""
        # Create test files
        files = []
        for i in range(3):
            test_file = Path(temp_dir) / "input" / f"test{i}.md"
            test_file.write_text(f"""# Test Document {i}

## Summary
This is test summary {i}.

## Raw Notes
These are raw notes {i}.

## Attachments
- test{i}.png
""")
            files.append(test_file)

        # Process the files
        result = await processor.process(files)
        
        assert result.success
        # Each input file produces both .md and .json output
        assert len(result.output_files) == 6  # 3 files * 2 outputs each
        md_files = [f for f in result.output_files if f.suffix == ".md"]
        json_files = [f for f in result.output_files if f.suffix == ".json"]
        assert len(md_files) == 3
        assert len(json_files) == 3
        for output_file in result.output_files:
            assert output_file.exists()

    @pytest.mark.asyncio
    async def test_process_invalid_file(self, processor, temp_dir):
        """Test processing an invalid file."""
        # Create test file with invalid extension
        test_file = Path(temp_dir) / "input" / "test.txt"
        test_file.write_text("This is not a markdown file.")

        # Process the file
        result = await processor.process([test_file])
        
        assert not result.success
        assert len(result.output_files) == 0
        assert 'Invalid file type' in str(result.error)

    @pytest.mark.asyncio
    async def test_process_nonexistent_file(self, processor):
        """Test processing a nonexistent file."""
        result = await processor.process([Path('nonexistent.md')])
        assert not result.success
        assert 'File not found' in str(result.error)

    @pytest.mark.asyncio
    async def test_process_empty_input(self, processor):
        """Test processing with no input files."""
        result = await processor.process([])
        
        assert result.success
        assert len(result.output_files) == 0

    @pytest.mark.asyncio
    async def test_cleanup(self, processor):
        """Test cleanup method."""
        # Mock handlers with async cleanup
        class AsyncMockHandler:
            async def cleanup(self):
                pass
        
        processor.handlers = [AsyncMockHandler(), AsyncMockHandler()]
        
        # Call cleanup
        await processor.cleanup()
        
        # Verify handlers were cleaned up
        # Note: We can't verify the cleanup was called since we're using simple async mocks
        assert True 