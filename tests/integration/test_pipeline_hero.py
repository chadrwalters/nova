"""Hero tests for the Nova pipeline."""

import os
import pytest
import asyncio
from pathlib import Path
import shutil
from textwrap import dedent
import yaml
import json
from datetime import datetime, timedelta

from nova.core.pipeline import NovaPipeline
from nova.config.manager import ConfigManager
from nova.core.progress import ProcessingStatus


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    config = ConfigManager()
    
    # Set up temporary directories using update_config
    config.update_config({
        'base_dir': str(tmp_path),
        'input_dir': str(tmp_path / "input"),
        'output_dir': str(tmp_path / "output"),
        'processing_dir': str(tmp_path / "processing"),
        'cache': {
            'dir': str(tmp_path / "cache"),
            'enabled': True,
            'ttl': 3600
        }
    })
    
    # Create directories
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.processing_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def test_files(test_config):
    """Create test files in a realistic directory structure."""
    # Create test files
    input_dir = test_config.input_dir
    
    # Create a text file
    text_file = input_dir / "test.txt"
    text_file.write_text("Test content")
    
    # Create a markdown file
    md_file = input_dir / "test.md"
    md_file.write_text(dedent("""
    # Test Document
    
    This is a test document.
    
    --==RAW NOTES==--
    These are raw notes.
    """).strip())
    
    return input_dir


@pytest.mark.asyncio
async def test_pipeline_phase_sequencing(test_config, test_files):
    """Test that phases are executed in the correct order with proper dependencies."""
    # Initialize pipeline
    pipeline = NovaPipeline()
    pipeline.config = test_config
    
    # Process a test file through both phases
    test_file = test_files / "test.txt"
    metadata = await pipeline.process_file(test_file, ["parse", "split"])
    
    # Verify metadata
    assert metadata is not None
    assert metadata.processed
    assert not metadata.has_errors
    
    # Verify phase directories were created
    phases_dir = test_config.processing_dir / "phases"
    assert (phases_dir / "parse").exists()
    assert (phases_dir / "split").exists()
    
    # Verify parse phase output exists and was created first
    parsed_file = phases_dir / "parse" / "test.parsed.md"
    assert parsed_file.exists()
    
    # Verify split phase output exists and was created after parse phase
    split_dir = phases_dir / "split"
    assert (split_dir / "Summary.md").exists()
    assert (split_dir / "Raw Notes.md").exists()
    
    # Verify phase completion status
    assert pipeline.progress.phases["parse"].status == ProcessingStatus.COMPLETED
    assert pipeline.progress.phases["split"].status == ProcessingStatus.COMPLETED
    
    # Verify phase ordering through timestamps
    parse_time = pipeline.progress.phases["parse"].end_time
    split_time = pipeline.progress.phases["split"].end_time
    assert parse_time < split_time, "Split phase completed before parse phase"
    
    # Verify state preservation between phases
    # The split phase should use the parse phase's output
    summary = (split_dir / "Summary.md").read_text()
    assert "Test content" in summary  # Content from parse phase should be in split phase output


@pytest.mark.asyncio
async def test_pipeline_phase_dependencies(test_config, test_files):
    """Test that phase dependencies are properly enforced."""
    # Initialize pipeline
    pipeline = NovaPipeline()
    pipeline.config = test_config
    
    # Try to run split phase without parse phase
    test_file = test_files / "test.txt"
    metadata = await pipeline.process_file(test_file, ["split"])
    
    # Verify that the operation failed appropriately
    assert metadata.has_errors
    assert any("No parse directory found" in str(err.get("message", "")) for err in metadata.errors)
    
    # Verify split phase was marked as failed
    assert pipeline.progress.phases["split"].status == ProcessingStatus.FAILED


@pytest.mark.asyncio
async def test_pipeline_state_preservation(test_config, test_files):
    """Test that pipeline state is properly preserved between runs."""
    # Initialize pipeline
    pipeline = NovaPipeline()
    pipeline.config = test_config
    
    # Process a file
    test_file = test_files / "test.md"
    metadata = await pipeline.process_file(test_file, ["parse", "split"])
    
    # Verify initial processing
    assert metadata.processed
    assert not metadata.has_errors
    
    # Get file timestamps
    phases_dir = test_config.processing_dir / "phases"
    parse_file = phases_dir / "parse" / "test.parsed.md"
    split_summary = phases_dir / "split" / "Summary.md"
    parse_time = parse_file.stat().st_mtime
    split_time = split_summary.stat().st_mtime
    
    # Wait a moment to ensure timestamps would be different
    await asyncio.sleep(0.1)
    
    # Process the same file again
    metadata2 = await pipeline.process_file(test_file, ["parse", "split"])
    
    # Verify file wasn't reprocessed (timestamps should be the same)
    assert parse_file.stat().st_mtime == parse_time
    assert split_summary.stat().st_mtime == split_time
    
    # Modify the input file
    test_file.write_text(dedent("""
    # Modified Document
    
    This document was modified.
    
    --==RAW NOTES==--
    Modified notes.
    """).strip())
    
    # Wait a moment to ensure timestamps would be different
    await asyncio.sleep(0.1)
    
    # Process the file again
    metadata3 = await pipeline.process_file(test_file, ["parse", "split"])
    
    # Verify file was reprocessed (timestamps should be different)
    assert parse_file.stat().st_mtime > parse_time
    assert split_summary.stat().st_mtime > split_time
    
    # Verify new content is present
    parse_content = parse_file.read_text()
    split_content = split_summary.read_text()
    assert "Modified Document" in parse_content
    assert "Modified Document" in split_content


@pytest.mark.asyncio
async def test_pipeline_error_propagation(test_config, test_files):
    """Test that errors are properly propagated through the pipeline."""
    # Initialize pipeline
    pipeline = NovaPipeline()
    pipeline.config = test_config
    
    # Create an unreadable file
    bad_file = test_files / "bad_file.txt"
    bad_file.write_text("Some content")
    bad_file.chmod(0o000)  # Make file unreadable
    
    try:
        # Process the unreadable file
        metadata = await pipeline.process_file(bad_file, ["parse", "split"])
        
        # Verify error handling
        assert metadata.has_errors
        assert pipeline.progress.phases["parse"].status == ProcessingStatus.FAILED
        assert pipeline.progress.phases["parse"].failed_files == 1
        
        # Verify split phase wasn't attempted
        assert pipeline.progress.phases["split"].status == ProcessingStatus.PENDING
        
        # Verify file progress
        assert pipeline.progress.files[bad_file].status == ProcessingStatus.FAILED
        assert pipeline.progress.files[bad_file].current_phase is None
        
    finally:
        # Clean up
        bad_file.chmod(0o644)
        bad_file.unlink() 