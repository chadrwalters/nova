"""Test markdown handler."""

import os
import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock

from rich.console import Console

from nova.core.utils.metrics import TimingManager, MetricsTracker
from nova.core.utils.metrics import MonitoringManager
from nova.core.pipeline import PipelineState
from nova.phases.parse.handlers.markdown import MarkdownHandler
from nova.core.models.result import ProcessingResult


@pytest.fixture
def handler(tmp_path):
    """Create a MarkdownHandler instance for testing."""
    config = {
        'sections': {
            'patterns': {
                'summary': r'^#{1,2}\s*Summary',
                'raw_notes': r'^#{1,2}\s*Raw\s*Notes',
                'attachments': r'^#{1,2}\s*Attachments'
            },
            'optional': ['attachments']
        }
    }
    timing = TimingManager()
    metrics = MetricsTracker()
    console = Console()
    pipeline_state = PipelineState(state_file=tmp_path / "pipeline_state.json")
    monitoring = MonitoringManager()
    return MarkdownHandler(
        config=config,
        timing=timing,
        metrics=metrics,
        console=console,
        pipeline_state=pipeline_state,
        monitoring=monitoring
    )


@pytest.mark.asyncio
async def test_can_handle(handler, tmp_path):
    """Test can_handle method."""
    # Test valid markdown file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test")
    assert handler.can_handle(test_file)

    # Test non-existent file
    assert not handler.can_handle(tmp_path / "nonexistent.md")

    # Test non-markdown file
    test_txt = tmp_path / "test.txt"
    test_txt.write_text("Test")
    assert not handler.can_handle(test_txt)

    # Test directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    assert not handler.can_handle(test_dir)


@pytest.mark.asyncio
async def test_process_basic_markdown(handler, tmp_path):
    """Test processing a basic markdown file."""
    # Create test file
    test_file = tmp_path / "basic.md"
    test_file.write_text("""# Test Document

## Summary
This is a test summary.

## Raw Notes
These are raw notes.

## Attachments
- test.png
""")

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the file
    result = await handler.process(test_file, {"output_dir": str(output_dir)})

    assert result.success
    assert result.output
    assert len(result.output_files) > 0
    
    # Verify output file exists
    output_file = output_dir / test_file.name
    assert output_file.exists()
    
    # Verify sections were parsed
    assert result.metadata
    assert 'raw_notes' in result.metadata
    assert result.metadata['raw_notes']


@pytest.mark.asyncio
async def test_process_with_dependencies(handler, tmp_path):
    """Test processing a markdown file with dependencies."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text("""# Test Document

## Summary
This is a test summary.

## Raw Notes
These are raw notes.

## Dependencies
- test.png
- data.csv
""")

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the file
    result = await handler.process(test_file, {"output_dir": str(output_dir)})

    assert result.success
    assert result.output
    assert len(result.output_files) > 0
    
    # Verify output file exists
    output_file = output_dir / test_file.name
    assert output_file.exists()
    
    # Verify sections were parsed
    assert result.metadata
    assert 'raw_notes' in result.metadata
    assert result.metadata['raw_notes']


@pytest.mark.asyncio
async def test_process_invalid_file(handler, tmp_path):
    """Test processing an invalid file."""
    # Create test file with invalid extension
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is not a markdown file.")

    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the file
    result = await handler.process(test_file, {"output_dir": str(output_dir)})

    assert not result.success
    assert "Cannot handle file" in str(result.error)


@pytest.mark.asyncio
async def test_process_no_output_dir(handler, tmp_path):
    """Test processing without output directory."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text("""# Test Document

## Summary
This is a test summary.

## Raw Notes
These are raw notes.
""")

    # Process the file without output directory
    result = await handler.process(test_file, {})

    assert not result.success
    assert "No output directory specified" in str(result.error)


@pytest.mark.asyncio
async def test_cleanup(handler):
    """Test cleanup method."""
    await handler.cleanup()
    assert True  # Just verify it doesn't raise an exception 