"""Hero tests for the Nova pipeline."""

import pytest
from pathlib import Path
import tempfile
import shutil
import os

from nova.core.pipeline import NovaPipeline
from nova.config.manager import ConfigManager
from nova.phases.base import Phase

@pytest.fixture
def config(test_dir):
    """Create a test configuration."""
    config = ConfigManager()
    config.update_config({
        'base_dir': str(test_dir),
        'input_dir': str(test_dir / "input"),
        'output_dir': str(test_dir / "output"),
        'processing_dir': str(test_dir / "processing"),
        'cache': {
            'dir': str(test_dir / "cache"),
            'enabled': True,
            'ttl': 3600
        },
        'apis': {
            'openai': {
                'api_key': "None"  # Explicitly disable OpenAI API for tests
            }
        }
    })
    return config

@pytest.fixture
def test_dir():
    """Create a temporary test directory."""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    shutil.rmtree(test_dir)

async def test_pipeline_phase_sequencing(config, test_dir):
    """Test that pipeline phases are executed in the correct order."""
    # Create pipeline
    pipeline = NovaPipeline(config)
    
    # Create test files
    input_dir = test_dir / "input"
    input_dir.mkdir(parents=True)
    test_file = input_dir / "test.txt"
    test_file.write_text("test content")
    
    # Process directory
    await pipeline.process_directory(input_dir)
    
    # Check that output file exists in parse phase
    parse_dir = test_dir / "processing" / "phases" / "parse"
    assert (parse_dir / "test.parsed.md").exists()
    
    # Check that split phase processed the parsed file
    split_dir = test_dir / "processing" / "phases" / "split"
    assert (split_dir / "test.parsed.md").exists()

async def test_pipeline_phase_dependencies(config, test_dir):
    """Test that pipeline phases respect dependencies."""
    # Create pipeline
    pipeline = NovaPipeline(config)
    
    # Create test files
    input_dir = test_dir / "input"
    input_dir.mkdir(parents=True)
    test_file = input_dir / "test.txt"
    test_file.write_text("test content")
    
    # Process directory
    await pipeline.process_directory(input_dir)
    
    # Check that parse phase output exists
    parse_dir = test_dir / "processing" / "phases" / "parse"
    assert (parse_dir / "test.parsed.md").exists()
    
    # Check that split phase output exists and depends on parse output
    split_dir = test_dir / "processing" / "phases" / "split"
    assert (split_dir / "test.parsed.md").exists()
    
    # Verify split phase output is newer than parse phase output
    parse_mtime = (parse_dir / "test.parsed.md").stat().st_mtime
    split_mtime = (split_dir / "test.parsed.md").stat().st_mtime
    assert split_mtime >= parse_mtime

async def test_pipeline_state_preservation(config, test_dir):
    """Test that pipeline preserves state between runs."""
    # Create pipeline
    pipeline = NovaPipeline(config)
    
    # Create test files
    input_dir = test_dir / "input"
    input_dir.mkdir(parents=True)
    test_file = input_dir / "test.txt"
    test_file.write_text("test content")
    
    # Process directory first time
    await pipeline.process_directory(input_dir)
    
    # Get initial content
    parse_dir = test_dir / "processing" / "phases" / "parse"
    split_dir = test_dir / "processing" / "phases" / "split"
    parse_content = (parse_dir / "test.parsed.md").read_text()
    split_content = (split_dir / "test.parsed.md").read_text()
    
    # Process directory again
    await pipeline.process_directory(input_dir)
    
    # Check that content wasn't modified
    assert (parse_dir / "test.parsed.md").read_text() == parse_content
    assert (split_dir / "test.parsed.md").read_text() == split_content

@pytest.mark.asyncio
async def test_pipeline_error_propagation(tmp_path: Path):
    """Test that errors are properly propagated through the pipeline."""
    # Create test input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Create an invalid file
    invalid_file = input_dir / "invalid.xyz"
    invalid_file.write_text("invalid content")
    
    # Create a valid file
    valid_file = input_dir / "test.txt"
    valid_file.write_text("test content")
    
    # Configure pipeline
    config = ConfigManager()
    config.update_config({
        'base_dir': str(tmp_path),
        'input_dir': str(input_dir),
        'output_dir': str(tmp_path / "output"),
        'processing_dir': str(tmp_path / "processing"),
        'cache': {
            'dir': str(tmp_path / "cache"),
            'enabled': True,
            'ttl': 3600
        }
    })
    
    # Process files
    pipeline = NovaPipeline(config)
    await pipeline.process_directory(input_dir)
    
    # Verify that invalid file is in failed_files
    assert invalid_file in pipeline.failed_files
    
    # Verify that valid file was processed
    assert valid_file in pipeline.successful_files
    
    # Verify that output file exists for valid file
    parse_dir = tmp_path / "processing" / "phases" / "parse"
    assert (parse_dir / "test.parsed.md").exists() 